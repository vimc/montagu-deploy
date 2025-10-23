import os
from os.path import join

import constellation
import docker
import yaml
from constellation import docker_util
from psycopg2 import connect

from montagu_deploy import database


def montagu_constellation(cfg):
    proxy = proxy_container(cfg)
    containers = [
        api_container(cfg),
        db_container(cfg),
        admin_container(cfg),
        contrib_container(cfg),
        proxy,
        proxy_metrics_container(cfg),
        mq_container(cfg),
        flower_container(cfg),
        task_queue_container(cfg),
    ]

    if cfg.ssl_mode == "acme":
        acme_buddy = acme_buddy_container(cfg, proxy)
        containers.append(acme_buddy)

    if cfg.fake_smtp_ref:
        fake_smtp = fake_smtp_container(cfg)
        containers.append(fake_smtp)

    return constellation.Constellation(
        "montagu", cfg.container_prefix, containers, cfg.network, cfg.volumes, data=cfg, vault_config=cfg.vault
    )


def admin_container(cfg):
    name = cfg.containers["admin"]
    return constellation.ConstellationContainer(name, cfg.admin_ref)


def contrib_container(cfg):
    name = cfg.containers["contrib"]
    mounts = [
        constellation.ConstellationVolumeMount("templates", "/usr/share/nginx/html/templates"),
        constellation.ConstellationVolumeMount("guidance", "/usr/share/nginx/html/guidance"),
    ]
    return constellation.ConstellationContainer(name, cfg.contrib_ref, mounts=mounts)


def mq_container(cfg):
    name = cfg.containers["mq"]
    mounts = [
        constellation.ConstellationVolumeMount("mq", "/data"),
    ]
    return constellation.ConstellationContainer(name, cfg.mq_ref, mounts=mounts, ports=[cfg.mq_port])


def flower_container(cfg):
    name = cfg.containers["flower"]
    mq = cfg.containers["mq"]
    env = {
        "CELERY_BROKER_URL": f"redis://{mq}//",
        "CELERY_RESULT_BACKEND": f"redis://{mq}/0",
        "FLOWER_PORT": cfg.flower_port,
    }
    return constellation.ConstellationContainer(name, cfg.flower_ref, ports=[cfg.flower_port], environment=env)


def task_queue_container(cfg):
    name = cfg.containers["task_queue"]
    mounts = [
        constellation.ConstellationVolumeMount("burden_estimates", "/home/worker/burden_estimate_files"),
    ]
    return constellation.ConstellationContainer(name, cfg.task_queue_ref, configure=task_queue_configure, mounts=mounts)


def task_queue_configure(container, cfg):
    print("[task-queue] Configuring task-queue container")
    task_queue_config = {"host": cfg.containers["mq"], "servers": cfg.task_queue_servers, "tasks": cfg.task_queue_tasks}
    task_queue_config["servers"]["montagu"]["url"] = f"http://{cfg.containers['api']}:8080"
    if cfg.fake_smtp_ref:
        task_queue_config["servers"]["smtp"]["host"] = cfg.containers["fake_smtp"]
        task_queue_config["servers"]["smtp"]["port"] = 1025
    reports_cfg_filename = join(cfg.path, "diagnostic-reports.yml")
    with open(reports_cfg_filename) as ymlfile:
        diag_reports = yaml.safe_load(ymlfile)
    task_queue_config["tasks"]["diagnostic_reports"]["reports"] = diag_reports
    docker_util.string_into_container(yaml.dump(task_queue_config), container, "/home/worker/config/config.yml")
    docker_util.exec_safely(container, ["chown", "worker:worker", "/home/worker/config/config.yml"], user="root")


def fake_smtp_container(cfg):
    name = cfg.containers["fake_smtp"]
    return constellation.ConstellationContainer(name, cfg.fake_smtp_ref, ports=[1025, 1080])


def acme_buddy_container(cfg, proxy):
    name = cfg.containers["acme-buddy"]
    acme_buddy_staging = int(os.environ.get("ACME_BUDDY_STAGING", "0"))
    acme_env = {
        "ACME_BUDDY_STAGING": acme_buddy_staging,
        "HDB_ACME_USERNAME": cfg.acme_buddy_hdb_username,
        "HDB_ACME_PASSWORD": cfg.acme_buddy_hdb_password,
    }
    acme_mounts = [
        constellation.ConstellationVolumeMount("montagu-tls", "/tls"),
        constellation.ConstellationBindMount("/var/run/docker.sock", "/var/run/docker.sock"),
    ]

    domain_names = cfg.hostname
    for i in range(len(cfg.acme_additional_domains)):
        domain_names += f",{cfg.acme_additional_domains[i]}"

    acme = constellation.ConstellationContainer(
        name,
        cfg.acme_buddy_ref,
        ports=[cfg.acme_buddy_port],
        mounts=acme_mounts,
        environment=acme_env,
        args=[
            "--domain",
            domain_names,
            "--email",
            cfg.acme_buddy_email,
            "--dns-provider",
            "hdb",
            "--certificate-path",
            "/tls/certificate.pem",
            "--key-path",
            "/tls/key.pem",
            "--account-path",
            "/tls/account.json",
            "--reload-container",
            proxy.name_external(cfg.container_prefix),
        ],
    )
    return acme


def db_container(cfg):
    name = cfg.containers["db"]
    mounts = [constellation.ConstellationVolumeMount("db", "/pgdata")]
    return constellation.ConstellationContainer(name, cfg.db_ref, mounts=mounts, ports=[5432], configure=db_configure)


def db_configure(container, cfg):
    print("[db] Waiting for the database to accept connections")
    docker_util.exec_safely(container, ["montagu-wait.sh", "7200"])
    print("[db] Scrambling root password")
    db_set_root_password(container, cfg, cfg.db_root_password)
    print("[db] Setting up database users")
    db_setup_users(cfg)
    print("[db] Migrating database schema")
    db_migrate_schema(cfg)
    print("[db] Refreshing user permissions")
    # The migrations may have added new tables, so we should set the permissions
    # again, in case users need to have permissions on these new tables
    db_set_user_permissions(cfg)

    if cfg.enable_streaming_replication:
        print("[db] Enabling streaming replication")
        db_enable_streaming_replication(container, cfg)


def db_set_root_password(container, cfg, password):
    query = f"ALTER USER {cfg.db_root_user} WITH PASSWORD '{password}'"
    docker_util.exec_safely(container, f'psql -U {cfg.db_root_user} -d postgres -c "{query}"')


def db_setup_users(cfg):
    with db_connection(cfg) as conn:
        with conn.cursor() as cur:
            for user in cfg.db_users:
                database.setup_db_user(cur, user, cfg.db_users[user])
        conn.commit()


def db_set_user_permissions(cfg):
    with db_connection(cfg) as conn:
        with conn.cursor() as cur:
            for user in cfg.db_users:
                database.set_permissions(cur, user, cfg.db_users[user])
                # Revoke specific permissions now that all tables have been created.
                database.revoke_write_on_protected_tables(cur, user, cfg.db_protected_tables)
        conn.commit()


def db_connection(cfg):
    return connect(user=cfg.db_root_user, dbname="montagu", password=cfg.db_root_password, host="localhost", port=5432)


def db_migrate_schema(cfg):
    network_name = cfg.network
    image = cfg.db_migrate_ref
    client = docker.client.from_env()
    client.containers.run(
        str(image),
        [f"-user={cfg.db_root_user}", f"-password={cfg.db_root_password}", "migrate"],
        network=network_name,
        stderr=True,
        remove=True,
    )


def db_enable_streaming_replication(container, cfg):
    docker_util.exec_safely(
        container,
        ["enable-replication.sh", cfg.db_users["barman"]["password"], cfg.db_users["streaming_barman"]["password"]],
    )


def api_container(cfg):
    name = cfg.containers["api"]
    mounts = [
        constellation.ConstellationVolumeMount("burden_estimates", "/upload_dir"),
        constellation.ConstellationVolumeMount("emails", "/tmp/emails"),  # noqa S108
    ]
    return constellation.ConstellationContainer(name, cfg.api_ref, mounts=mounts, configure=api_configure)


def api_configure(container, cfg):
    print("[api] Configuring API container")
    docker_util.exec_safely(container, ["mkdir", "-p", "/etc/montagu/api"])
    inject_api_config(container, cfg)
    start_api(container)


def start_api(container):
    docker_util.exec_safely(container, ["touch", "/etc/montagu/api/go_signal"])


def inject_api_config(container, cfg):
    db_name = cfg.containers["db"]
    opts = {
        "app.url": f"https://{cfg.hostname}/api",
        "db.host": db_name,
        "db.username": "api",
        "db.password": cfg.db_users["api"]["password"],
        "allow.localhost": False,
        "celery.flower.host": cfg.containers["flower"],
        "packit.api.url": cfg.packit_api_url,
        "upload.dir": "/upload_dir",
    }

    if cfg.real_emails:
        opts["email.mode"] = "real"
        opts["email.password"] = cfg.email_password
        opts["flow.url"] = cfg.email_flow_url

    txt = "".join([f"{k}={v}\n" for k, v in opts.items()])
    docker_util.string_into_container(txt, container, "/etc/montagu/api/config.properties")


def proxy_container(cfg):
    name = cfg.containers["proxy"]
    proxy_ports = [cfg.proxy_port_http, cfg.proxy_port_https, cfg.proxy_port_metrics]

    mounts = []

    if cfg.ssl_mode == "acme":
        mounts.extend(
            [
                constellation.ConstellationVolumeMount("montagu-tls", "/etc/montagu/proxy"),
            ]
        )

    return constellation.ConstellationContainer(
        name,
        cfg.proxy_ref,
        ports=proxy_ports,
        args=[str(cfg.proxy_port_https), cfg.hostname],
        mounts=mounts,
    )


def proxy_metrics_container(cfg):
    proxy_name = cfg.containers["proxy"]
    return constellation.ConstellationContainer(
        cfg.containers["metrics"],
        cfg.proxy_metrics_ref,
        ports=[9113],
        args=["-nginx.scrape-uri", f"http://{proxy_name}/basic_status"],
    )

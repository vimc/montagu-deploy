from os.path import join

import constellation
import docker.client
from constellation import docker_util


class MontaguConstellation:
    def __init__(self, cfg):
        api = api_container(cfg)
        db = db_container(cfg)
        admin = admin_container(cfg)
        contrib = contrib_container(cfg)
        static = static_container(cfg)
        proxy = proxy_container(cfg)

        containers = [api, db, admin, contrib, static, proxy]

        self.cfg = cfg
        self.obj = constellation.Constellation(
            "montagu", cfg.container_prefix, containers, cfg.network, cfg.volumes, data=cfg, vault_config=cfg.vault
        )

    def start(self, **kwargs):
        self.obj.start(**kwargs)

    def stop(self, **kwargs):
        self.obj.stop(**kwargs)

    def status(self):
        self.obj.status()


def admin_container(cfg):
    name = cfg.containers["admin"]
    return constellation.ConstellationContainer(name, cfg.admin_ref)


def contrib_container(cfg):
    name = cfg.containers["contrib"]
    mounts = [
        constellation.ConstellationMount("templates", "/usr/share/nginx/html/templates"),
        constellation.ConstellationMount("guidance", "/usr/share/nginx/html/guidance"),
    ]
    return constellation.ConstellationContainer(name, cfg.contrib_ref, mounts=mounts, configure=contrib_configure)


def contrib_configure(container, cfg):
    if cfg.guidance_reports is not None:
        print("[contrib] Configuring contrib portal")
        for p in cfg.guidance_reports:
            if len(p) > 0:
                path_to_artefacts = join("archive", p, "*.html")
                add_reports_to_contrib_portal(cfg, path_to_artefacts)


def add_reports_to_contrib_portal(cfg, path_to_reports):
    print("[contrib] Copying guidance reports from orderly to contrib portal")
    copy_between_volumes(cfg.orderly_volume_name, cfg.volumes["guidance"], path_to_reports)


def static_container(cfg):
    name = cfg.containers["static"]
    mounts = [
        constellation.ConstellationMount("static", "/www"),
        constellation.ConstellationMount("static_logs", "/var/log/caddy"),
    ]
    return constellation.ConstellationContainer(name, cfg.static_ref, mounts=mounts)


def db_container(cfg):
    name = cfg.containers["db"]
    mounts = [constellation.ConstellationMount("db", "/pgdata")]
    return constellation.ConstellationContainer(name, cfg.db_ref, mounts=mounts, ports=[5432])


def api_container(cfg):
    name = cfg.containers["api"]
    mounts = [
        constellation.ConstellationMount("burden_estimates", "/upload_dir"),
        constellation.ConstellationMount("emails", "/tmp/emails"),  # noqa S108
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
        "db.username": cfg.db_user,
        "db.password": cfg.db_password,
        "allow.localhost": False,
        # TODO  "celery.flower.host",
        "orderlyweb.api.url": cfg.orderly_web_api_url,
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
    proxy_ports = [cfg.proxy_port_http, cfg.proxy_port_https]
    return constellation.ConstellationContainer(
        name,
        cfg.proxy_ref,
        ports=proxy_ports,
        args=[str(cfg.proxy_port_https), cfg.hostname],
        configure=proxy_configure,
    )


def proxy_configure(container, cfg):
    print("[proxy] Configuring reverse proxy")
    ssl_path = "/etc/montagu/proxy"
    if cfg.proxy_ssl_self_signed:
        print("[proxy] Generating self-signed certificates for proxy")
        docker_util.exec_safely(container, ["self-signed-certificate", ssl_path])
    else:
        print("[proxy] Copying ssl certificate and key into proxy")
        docker_util.exec_safely(container, f"mkdir -p {ssl_path}")
        docker_util.string_into_container(cfg.ssl_certificate, container, join(ssl_path, "certificate.pem"))
        docker_util.string_into_container(cfg.ssl_key, container, join(ssl_path, "ssl_key.pem"))
        docker_util.string_into_container(cfg.dhparam, container, join(ssl_path, "dhparam.pem"))


def copy_between_volumes(source_volume, destination_volume, path_to_copy, destination_path="."):
    client = docker.client.from_env()
    cmd = "cd /to ; mkdir -p {} && find /from/{} -exec cp -a {{}} {} \;".format(destination_path, path_to_copy,
                                                                               destination_path)
    client.containers.run("alpine", ["ash", "-c", cmd], remove=True,
                          mounts=[docker.types.Mount("/from", source_volume),
                                  docker.types.Mount("/to", destination_volume)])

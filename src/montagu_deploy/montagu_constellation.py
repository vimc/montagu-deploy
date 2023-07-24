import constellation
from constellation import docker_util


class MontaguConstellation:
    def __init__(self, cfg):
        api = api_container(cfg)
        db = db_container(cfg)

        containers = [api, db]

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


def api_container(cfg):
    name = cfg.containers["api"]
    mounts = [
        constellation.ConstellationMount("burden_estimates", "/upload_dir"),
        constellation.ConstellationMount("emails", "/tmp/emails"),  # noqa S108
    ]
    return constellation.ConstellationContainer(name, cfg.api_ref, mounts=mounts, configure=api_configure)


def db_container(cfg):
    name = cfg.containers["db"]
    mounts = [constellation.ConstellationMount("db", "/pgdata")]
    return constellation.ConstellationContainer(name, cfg.db_ref, mounts=mounts, ports=[5432])


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

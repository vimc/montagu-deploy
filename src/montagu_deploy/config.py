import constellation
from constellation import config


class MontaguConfig:
    def __init__(self, path, extra=None, options=None):
        dat = config.read_yaml(f"{path}/montagu.yml")
        dat = config.config_build(path, dat, extra, options)
        self.vault = config.config_vault(dat, ["vault"])
        self.network = config.config_string(dat, ["network"])
        self.protect_data = config.config_boolean(dat, ["protect_data"])
        self.volumes = {
            "db": config.config_string(dat, ["volumes", "db"]),
            "emails": config.config_string(dat, ["volumes", "emails"]),
            "burden_estimates": config.config_string(dat, ["volumes", "burden_estimates"]),
            "templates": config.config_string(dat, ["volumes", "templates"]),
            "guidance": config.config_string(dat, ["volumes", "guidance"]),
            "static": config.config_string(dat, ["volumes", "static"]),
            "static_logs": config.config_string(dat, ["volumes", "static_logs"]),
            "mq": config.config_string(dat, ["volumes", "mq"])
        }

        self.container_prefix = config.config_string(dat, ["container_prefix"])
        self.repo = config.config_string(dat, ["repo"])
        self.hostname = config.config_string(dat, ["hostname"])
        self.orderly_web_api_url = config.config_string(dat, ["orderly_web_api_url"])

        # API
        self.api_ref = self.build_ref(dat, "api")
        self.real_emails = "email" in dat["api"]
        if self.real_emails:
            self.email_password = config.config_string(dat, ["api", "email", "password"])
            self.email_flow_url = config.config_string(dat, ["api", "email", "flow_url"])

        # DB
        self.db_ref = self.build_ref(dat, "db")
        self.db_user = config.config_string(dat, ["db", "user"])
        self.db_password = config.config_string(dat, ["db", "password"])

        # Proxy
        self.proxy_ref = self.build_ref(dat, "proxy")
        self.proxy_ssl_self_signed = "ssl" not in dat["proxy"]
        if not self.proxy_ssl_self_signed:
            self.ssl_certificate = config.config_string(dat, ["proxy", "ssl", "certificate"])
            self.ssl_key = config.config_string(dat, ["proxy", "ssl", "key"])
            self.dhparam = config.config_string(dat, ["proxy", "ssl", "dhparam"])
        self.proxy_port_http = config.config_integer(dat, ["proxy", "port_http"])
        self.proxy_port_https = config.config_integer(dat, ["proxy", "port_https"])

        # Portals
        self.admin_ref = self.build_ref(dat, "admin")
        self.contrib_ref = self.build_ref(dat, "contrib")

        self.static_ref = self.build_ref(dat, "static")

        # Task Q
        self.mq_ref = self.build_ref(dat, "mq")
        self.mq_port = config.config_integer(dat, ["mq", "port"])
        self.flower_ref = self.build_ref(dat, "flower")
        self.flower_port = config.config_integer(dat, ["flower", "port"])
        self.task_queue_ref = self.build_ref(dat, "task_queue")
        self.youtrack_token = config.config_string(dat, ["task_queue", "youtrack_token"])

        self.containers = {
            "db": "db",
            "api": "api",
            "proxy": "proxy",
            "admin": "admin",
            "contrib": "contrib",
            "static": "static",
            "mq": "mq",
            "flower": "flower",
            "task_queue": "task-queue"
        }

        self.images = {
            "db": self.db_ref,
            "api": self.api_ref,
            "proxy": self.proxy_ref,
            "admin": self.admin_ref,
            "contrib": self.contrib_ref,
            "static": self.static_ref,
            "mq": self.mq_ref,
            "flower": self.flower_ref,
            "task_queue": self.task_queue_ref
        }

    def build_ref(self, dat, section):
        name = config.config_string(dat, [section, "name"])
        tag = config.config_string(dat, [section, "tag"])
        if "repo" in dat[section]:
            repo = config.config_string(dat, [section, "repo"])
        else:
            repo = self.repo
        return constellation.ImageReference(repo, name, tag)

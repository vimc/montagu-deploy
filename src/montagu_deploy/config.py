import random
import string

import constellation
from constellation import config


class MontaguConfig:
    def __init__(self, path, extra=None, options=None):
        dat = config.read_yaml(f"{path}/montagu.yml")
        dat = config.config_build(path, dat, extra, options)
        self.path = path
        self.vault = config.config_vault(dat, ["vault"])
        self.network = config.config_string(dat, ["network"])
        self.protect_data = config.config_boolean(dat, ["protect_data"])
        self.volumes = config.config_dict(dat, ["volumes"])

        self.container_prefix = config.config_string(dat, ["container_prefix"])
        self.repo = config.config_string(dat, ["repo"])
        self.hostname = config.config_string(dat, ["hostname"])
        self.packit_api_url = config.config_string(dat, ["packit_api_url"])

        # API
        self.api_ref = self.build_ref(dat, "api")
        self.api_admin_ref = self.build_ref(dat["api"], "admin")
        self.real_emails = "email" in dat["api"]
        if self.real_emails:
            self.email_password = config.config_string(dat, ["api", "email", "password"])
            self.email_flow_url = config.config_string(dat, ["api", "email", "flow_url"])

        # DB
        self.db_ref = self.build_ref(dat, "db")
        self.db_migrate_ref = self.build_ref(dat["db"], "migrate")
        self.db_root_user = config.config_string(dat, ["db", "root_user"])
        if "root_password" in dat["db"]:
            self.db_root_password = config.config_string(dat, ["db", "root_password"])
        else:
            self.db_root_password = "".join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(50)
            )
        self.db_users = config.config_dict(dat, ["db", "users"])
        invalid = {
            k: v for k, v in self.db_users.items() if "permissions" in v and v["permissions"] not in ["all", "readonly"]
        }
        if any(invalid):
            invalid_str = ",".join(iter(invalid.keys()))
            msg = f"Invalid database permissions for '{invalid_str}'. Supported values are 'all' and 'readonly'"
            raise Exception(msg)
        self.db_protected_tables = config.config_list(dat, ["db", "protected_tables"])
        self.enable_streaming_replication = "barman" in self.db_users and "streaming_barman" in self.db_users

        # Proxy
        self.proxy_ref = self.build_ref(dat, "proxy")
        self.proxy_port_http = config.config_integer(dat, ["proxy", "port_http"])
        self.proxy_port_https = config.config_integer(dat, ["proxy", "port_https"])
        self.proxy_port_metrics = config.config_integer(dat, ["proxy", "port_metrics"], is_optional=True, default=9000)
        self.proxy_metrics_ref = self.build_ref(dat["proxy"], "metrics")

        if "ssl" in dat["proxy"] and "acme" in dat["proxy"]:
            msg = "Cannot specify both ssl and acme options in proxy options."
            raise Exception(msg)
        if "ssl" in dat["proxy"]:
            self.ssl_mode = "static"
            self.ssl_certificate = config.config_string(dat, ["proxy", "ssl", "certificate"])
            self.ssl_key = config.config_string(dat, ["proxy", "ssl", "key"])
        elif "acme" in dat["proxy"]:
            self.ssl_mode = "acme"
            self.acme_email = config.config_string(dat, ["proxy", "acme", "email"])
            self.acme_server = config.config_string(dat, ["proxy", "acme", "server"], is_optional=True)
            self.acme_no_verify_ssl = config.config_boolean(dat, ["proxy", "acme", "no_verify_ssl"], is_optional=True)
            self.acme_additional_domains = config.config_list(
                dat, ["proxy", "acme", "additional_domains"], is_optional=True, default=[]
            )
        else:
            self.ssl_mode = "self-signed"

        # Portals
        self.admin_ref = self.build_ref(dat, "admin")
        self.contrib_ref = self.build_ref(dat, "contrib")

        # Task Q
        self.mq_ref = self.build_ref(dat, "mq")
        self.mq_port = config.config_integer(dat, ["mq", "port"])
        self.flower_ref = self.build_ref(dat, "flower")
        self.flower_port = config.config_integer(dat, ["flower", "port"])
        self.task_queue_ref = self.build_ref(dat, "task_queue")
        self.task_queue_tasks = config.config_dict(dat, ["task_queue", "tasks"])
        self.task_queue_servers = config.config_dict(dat, ["task_queue", "servers"])
        if "fake_smtp_server" in dat:
            self.fake_smtp_ref = self.build_ref(dat, "fake_smtp_server")
        else:
            self.fake_smtp_ref = False

        self.containers = {
            "db": "db",
            "api": "api",
            "proxy": "proxy",
            "metrics": "proxy-metrics",
            "admin": "admin",
            "contrib": "contrib",
            "mq": "mq",
            "flower": "flower",
            "task_queue": "task-queue",
        }

        if self.fake_smtp_ref:
            self.containers["fake_smtp"] = "fake-smtp"

        self.images = {
            "db": self.db_ref,
            "api": self.api_ref,
            "proxy": self.proxy_ref,
            "metrics": self.proxy_metrics_ref,
            "admin": self.admin_ref,
            "contrib": self.contrib_ref,
            "mq": self.mq_ref,
            "flower": self.flower_ref,
            "task_queue": self.task_queue_ref,
            "api_admin": self.api_admin_ref,
            "db_migrate": self.db_migrate_ref,
        }

        if self.fake_smtp_ref:
            self.images["fake_smtp"] = self.fake_smtp_ref

    def build_ref(self, dat, section):
        name = config.config_string(dat, [section, "name"])
        tag = config.config_string(dat, [section, "tag"])
        if "repo" in dat[section]:
            repo = config.config_string(dat, [section, "repo"])
        else:
            repo = self.repo
        return constellation.ImageReference(repo, name, tag)

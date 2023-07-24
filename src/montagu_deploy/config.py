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

        self.containers = {"db": "db", "api": "api"}

        self.images = {
            "db": self.db_ref,
            "api": self.api_ref,
        }

    def build_ref(self, dat, section):
        name = config.config_string(dat, [section, "name"])
        tag = config.config_string(dat, [section, "tag"])
        return constellation.ImageReference(self.repo, name, tag)

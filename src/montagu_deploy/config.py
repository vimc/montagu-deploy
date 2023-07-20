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
            "db": config.config_string(dat, ["volumes", "db"])
        }

        self.container_prefix = config.config_string(dat, ["container_prefix"])
        self.repo = config.config_string(dat, ["repo"])
        self.api_ref = self.build_ref(dat, "api")
        self.db_ref = self.build_ref(dat, "db")
        self.db_user = config.config_string(dat, ["db", "user"])
        self.db_password = config.config_string(dat, ["db", "password"])

        self.containers = {
            "montagu-db": "montagu-db",
            "montagu-api": "montagu-api"
        }

        self.images = {
            "montagu-db": self.db_ref,
            "montagu-api": self.api_ref,
        }

    def build_ref(self, dat, section):
        name = config.config_string(dat, [section, "name"])
        tag = config.config_string(dat, [section, "tag"])
        return constellation.ImageReference(self.repo, name, tag)

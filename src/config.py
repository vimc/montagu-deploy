import constellation
import constellation.config as config


class MontaguConfig:
    def __init__(self, path, config_name=None):
        dat = config.read_yaml("{}/montagu.yml".format(path))
        dat = config.config_build(path, dat, config_name)

        self.proxy_host = config.config_string(
            dat, ["proxy", "host"])
        self.proxy_port = config.config_integer(
            dat, ["proxy", "port"])
        self.proxy_ssl_certificate = config.config_string(
            dat, ["proxy", "ssl", "certificate"], True)
        self.proxy_ssl_key = config.config_string(
            dat, ["proxy", "ssl", "key"], True)

        self.db_persist = config.config_boolean(
            dat, ["db", "persist"])
        self.db_backup = config.config_boolean(
            dat, ["db", "backup"])
        self.db_initial = config.config_enum(
            dat, ["db", "initial"], ["minimal", "test", "restore"])
        self.db_update = config.config_boolean(
            dat, ["db", "update"])
        self.db_replication = config.config_boolean(
            dat, ["db", "replication"])
        self.db_large_memory = config.config_boolean(
            dat, ["db", "large_memory"])
        self.db_password_group = config.config_enum(
            dat, ["db", "password_group"], ["production", "science", "fake"])

        # TODO: validation for update

        self.annex_type = config.config_enum(
            dat, ["annex", "type"], ["fake", "readonly", "real"])

        self.api_add_test_user = config.config_boolean(
            dat, ["api", "add_test_user"])

        self.vault = config.config_vault(dat, ["vault"])

        self.docker_network = config.config_string(dat, ["docker", "network"])
        self.docker_prefix = config.config_string(dat, ["docker", "prefix"])

        self.general_open_browser = config.config_boolean(
            dat, ["general", "open_browser"])
        self.general_instance_name = config.config_string(
            dat, ["general", "instance_name"])
        self.general_notify_slack = config.config_boolean(
            dat, ["general", "notify_slack"])

        self.static_copy_static = config.config_boolean(
            dat, ["static", "copy_static"])
        self.static_copy_guidance = config.config_boolean(
            dat, ["static", "copy_guidance"])

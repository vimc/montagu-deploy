import constellation
import constellation.config as config


class MontaguConfig:
    def __init__(self, path, config_name=None):
        dat = config.read_yaml("{}/montagu.yml".format(path))
        dat = config.config_build(path, dat, config_name)

        self.proxy_host = config.config_string(dat, ["proxy", "host"])
        self.proxy_port = config.config_integer(dat, ["proxy", "port"])
        self.proxy_ssl_certificate = config.config_string(
            dat, ["proxy", "ssl", "certificate"], True)
        self.proxy_ssl_key = config.config_string(
            dat, ["proxy", "ssl", "key"], True)

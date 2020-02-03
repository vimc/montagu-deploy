from src import config


def test_default_proxy_configuration():
    cfg = config.MontaguConfig("config")
    assert cfg.proxy_host == "localhost"
    assert cfg.proxy_port == 8443
    assert cfg.proxy_ssl_certificate is None
    assert cfg.proxy_ssl_key is None

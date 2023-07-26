import pytest

from src.montagu_deploy.config import MontaguConfig


def test_config_basic():
    cfg = MontaguConfig("config/basic")
    assert cfg.network == "montagu-network"
    assert cfg.volumes["db"] == "db_volume"
    assert cfg.volumes["emails"] == "emails"
    assert cfg.volumes["burden_estimates"] == "burden_estimate_files"
    assert cfg.volumes["guidance"] == "guidance_volume"
    assert cfg.volumes["templates"] == "template_volume"
    assert cfg.volumes["static"] == "static_volume"
    assert cfg.volumes["static_logs"] == "static_logs"
    assert cfg.container_prefix == "montagu"

    assert len(cfg.containers) == 6
    assert cfg.containers["api"] == "api"
    assert cfg.containers["db"] == "db"
    assert cfg.containers["admin"] == "admin"
    assert cfg.containers["contrib"] == "contrib"
    assert cfg.containers["static"] == "static"
    assert cfg.containers["proxy"] == "proxy"

    assert len(cfg.images) == 7
    assert str(cfg.images["db"]) == "vimc/montagu-db:master"
    assert str(cfg.images["api"]) == "vimc/montagu-api:master"
    assert str(cfg.images["admin"]) == "vimc/montagu-admin-portal:master"
    assert str(cfg.images["contrib"]) == "vimc/montagu-contrib-portal:master"
    assert str(cfg.images["static"]) == "vimc/montagu-static:master"
    assert str(cfg.images["proxy"]) == "vimc/montagu-reverse-proxy:vimc-7152"
    assert str(cfg.images["db_migrate"]) == "vimc/montagu-migrate:master"

    assert cfg.protect_data is False
    assert cfg.proxy_ssl_self_signed is True

    assert cfg.db_root_user == "vimc"
    assert cfg.db_root_password == "changeme"
    assert cfg.db_users == {
        "api": "apipassword",
        "import": "importpassword",
        "orderly": "orderlypassword",
        "readonly": "readonlypassword",
    }
    assert len(cfg.db_protected_tables) == 12
    assert cfg.db_protected_tables[0] == "gavi_support_level"


def test_config_email():
    cfg = MontaguConfig("config/basic")
    assert not cfg.real_emails

    options = {"api": {"email": {"password": "changeme"}}}
    with pytest.raises(Exception, match="flow_url"):
        MontaguConfig("config/basic", options=options)

    cfg = MontaguConfig("config/complete")
    assert cfg.real_emails
    assert cfg.email_password == "changeme"
    assert cfg.email_flow_url == "fakeurl"


def test_config_ssl():
    cfg = MontaguConfig("config/complete")
    assert cfg.proxy_ssl_self_signed is False
    assert cfg.ssl_certificate == "cert"
    assert cfg.ssl_key == "k3y"
    assert cfg.dhparam == "param"

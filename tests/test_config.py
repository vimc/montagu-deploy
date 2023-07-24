import pytest

from src.montagu_deploy.config import MontaguConfig


def test_config_basic():
    cfg = MontaguConfig("config/basic")
    assert cfg.network == "montagu-network"
    assert cfg.volumes["db"] == "db_volume"
    assert cfg.volumes["emails"] == "emails"
    assert cfg.volumes["burden_estimates"] == "burden_estimate_files"
    assert cfg.container_prefix == "montagu"

    assert len(cfg.containers) == 2
    assert cfg.containers["api"] == "api"
    assert cfg.containers["db"] == "db"

    assert len(cfg.images) == 2
    assert str(cfg.images["db"]) == "vimc/montagu-db:master"
    assert str(cfg.images["api"]) == "vimc/montagu-api:master"

    assert cfg.protect_data is False

    assert cfg.db_user == "vimc"
    assert cfg.db_password == "changeme"


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

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
    assert cfg.volumes["mq"] == "mq"
    assert cfg.container_prefix == "montagu"

    assert len(cfg.containers) == 9
    assert cfg.containers["api"] == "api"
    assert cfg.containers["db"] == "db"
    assert cfg.containers["admin"] == "admin"
    assert cfg.containers["contrib"] == "contrib"
    assert cfg.containers["static"] == "static"
    assert cfg.containers["proxy"] == "proxy"
    assert cfg.containers["mq"] == "mq"
    assert cfg.containers["flower"] == "flower"
    assert cfg.containers["task_queue"] == "task-queue"

    assert len(cfg.images) == 9
    assert str(cfg.images["db"]) == "vimc/montagu-db:master"
    assert str(cfg.images["api"]) == "vimc/montagu-api:master"
    assert str(cfg.images["admin"]) == "vimc/montagu-admin-portal:master"
    assert str(cfg.images["contrib"]) == "vimc/montagu-contrib-portal:master"
    assert str(cfg.images["static"]) == "vimc/montagu-static:master"
    assert str(cfg.images["proxy"]) == "vimc/montagu-reverse-proxy:vimc-7152"
    assert str(cfg.images["mq"]) == "docker.io/redis:latest"
    assert str(cfg.images["flower"]) == "mher/flower:0.9.5"
    assert str(cfg.images["task_queue"]) == "vimc/task-queue-worker:master"

    assert cfg.mq_port == 6379
    assert cfg.flower_port == 5555
    assert cfg.youtrack_token == "faketoken"

    assert cfg.protect_data is False
    assert cfg.proxy_ssl_self_signed is True

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


def test_config_ssl():
    cfg = MontaguConfig("config/complete")
    assert cfg.proxy_ssl_self_signed is False
    assert cfg.ssl_certificate == "cert"
    assert cfg.ssl_key == "k3y"
    assert cfg.dhparam == "param"

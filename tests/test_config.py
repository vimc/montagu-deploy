from src.montagu_deploy.config import MontaguConfig


def test_config_no_proxy():
    cfg = MontaguConfig("config")
    assert cfg.network == "montagu-network"
    assert cfg.volumes["db"] == "db_volume"
    assert cfg.container_prefix == "montagu"

    assert len(cfg.containers) == 2
    assert cfg.containers["montagu-api"] == "montagu-api"
    assert cfg.containers["montagu-db"] == "montagu-db"

    assert len(cfg.images) == 2
    assert str(cfg.images["montagu-db"]) == "vimc/montagu-db:main"
    assert str(cfg.images["montagu-api"]) == "vimc/montagu-api:main"

    assert cfg.protect_data is False

    assert cfg.db_user == "changeme"
    assert cfg.db_password == "changeme"

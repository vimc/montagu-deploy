from src import config


def test_default_configuration():
    cfg = config.MontaguConfig("config")
    assert cfg.proxy_host == "localhost"
    assert cfg.proxy_port == 8443
    assert cfg.proxy_ssl_certificate is None
    assert cfg.proxy_ssl_key is None

    assert not cfg.db_persist
    assert not cfg.db_backup
    assert cfg.db_initial == "minimal"
    assert not cfg.db_update
    assert not cfg.db_replication
    assert not cfg.db_large_memory
    assert cfg.db_password_group == "fake"

    assert cfg.annex_type == "fake"

    assert not cfg.api_add_test_user

    assert not cfg.vault.url

    assert cfg.docker_network == "montagu_nw"
    assert cfg.docker_prefix == "montagu"

    assert not cfg.general_open_browser
    assert cfg.general_instance_name == "teamcity"
    assert not cfg.general_notify_slack

    assert not cfg.static_copy_static
    assert not cfg.static_copy_guidance

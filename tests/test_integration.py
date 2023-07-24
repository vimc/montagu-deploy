from unittest import mock

import docker
from constellation import docker_util

from src.montagu_deploy import cli
from src.montagu_deploy.config import MontaguConfig


def test_start_stop_status():
    path = "config/basic"
    try:
        # Start
        res = cli.main(["start", path, "--pull"])
        assert res

        cl = docker.client.from_env()
        containers = cl.containers.list()
        assert len(containers) == 2
        cfg = MontaguConfig(path)
        assert docker_util.network_exists(cfg.network)
        assert docker_util.volume_exists(cfg.volumes["db"])

        # Status
        res = cli.main(["status", "config/basic"])
        assert res

        # Stop
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            cli.main(["stop", path, "--kill", "--volumes", "--network"])
            containers = cl.containers.list()
            assert len(containers) == 0
            assert not docker_util.network_exists(cfg.network)
            assert not docker_util.volume_exists(cfg.volumes["db"])
    finally:
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            cli.main(["stop", path, "--kill", "--volumes", "--network"])

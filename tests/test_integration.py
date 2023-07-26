import os
from unittest import mock

import celery
import docker
import orderly_web
import requests
from YTClient.YTClient import YTClient
from YTClient.YTDataClasses import Command
from constellation import docker_util

from src.montagu_deploy import cli, admin
from src.montagu_deploy.config import MontaguConfig


def test_start_stop_status():
    path = "config/basic"
    try:
        # Start
        res = cli.main(["start", path, "--pull"])
        assert res

        cl = docker.client.from_env()
        containers = cl.containers.list()
        assert len(containers) == 10
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


def test_task_queue():
    orderly_config_path = "tests"
    path = "config/basic"
    cfg = MontaguConfig(path)
    try:
        orderly_web.start(orderly_config_path)

        admin.add_user(cfg, "task.queue", "task.queue", "montagu-task@imperial.ac.uk", "password")
        orderly_web.admin.add_users(orderly_config_path, ["montagu-task@imperial.ac.uk"])
        orderly_web.admin.grant(orderly_config_path, "montagu-task@imperial.ac.uk", ["*/reports.run", "*/reports.review",
                                                                                     "*/reports.read"])
        cli.main(["start", path])
        yt = YTClient('https://mrc-ide.myjetbrains.com/youtrack/',
                      token=os.environ["YOUTRACK_TOKEN"])
        app = celery.Celery(broker="redis://localhost//",
                            backend="redis://")
        sig = "run-diagnostic-reports"
        args = ["testGroup", "testDisease", "testTouchstone-1",
                "2020-11-04T12:21:15", "no_vaccination"]
        signature = app.signature(sig, args)
        versions = signature.delay().get()
        assert len(versions) == 1
        # check expected notification email was sent to fake smtp server
        emails = requests.get("http://localhost:1080/api/emails").json()
        assert len(emails) == 1
        s = "VIMC diagnostic report: testTouchstone-1 - testGroup - testDisease"
        assert emails[0]["subject"] == s
        assert emails[0]["to"]["value"][0][
                   "address"] == "minimal_modeller@example.com"  #
        issues = yt.get_issues("tag: {}".format("testTouchstone-1"))
        assert len(issues) == 1
        yt.run_command(Command(issues, "delete"))
    finally:
        # with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
        #     prompt.return_value = True
        #     cli.main(["stop", path, "--kill", "--volumes", "--network"])
        orderly_web.stop(orderly_config_path, kill=True)

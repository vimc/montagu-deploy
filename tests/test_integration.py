import os
from unittest import mock

import celery
import docker
import orderly_web
import requests
import vault_dev
from constellation import docker_util
from YTClient.YTClient import YTClient
from YTClient.YTDataClasses import Command

from src.montagu_deploy import admin, cli
from src.montagu_deploy.config import MontaguConfig
from tests.utils import http_get


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
    path = "config/ci"
    cfg = MontaguConfig(path)
    try:
        youtrack_token = os.environ["YOUTRACK_TOKEN"]
        os.environ["VAULT_AUTH_GITHUB_TOKEN"] = os.environ["VAULT_TOKEN"]
        with vault_dev.server() as s:
            cl = s.client()
            enable_github_login(cl)
            cl.write("secret/youtrack/token", value=youtrack_token)
            vault_addr = f"http://localhost:{s.port}"

            orderly_web.start(orderly_config_path)
            cli.main(["start", path, f"--option=vault.addr={vault_addr}"])

            # wait for API to be ready
            http_get("https://localhost/api/v1")

            add_task_queue_user(cfg, orderly_config_path)
            app = celery.Celery(broker="redis://localhost//", backend="redis://")
            sig = "run-diagnostic-reports"
            args = ["testGroup", "testDisease", "testTouchstone-1", "2020-11-04T12:21:15", "no_vaccination"]
            signature = app.signature(sig, args)
            versions = signature.delay().get()
            assert len(versions) == 1
            # check expected notification email was sent to fake smtp server
            emails = requests.get("http://localhost:1080/api/emails", timeout=5).json()
            assert len(emails) == 1
            subj = "VIMC diagnostic report: testTouchstone-1 - testGroup - testDisease"
            assert emails[0]["subject"] == subj
            assert emails[0]["to"]["value"][0]["address"] == "minimal_modeller@example.com"
            yt = YTClient("https://mrc-ide.myjetbrains.com/youtrack/", token=youtrack_token)
            issues = yt.get_issues("tag: {}".format("testTouchstone-1"))
            assert len(issues) == 1
            yt.run_command(Command(issues, "delete"))
    finally:
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            orderly_web.stop(orderly_config_path, kill=True)
            cli.main(["stop", path, "--kill", "--volumes", "--network"])


def add_task_queue_user(cfg, orderly_config_path):
    admin.add_user(cfg, "task.queue", "task.queue", "montagu-task@imperial.ac.uk", "password")
    admin.add_role_to_user(cfg, "task.queue", "user")
    orderly_web.admin.add_users(orderly_config_path, ["montagu-task@imperial.ac.uk"])
    orderly_web.admin.grant(
        orderly_config_path, "montagu-task@imperial.ac.uk", ["*/reports.run", "*/reports.review", "*/reports.read"]
    )


def enable_github_login(cl, path="github"):
    cl.sys.enable_auth_method(method_type="github", path=path)
    policy = """
           path "secret/*" {
             capabilities = ["read", "list"]
           }
           """

    cl.sys.create_or_update_policy(
        name="secret-reader",
        policy=policy,
    )

    cl.auth.github.map_team(team_name="robots", policies=["secret-reader"], mount_point=path)

    cl.auth.github.configure(organization="vimc", mount_point=path)

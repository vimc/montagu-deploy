import os
import ssl
import time
from unittest import mock

import celery
import docker
import pytest
import requests
import tenacity
import vault_dev
from constellation import docker_util
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID
from packit_deploy.config import PackitConfig
from packit_deploy.packit_constellation import PackitConstellation
from YTClient.YTClient import YTClient
from YTClient.YTDataClasses import Command

from src.montagu_deploy import cli
from src.montagu_deploy.config import MontaguConfig
from tests import admin
from tests.utils import http_get, run_pebble


def test_start_stop_status():
    path = "config/basic"
    try:
        # Start
        cli.main(["start", "--name", path])

        cl = docker.client.from_env()
        containers = cl.containers.list()
        assert len(containers) == 10

        cfg = MontaguConfig(path)
        assert docker_util.network_exists(cfg.network)
        assert docker_util.volume_exists(cfg.volumes["db"])

        # Status
        cli.main(["status", "--name", "config/basic"])

        # Stop
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            cli.main(["stop", "--name", path, "--kill", "--volumes", "--network"])
            containers = cl.containers.list()
            assert len(containers) == 0
            assert not docker_util.network_exists(cfg.network)
            assert not docker_util.volume_exists(cfg.volumes["db"])
    finally:
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            cli.main(["stop", "--name", path, "--kill", "--volumes", "--network"])


def test_task_queue():
    packit_config_path = "tests"
    path = "config/ci"
    cfg = MontaguConfig(path)
    packit_config = PackitConfig(packit_config_path)
    try:
        youtrack_token = os.environ["YOUTRACK_TOKEN"]
        with vault_dev.Server(export_token=True) as s:
            cl = s.client()
            cl.write("secret/youtrack/token", value=youtrack_token)
            vault_addr = f"http://localhost:{s.port}"

            packit = PackitConstellation(packit_config)
            packit.start(pull_images=True)
            cli.main(
                [
                    "start",
                    "--name",
                    path,
                    f"--option=vault.addr={vault_addr}",
                    f"--option=vault.auth.args.token={s.token}",
                ]
            )

            # wait for APIs to be ready
            http_get("https://localhost/api/v1")
            wait_for_packit_api()

            add_task_queue_user(cfg, packit)
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
            if False:
                # skip everywhere because these tests are well meaning but don't work
                yt = YTClient("https://mrc-ide.myjetbrains.com/youtrack/", token=youtrack_token)
                issues = yt.get_issues("tag: {}".format("testTouchstone-1"))
                assert len(issues) == 1
                yt.run_command(Command(issues, "delete"))
    finally:
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            PackitConstellation(packit_config).stop(kill=True)
            cli.main(["stop", "--name", path, "--kill", "--volumes", "--network"])


def test_metrics_endpoints():
    packit_config_path = "tests"
    path = "config/basic"
    packit_config = PackitConfig(packit_config_path)
    try:
        packit = PackitConstellation(packit_config)
        packit.start(pull_images=True)
        cli.main(["start", "--name", path])

        wait_for_packit_api()

        assert "jvm_info" in http_get("http://localhost:9000/metrics/packit-api")
        assert "http_requests_duration_seconds_bucket" in http_get("http://localhost:9000/metrics/outpack_server")
    finally:
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            PackitConstellation(packit_config).stop(kill=True)
            cli.main(["stop", "--name", path, "--kill", "--volumes", "--network"])


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(60))
def wait_for_packit_api():
    print("Trying to connect to packit api..")
    http_get("https://localhost/packit/api/auth/config")
    print("Success!")


def add_task_queue_user(cfg, packit):
    packit_db_container = packit.obj.containers.get("packit-db", "montagu")
    docker_util.exec_safely(
        packit_db_container,
        [
            "create-preauth-user",
            "--username",
            "task.queue",
            "--email",
            "montagu-task@imperial.ac.uk",
            "--displayname",
            "task.queue",
            "--role",
            "ADMIN",
        ],
    )

    admin.add_user(cfg, "task.queue", "task.queue", "montagu-task@imperial.ac.uk", "password")
    admin.add_role_to_user(cfg, "task.queue", "user")

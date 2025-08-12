import io
import os
import re
from contextlib import contextmanager, redirect_stdout
from unittest import mock

import pytest

from src.montagu_deploy import cli
from src.montagu_deploy.cli import prompt_yes_no, verify_data_loss
from src.montagu_deploy.config import MontaguConfig


@contextmanager
def transient_working_directory(path):
    origin = os.getcwd()
    try:
        if path is not None:
            os.chdir(path)
        yield
    finally:
        if path is not None:
            os.chdir(origin)


def test_parse_args():
    res = cli.parse_args(["start", "--name=config/basic", "--pull"])
    assert res[0] == "config/basic"
    assert res[1] is None
    assert res[2] == []
    args = res[3]
    assert args.action == "start"
    assert args.pull is True
    assert args.kill is False
    assert args.volumes is False
    assert args.network is False

    res = cli.parse_args(["start", "--name=config/basic", "--extra=extra.yml"])
    assert res[1] == "extra.yml"

    res = cli.parse_args(["start", "--name=config/basic", "--option=a=x", "--option=b.c=y"])
    assert res[2] == [{"a": "x"}, {"b": {"c": "y"}}]

    res = cli.parse_args(["stop", "--name=config/basic", "--kill", "--network", "--volumes"])
    args = res[3]
    assert args.action == "stop"
    assert args.pull is False
    assert args.kill is True
    assert args.volumes is True
    assert args.network is True

    res = cli.parse_args(["status", "--name=config/basic"])
    args = res[3]
    assert args.action == "status"

    res = cli.parse_args(["--version"])
    args = res[3]
    assert args.version is True


def test_version(capsys):
    cli.main(["--version"])
    out, err = capsys.readouterr()
    assert re.match(r"\d+\.\d+\.\d+", out)


def test_args_passed_to_start():
    with mock.patch("src.montagu_deploy.cli.montagu_start") as f:
        cli.main(["start", "--name=config/basic"])

    assert f.called
    assert f.call_args[0][1].pull is False

    with mock.patch("src.montagu_deploy.cli.montagu_start") as f:
        cli.main(["start", "--name=config/basic", "--pull"])

    assert f.called
    assert f.call_args[0][1].pull is True


def test_args_passed_to_stop():
    with mock.patch("src.montagu_deploy.cli.montagu_stop") as f:
        cli.main(["stop", "--name=config/basic"])

    assert f.called
    assert f.call_args[0][1].kill is False
    assert f.call_args[0][1].network is False
    assert f.call_args[0][1].volumes is False

    with mock.patch("src.montagu_deploy.cli.montagu_stop") as f:
        cli.main(["stop", "--name=config/basic", "--volumes", "--network"])

    assert f.called
    assert f.call_args[0][1].kill is False
    assert f.call_args[0][1].network is True
    assert f.call_args[0][1].volumes is True


def test_args_passed_to_configure():
    with mock.patch("src.montagu_deploy.cli.montagu_configure") as f:
        cli.main(["configure", "config/basic"])

    assert f.call_count == 1
    assert f.mock_calls[0] == mock.call("config/basic")


def test_can_parse_extra_certbot_args():
    res = cli.parse_args(["renew-certificate", "--name=config/basic", "--", "--force-renewal"])
    assert res[0] == "config/basic"
    assert res[1] is None
    assert res[2] == []
    args = res[3]
    assert args.action == "renew-certificate"
    assert args.extra_args == ["--force-renewal"]


def test_verify_data_loss_called():
    f = io.StringIO()
    with redirect_stdout(f):
        with mock.patch("src.montagu_deploy.cli.verify_data_loss") as verify:
            verify.return_value = True
            cli.main(["stop", "--name=config/basic", "--volumes"])

    assert verify.called


def test_verify_data_loss_not_called():
    f = io.StringIO()
    with redirect_stdout(f):
        with mock.patch("src.montagu_deploy.cli.verify_data_loss") as verify:
            verify.return_value = True
            cli.main(["stop", "--name=config/basic"])

    assert not verify.called


def test_verify_data_loss_warns_if_loss():
    cfg = MontaguConfig("config/basic")
    f = io.StringIO()
    with redirect_stdout(f):
        with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
            prompt.return_value = True
            verify_data_loss(cfg)

    assert prompt.called
    assert "WARNING! PROBABLE IRREVERSIBLE DATA LOSS!" in f.getvalue()


def test_verify_data_loss_throws_if_loss():
    cfg = MontaguConfig("config/basic")
    with mock.patch("src.montagu_deploy.cli.prompt_yes_no") as prompt:
        prompt.return_value = False
        with pytest.raises(Exception, match="Not continuing"):
            verify_data_loss(cfg)


def test_verify_data_prevents_unwanted_loss():
    cfg = MontaguConfig("config/basic")
    cfg.protect_data = True
    msg = "Cannot remove volumes with this configuration"
    with mock.patch("src.montagu_deploy.cli.prompt_yes_no"):
        with pytest.raises(Exception, match=msg):
            verify_data_loss(cfg)


def test_prompt_is_quite_strict():
    assert prompt_yes_no(lambda _: "yes")
    assert not prompt_yes_no(lambda _: "no")
    assert not prompt_yes_no(lambda _: "Yes")
    assert not prompt_yes_no(lambda _: "Great idea!")
    assert not prompt_yes_no(lambda _: "")


def test_bad_option_format():
    with pytest.raises(Exception, match="Invalid option"):
        cli.parse_args(["start", "--name=config/basic", "--option=one:two"])


def test_invalid_option_type():
    with pytest.raises(Exception, match="Invalid value"):
        cli.parse_args(["start", "--name=config/basic", "--option=one={2}"])


def test_can_read_identity(tmp_path):
    with transient_working_directory(tmp_path):
        assert cli._read_identity(required=False) is None
        assert cli._read_identity("foo") == "foo"
        with pytest.raises(Exception, match="not yet configured"):
            cli._read_identity()
        with open(".montagu_identity", "w") as f:
            f.write("foo\n")
        assert cli._read_identity() == "foo"


def test_can_configure_montagu(tmp_path, mocker):
    with transient_working_directory(tmp_path):
        mocker.patch("src.montagu_deploy.cli.MontaguConfig")
        cli.montagu_configure("foo")
        assert cli._read_identity() == "foo"
        cli.montagu_configure("foo")
        assert cli._read_identity() == "foo"
        with pytest.raises(Exception, match="already configured as 'foo'"):
            cli.montagu_configure("bar")
        assert cli._read_identity() == "foo"

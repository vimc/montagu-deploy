import ssl
import time
import urllib

import docker
from constellation import docker_util

from src.montagu_deploy.config import MontaguConfig
from src.montagu_deploy.montagu_constellation import MontaguConstellation


def test_start_and_stop():
    cfg = MontaguConfig("config/basic")
    obj = MontaguConstellation(cfg)

    obj.start()

    cl = docker.client.from_env()
    containers = cl.containers.list()
    assert len(containers) == 10

    assert docker_util.network_exists(cfg.network)
    assert docker_util.volume_exists(cfg.volumes["db"])
    assert docker_util.volume_exists(cfg.volumes["burden_estimates"])
    assert docker_util.volume_exists(cfg.volumes["emails"])
    assert docker_util.volume_exists(cfg.volumes["static"])
    assert docker_util.volume_exists(cfg.volumes["static_logs"])
    assert docker_util.volume_exists(cfg.volumes["mq"])
    assert docker_util.volume_exists(cfg.volumes["templates"])
    assert docker_util.volume_exists(cfg.volumes["guidance"])

    assert docker_util.container_exists("montagu-api")
    assert docker_util.container_exists("montagu-db")
    assert docker_util.container_exists("montagu-proxy")
    assert docker_util.container_exists("montagu-admin")
    assert docker_util.container_exists("montagu-contrib")
    assert docker_util.container_exists("montagu-static")
    assert docker_util.container_exists("montagu-mq")
    assert docker_util.container_exists("montagu-flower")
    assert docker_util.container_exists("montagu-task-queue")

    obj.stop(kill=True)


def test_api_configured():
    cfg = MontaguConfig("config/basic")
    obj = MontaguConstellation(cfg)

    obj.start()

    api = get_container(cfg, "api")
    api_config = docker_util.string_from_container(api, "/etc/montagu/api/config.properties").split("\n")

    assert "app.url=https://localhost/api" in api_config
    assert "db.host=db" in api_config
    assert "db.username=vimc" in api_config
    assert "db.password=changeme" in api_config
    assert "allow.localhost=False" in api_config
    assert "upload.dir=/upload_dir" in api_config
    assert "email.mode=real" not in api_config

    # Once the db is configured we can test that the API is running by actually making a request to it
    # but for now, just check the go_signal has been written
    go = docker_util.string_from_container(api, "/etc/montagu/api/go_signal")
    assert go is not None

    obj.stop(kill=True)

    cfg = MontaguConfig("config/complete")
    obj = MontaguConstellation(cfg)

    obj.start()
    api = get_container(cfg, "api")
    api_config = docker_util.string_from_container(api, "/etc/montagu/api/config.properties").split("\n")
    assert "email.mode=real" in api_config
    assert "email.password=changeme" in api_config
    assert "flow.url=fakeurl" in api_config

    obj.stop(kill=True)


def test_proxy_configured_self_signed():
    cfg = MontaguConfig("config/basic")
    obj = MontaguConstellation(cfg)

    obj.start()

    api = get_container(cfg, "proxy")
    cert = docker_util.string_from_container(api, "/etc/montagu/proxy/certificate.pem")
    key = docker_util.string_from_container(api, "/etc/montagu/proxy/ssl_key.pem")
    param = docker_util.string_from_container(api, "/etc/montagu/proxy/dhparam.pem")
    assert cert is not None
    assert key is not None
    assert param is not None

    res = http_get("https://localhost")
    assert "Montagu" in res

    obj.stop(kill=True)


def test_proxy_configured_ssl():
    cfg = MontaguConfig("config/complete")
    obj = MontaguConstellation(cfg)

    obj.start()

    api = get_container(cfg, "proxy")
    cert = docker_util.string_from_container(api, "/etc/montagu/proxy/certificate.pem")
    key = docker_util.string_from_container(api, "/etc/montagu/proxy/ssl_key.pem")
    param = docker_util.string_from_container(api, "/etc/montagu/proxy/dhparam.pem")
    assert cert == "cert"
    assert key == "k3y"
    assert param == "param"

    obj.stop(kill=True)


def get_container(cfg, name):
    cl = docker.client.from_env()
    return cl.containers.get(f"{cfg.container_prefix}-{cfg.containers[name]}")


# Because we wait for a go signal to come up, we might not be able to
# make the request right away:
def http_get(url, retries=5, poll=0.5):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for _i in range(retries):
        try:
            r = urllib.request.urlopen(url, context=ctx)  # noqa
            return r.read().decode("UTF-8")
        except (urllib.error.URLError, ConnectionResetError) as e:
            print("sleeping...")
            time.sleep(poll)
            error = e
    raise error

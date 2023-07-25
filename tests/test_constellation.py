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
    assert len(containers) == 3

    assert docker_util.network_exists(cfg.network)
    assert docker_util.volume_exists(cfg.volumes["db"])
    assert docker_util.volume_exists(cfg.volumes["burden_estimates"])

    assert docker_util.container_exists("montagu-api")
    assert docker_util.container_exists("montagu-db")
    assert docker_util.container_exists("montagu-proxy")

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

    res = http_get("https://localhost/api/")
    assert "test" in res

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


def test_proxy_configured():
    cfg = MontaguConfig("config/basic")
    obj = MontaguConstellation(cfg)

    obj.start()

    api = get_container(cfg, "proxy")
    cert = docker_util.string_from_container(api, "/etc/montagu/proxy/certificate.pem")
    assert cert is not None

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
    for i in range(retries):
        try:
            r = urllib.request.urlopen(url, context=ctx)
            return r.read().decode("UTF-8")
        except (urllib.error.URLError, ConnectionResetError) as e:
            print("sleeping...")
            time.sleep(poll)
            error = e
    raise error

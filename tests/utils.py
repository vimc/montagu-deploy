import json
import ssl
import time
import urllib
from contextlib import contextmanager

import docker
from constellation import docker_util


# Because we wait for a go signal to come up, we might not be able to
# make the request right away:
def http_get(url, retries=10, poll=0.5):
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


# Create a container, as a context manager.
# This container will be stopped and removed when the context manager exits.
@contextmanager
def create_container(image, **kwargs):
    container = docker.from_env().containers.create(image, detach=True, **kwargs)
    try:
        yield container
    finally:
        container.stop()
        container.remove()


# Run the Pebble ACME server.
@contextmanager
def run_pebble(**kwargs):
    env = {
        "PEBBLE_WFE_NONCEREJECT": 0,
        "PEBBLE_VA_NOSLEEP": 1,
    }
    config = {
        "pebble": {
            "listenAddress": "0.0.0.0:443",
            # These are baked into the docker image already
            "certificate": "test/certs/localhost/cert.pem",
            "privateKey": "test/certs/localhost/key.pem",
            # This is the port pebble connects to to fetch well-known challenges
            "httpPort": 80,
        }
    }

    with create_container(
        "ghcr.io/letsencrypt/pebble:latest", command=["-config", "/config.json"], environment=env, **kwargs
    ) as container:
        docker_util.string_into_container(json.dumps(config), container, "/config.json")
        container.start()
        yield

import ssl
import time
import urllib

# Because we wait for a go signal to come up, we might not be able to
# make the request right away:
import docker


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


def get_container(cfg, name):
    cl = docker.client.from_env()
    return cl.containers.get(f"{cfg.container_prefix}-{cfg.containers[name]}")

# https://github.com/certbot/certbot/blob/v3.0.1/acme/examples/http01_example.py

import os.path
import sys
import tarfile
from tempfile import TemporaryFile

import docker
from constellation import docker_util

# The Docker API uses Go's FileMode values. These are different from the
# standard values, as found in eg. stat.S_IFLNK.
# https://pkg.go.dev/io/fs#FileMode
DOCKER_MODE_TYPE = 0x8F280000
DOCKER_MODE_SYMLINK = 0x8000000


def read_file(container, path, *, follow_links=False):
    stream, status = container.get_archive(path)
    if follow_links and (status["mode"] & DOCKER_MODE_TYPE) == DOCKER_MODE_SYMLINK:
        return read_file(container, status["linkTarget"], follow_links=False)
    else:
        with TemporaryFile() as f:
            for d in stream:
                f.write(d)
            f.seek(0)

            with tarfile.open(fileobj=f) as tar:
                return tar.extractfile(os.path.basename(path)).read()


def obtain_certificate(cfg, extra_args):
    docker_util.ensure_volume(cfg.volumes["certbot"])
    docker_util.ensure_volume(cfg.volumes["acme-challenge"])

    environment = {}
    command = [
        "certonly",
        "--non-interactive",
        "--agree-tos",
        "--webroot",
        "--webroot-path=/var/www",
        f"--email={cfg.acme_email}",
        f"--domain={cfg.hostname}",
    ]

    for d in cfg.acme_additional_domains:
        command.append(f"--domain={d}")

    if cfg.acme_server:
        command.append(f"--server={cfg.acme_server}"),
    if cfg.acme_no_verify_ssl:
        command.append("--no-verify-ssl")
        environment["PYTHONWARNINGS"] = "ignore:Unverified HTTPS request"

    command.extend(extra_args)

    image = "certbot/certbot"
    container = docker.from_env().containers.run(
        image,
        command=command,
        detach=True,
        volumes={
            cfg.volumes["acme-challenge"]: {
                "bind": "/var/www/.well-known/acme-challenge",
                "mode": "rw",
            },
            cfg.volumes["certbot"]: {
                "bind": "/etc/letsencrypt",
                "mode": "rw",
            },
        },
        network=cfg.network,
        environment=environment,
    )

    try:
        exit_status = container.wait()["StatusCode"]

        sys.stderr.write(container.logs().decode("utf-8"))
        if exit_status != 0:
            raise docker.errors.ContainerError(container, exit_status, command, image, None)

        cert = read_file(container, f"/etc/letsencrypt/live/{cfg.hostname}/fullchain.pem", follow_links=True)
        key = read_file(container, f"/etc/letsencrypt/live/{cfg.hostname}/privkey.pem", follow_links=True)

        return (cert, key)

    finally:
        container.remove()

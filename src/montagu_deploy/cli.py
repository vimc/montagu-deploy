"""Usage:
  montagu --version
  montagu configure <path>
  montagu start [--name=PATH] [--extra=PATH] [--option=OPTION]... [--pull]
  montagu status [--name=PATH]
  montagu stop [--name=PATH] [--volumes] [--network] [--kill] [--force]
    [--extra=PATH] [--option=OPTION]...
  montagu renew-certificate [--name=PATH] [--option=OPTION]... [--] [ARGS...]

Options:
  --name=PATH      Override the configured name, use with care!
  --extra=PATH     Path, relative to <path>, of yml file of additional
                   configuration
  --option=OPTION  Additional configuration options, in the form key=value
                   Use dots in key for hierarchical structure, e.g., a.b=value
                   This argument may be repeated to provide multiple arguments
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
"""

from pathlib import Path

import docopt
import yaml

import montagu_deploy.__about__ as about
from montagu_deploy.certbot import obtain_certificate
from montagu_deploy.config import MontaguConfig
from montagu_deploy.montagu_constellation import montagu_constellation, proxy_update_certificate


def main(argv=None):
    path, extra, options, args = parse_args(argv)
    if args.version:
        print(about.__version__)
    else:
        if args.action == "configure":
            montagu_configure(path)
            return

        path = _read_identity(path)
        cfg = MontaguConfig(path, extra, options)
        obj = montagu_constellation(cfg)
        if args.action == "start":
            montagu_start(obj, args)
        elif args.action == "status":
            montagu_status(obj)
        elif args.action == "stop":
            montagu_stop(obj, args, cfg)
        elif args.action == "renew-certificate":
            montagu_renew_certificate(obj, cfg, args.extra_args)


def parse_args(argv=None):
    opts = docopt.docopt(__doc__, argv)
    path = opts["<path>"] if opts["configure"] else opts["--name"]
    extra = opts["--extra"]
    options = parse_option(opts)
    return path, extra, options, MontaguArgs(opts)


def montagu_configure(name):
    prev = _read_identity(required=False)
    if prev:
        if prev != name:
            msg = (
                f"This montagu instance is already configured as '{prev}', "
                f"but you are trying to reconfigure it as '{name}'. "
                "If you really want to do do this, then delete the file "
                "'{IDENTITY_FILE}' from this directory and try again"
            )
            raise Exception(msg)
        else:
            print(f"Montagu already configured as '{name}")
    else:
        # Check that we can read the configuration before saving it.
        MontaguConfig(name)
        with IDENTITY_FILE.open("w") as f:
            f.write(name)
        print(f"Configured montagu as '{name}")


def montagu_start(obj, args):
    obj.start(pull_images=args.pull)


def montagu_status(obj):
    obj.status()


def montagu_renew_certificate(obj, cfg, extra_args):
    if cfg.ssl_mode != "acme":
        msg = "Proxy is not configured to use automatic certificates"
        raise Exception(msg)

    print("Renewing certificates")
    (cert, key) = obtain_certificate(cfg, extra_args)

    container = obj.containers.get("proxy", cfg.container_prefix)
    proxy_update_certificate(container, cert, key, reload=True)


def montagu_stop(obj, args, cfg):
    if args.volumes:
        verify_data_loss(cfg)
    obj.stop(kill=args.kill, remove_network=args.network, remove_volumes=args.volumes)


def verify_data_loss(cfg):
    if cfg.protect_data:
        err = "Cannot remove volumes with this configuration"
        raise Exception(err)
    else:
        print(
            """WARNING! PROBABLE IRREVERSIBLE DATA LOSS!
You are about to delete the data volumes. This action cannot be undone
and will result in the irreversible loss of *all* data associated with
the application. This includes all databases etc."""
        )
    if not prompt_yes_no():
        msg = "Not continuing"
        raise Exception(msg)


def prompt_yes_no(get_input=input):
    return get_input("\nContinue? [yes/no] ") == "yes"


def parse_option(args):
    return [string_to_dict(x) for x in args["--option"]]


def string_to_dict(string):
    """Convert a configuration option a.b.c=x to a dictionary
    {"a": {"b": "c": x}}"""
    # Won't deal with dots embedded within quotes but that's ok as
    # that should not be allowed generally.
    try:
        key, value = string.split("=")
    except ValueError as err:
        msg = f"Invalid option '{string}', expected option in form key=value"
        raise Exception(msg) from err
    value = yaml_atom_parse(value)
    for k in reversed(key.split(".")):
        value = {k: value}
    return value


def yaml_atom_parse(x):
    ret = yaml.safe_load(x)
    if type(ret) not in [bool, int, float, str]:
        msg = f"Invalid value '{x}' - expected simple type"
        raise Exception(msg)
    return ret


class MontaguArgs:
    def __init__(self, args):
        if args["start"]:
            self.action = "start"
        elif args["status"]:
            self.action = "status"
        elif args["stop"]:
            self.action = "stop"
        elif args["renew-certificate"]:
            self.action = "renew-certificate"
        elif args["configure"]:
            self.action = "configure"

        self.pull = args["--pull"]
        self.kill = args["--kill"]
        self.volumes = args["--volumes"]
        self.network = args["--network"]
        self.version = args["--version"]
        self.extra_args = args["ARGS"]


IDENTITY_FILE = Path(".montagu_identity")


def _read_identity(name=None, *, required=True):
    if name:
        return name
    if IDENTITY_FILE.exists():
        with IDENTITY_FILE.open() as f:
            return f.read().strip()
    if required:
        msg = "Montagu identity is not yet configured; run 'montagu configure <name>' first"
        raise Exception(msg)
    return None

"""Usage:
  montagu --version
  montagu start <path> [--extra=PATH] [--option=OPTION]... [--pull]
  montagu status <path>
  montagu stop <path> [--volumes] [--network] [--kill] [--force]
    [--extra=PATH] [--option=OPTION]...
  montagu renew-certificate <path> [--force-renewal] [--expand] [--option=OPTION]...

Options:
  --extra=PATH     Path, relative to <path>, of yml file of additional
                   configuration
  --option=OPTION  Additional configuration options, in the form key=value
                   Use dots in key for hierarchical structure, e.g., a.b=value
                   This argument may be repeated to provide multiple arguments
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
  --force          Force stop even if containers are corrupted and cannot
                   signal their running configuration, or if config cannot be
                   parsed. Use with extra and/or option to force stop with
                   configuration options.
  --force-renewal  Renew the certificate, even if the current one isn't close to
                   expiry.
  --expand         If an existing certificate is a strict subset of the
                   requested names, always expand and replace it with the
                   additional names.
"""

import docopt
import yaml

import montagu_deploy.__about__ as about
from montagu_deploy.certbot import obtain_certificate
from montagu_deploy.config import MontaguConfig
from montagu_deploy.montagu_constellation import montagu_constellation, proxy_update_certificate


def main(argv=None):
    path, extra, options, args = parse_args(argv)
    if args.version:
        return about.__version__
    else:
        cfg = MontaguConfig(path, extra, options)
        obj = montagu_constellation(cfg)
        if args.action == "start":
            montagu_start(obj, args)
        elif args.action == "status":
            montagu_status(obj)
        elif args.action == "stop":
            montagu_stop(obj, args, cfg)
        elif args.action == "renew-certificate":
            montagu_renew_certificate(obj, cfg,
                                      force_renewal=args.force_renewal,
                                      expand=args.expand)
        return True


def parse_args(argv=None):
    opts = docopt.docopt(__doc__, argv)
    path = opts["<path>"]
    extra = opts["--extra"]
    options = parse_option(opts)
    return path, extra, options, MontaguArgs(opts)


def montagu_start(obj, args):
    obj.start(pull_images=args.pull)


def montagu_status(obj):
    obj.status()


def montagu_renew_certificate(obj, cfg, **kwargs):
    if cfg.ssl_mode != "acme":
        msg = "Proxy is not configured to use automatic certificates"
        raise Exception(msg)

    print("Renewing certificates")
    (cert, key) = obtain_certificate(cfg, **kwargs)

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

        self.pull = args["--pull"]
        self.kill = args["--kill"]
        self.volumes = args["--volumes"]
        self.network = args["--network"]
        self.version = args["--version"]
        self.force_renewal = args["--force-renewal"]
        self.expand = args["--expand"]

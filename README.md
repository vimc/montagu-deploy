# montagu-deploy

[![PyPI - Version](https://img.shields.io/pypi/v/montagu-deploy.svg)](https://pypi.org/project/montagu-deploy)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/montagu-deploy.svg)](https://pypi.org/project/montagu-deploy)

-----

This is the command-line tool for deploying Montagu. It is a [Hatch](https://hatch.pypa.io/latest/install/) project.

## Installation

```console
pip install montagu-deploy
```

## Usage

```
$ montagu --help
Usage:
  montagu --version
  montagu start <path> [--extra=PATH] [--option=OPTION]... [--pull]
  montagu status <path>
  montagu stop <path> [--volumes] [--network] [--kill] [--force]
    [--extra=PATH] [--option=OPTION]...

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
```

Here `<path>` is the path to a directory that contains a configuration file `montagu.yml`.

## Dev requirements

1. [Python3](https://www.python.org/downloads/) (>= 3.7)
2. [Hatch](https://hatch.pypa.io/latest/install/)

## Test and lint

For all integration tests to pass, you will need 2 environment variables:
1. `YOUTRACK_TOKEN` - a token for accessing the YT API
2. `VAULT_TOKEN` - a github PAT for a user in the vimc robots team.

1. `hatch run test`
2. `hatch run lint:fmt`

To get coverage reported locally in the console, use `hatch run cov`. 
On CI, use `hatch run cov-ci` to generate an xml report.

## Build

```console
hatch build
```

## Install from local sources

1. `hatch build`
2. `pip install dist/montagu_deploy-{version}.tar.gz`

## Publish to PyPi

```console
hatch publish
```

## License

`montagu-deploy` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.


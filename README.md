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

## License

`montagu-deploy` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.


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
$ montagu configure <path>
$ montagu start --pull
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

## License

`montagu-deploy` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Publishing to PyPI

Automatically publish to [PyPI](https://pypi.org/project/montagu-deploy).  Assuming a version number `0.1.2`:

* Create a [release on github](https://github.com/vimc/montagu-deploy/releases/new)
* Choose a tag -> Create a new tag: `v0.1.2`
* Use this version as the description
* Optionally describe the release
* Click "Publish release"
* This triggers the release workflow and the package will be available on PyPI in a few minutes

Settings are configured [here on PyPI](https://pypi.org/manage/project/montagu-deploy/settings/publishing)

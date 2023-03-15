# tox-min-req

[![PyPI - Version](https://img.shields.io/pypi/v/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![Development Status](https://img.shields.io/pypi/status/napari.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha)
[![Tests](https://github.com/Czaki/tox-min-req/actions/workflows/test.yaml/badge.svg)](https://github.com/Czaki/tox-min-req/actions/workflows/test.yaml)
[![PyPI - License](https://img.shields.io/pypi/l/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![codecov](https://codecov.io/gh/Czaki/tox-min-req/branch/main/graph/badge.svg?token=QrHmd50nYq)](https://codecov.io/gh/Czaki/tox-min-req)
-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Usage](#usage)

tox-min-req is a [tox](https://tox.wiki/) plugin that simplify the 
minimum requirements testing.

The minimum requirements is to validate if minimum requirements are 
satisfied.

To use this plugin you need to use `MIN_REQ` environment variable either in call or in `setenv` section 
of tox configuration.

## Installation

```console
pip install tox-min-req
```

## License

`tox-min-req` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.


# Usage

The basic usage is to set the `MIN_REQ` environment variable to `1`

```bash
$ MIN_REQ=1 tox -e py37
```

## Configuration options

The `tox-min-req` plugin allow to provide following environment configuration options:

* `min_req` - set to `1` to enable the minimum requirements testing, could be used instead of environment variable.
* `min_req_constraints` - list of additional constrains that will be used to generate the constrains file. 
   It could be useful in following scenarios:
  * Some of dependencies in old version is incompatible with its dependencies in latest version. (see Known issues)
  * Maintainers would like to test also some problematic dependencies in old version, but not oldest supported version.

```ini
[tox]
envlist = py310

[testenv]
extras = test
recreate = True
commands = pytest test_file.py
min_req = 1
min_req_constraints=
    coverage==6.5.0
    babel==2.6.0
    six==1.14.0
    -r {project_dir}/constraints.txt
```

Please note that `-r {project_dir}/constraints.txt` will be put in generated constrains file, not parsed.

# Known issues

## Pinning only direct dependencies

As this plugin parse only `setup.cfg` or `pyproject.toml` file, it is not possible to pin the indirect dependencies.
To provide the indirect dependencies pinning, the `min_req_constraints` environment configuration option could be used.

## Space in constrains file path
`pip` is using the space as file path separator in `PIP_CONSTRAINT` variable. 
The plugin is storing the generated constrains file in the `.tox` temporary directory.
If the path to the temporary directory contains space, the `pip` will not be able to find the constrains file.

In such situation there is a need to set the `TOX_MIN_REQ_CONSTRAINTS` environment variable
to the path where constrains file could be written.

```bash
$ TOX_MIN_REQ_CONSTRAINTS=/tmp MIN_REQ=1 tox -e py37
```

It is also possible to use the `--min-req-constraints-path` command line option to set the path to the constrains file.

```bash
$ tox --min-req-constraints-path=/tmp -e py37
``` 

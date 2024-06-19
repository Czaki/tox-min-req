# tox-min-req

[![PyPI - Version](https://img.shields.io/pypi/v/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![Development Status](https://img.shields.io/pypi/status/napari.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha)
[![Tests](https://github.com/Czaki/tox-min-req/actions/workflows/test.yaml/badge.svg)](https://github.com/Czaki/tox-min-req/actions/workflows/test.yaml)
[![PyPI - License](https://img.shields.io/pypi/l/tox-min-req.svg)](https://pypi.org/project/tox-min-req)
[![codecov](https://codecov.io/gh/Czaki/tox-min-req/branch/main/graph/badge.svg?token=QrHmd50nYq)](https://codecov.io/gh/Czaki/tox-min-req)
[![Downloads](https://static.pepy.tech/badge/tox-min-req/month)](https://pepy.tech/project/tox-min-req)
-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Usage](#usage)

tox-min-req is a [tox](https://tox.wiki/) plugin that simplifies  
minimum requirements (min-req) testing.

Minimum requirements testing is important to validate whether the minimum requirements are 
satisfied.

After installing, to use this plugin you need to use `MIN_REQ` environment variable either in the call
(e.g. `MIN_REQ=1 tox -e py38-linux-pyqt5`) or in `setenv` section of your tox configuration.

## Why use this instead of `deps` attribute of the tox env section?

One alternative solution is to use the `deps` section in tox configuration to install min-req dependecies. 

However, packages from `deps` and the actual package to be tested are installed in two independent steps. This means that 
some of the min-req dependencies could be upgraded or downgraded when installing the actual package. 

The `PIP_CONSTRAINT` and `UV_CONSTRAINT` variables are used to pin the dependencies; it will apply to the call of `pip install`
during dependency resolving. 


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

The `tox-min-req` plugin allows one to provide the following environment configuration options:

* `min_req` - set to `1` to enable the minimum requirements testing; can be used instead of setting the environment variable.
* `min_req_constraints` - list of additional constraints that will be used to generate the constraints file. 
   This is useful in following scenarios:
  * Some of dependencies of an old version are incompatible with  dependencies in latest version (see Known issues, below).
  * Maintainers would like to also test some problematic dependencies an old version, but not the oldest supported version.

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

Please note that `-r {project_dir}/constraints.txt` will be put in the generated constraints file—it will not be parsed.

# Known issues

## Pinning only direct dependencies

Because this plugin only parses `setup.cfg` or `pyproject.toml` files, it is not possible to pin any indirect dependencies.
To pin indirect dependencies, the `min_req_constraints` environment configuration option should be used.

## Spaces in the constraints file path
`pip` uses spaces as file path separators in the `PIP_CONSTRAINT` variable. 
This plugin stores the generated constraints file in a `.tox` temporary directory.
As a result, if the path to the temporary directory contains spaces, then `pip` will not be able to find the constraints file.

In such a scenatio, one needs to set the `TOX_MIN_REQ_CONSTRAINTS` environment variable
to the path where constraints file can be written.

```bash
$ TOX_MIN_REQ_CONSTRAINTS=/tmp MIN_REQ=1 tox -e py37
```

It is also possible to use the `--min-req-constraints-path` command line option to set the path to the constraints file.

```bash
$ tox --min-req-constraints-path=/tmp -e py37
``` 

import sys
from typing import TYPE_CHECKING

import pytest
from tox.pytest import ToxProjectCreator, init_fixture  # noqa: F401, TCH002

if TYPE_CHECKING:
    from pathlib import Path

tox_ini_template = """
[tox]
envlist = py{env}

[testenv]
extras = test
recreate = True
commands = pytest test_file.py
"""

setup_cfg_template = """
[metadata]
name = test_package
version = 0.0.1
author = Grzegorz Bokota

[options]
packages = sample_package
install_requires =
    six>=1.13.0
    click>=7.1.2
    
[options.extras_require]
test =
    pytest>=7.1.0
"""

setup_py_template = """
from setuptools import setup

setup()
"""


pyproject_toml_template = """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test_package"
version = "0.0.1"
description = "Test package"
dependencies = [
    "six>=1.13.0",
    "click>=7.1.2",
]

[project.optional-dependencies]
test = [
    "pytest>=7.1.0",
]
"""

test_file_template = """
import pytest
import six

import sample_package

def test_pytest_version():
    assert pytest.__version__ {cmp} "7.1.0"
    
def test_six_version():
    assert six.__version__ {cmp} "1.13.0"
    
def test_sample_package():
    assert sample_package.sample_function() == 42
"""


@pytest.mark.parametrize(("cmp", "req"), [("==", "1"), ("!=", "0")])
def test_tox_project_creator_setup_sfg(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    cmp: str,
    req: str,
) -> None:
    monkeypatch.setenv("MIN_REQ", req)
    env = f"{sys.version_info[0]}{sys.version_info[1]}"
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template.format(cmp=cmp),
            "setup.py": setup_py_template,
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


@pytest.mark.parametrize(("cmp", "req"), [("==", "1"), ("!=", "0")])
def test_tox_project_creator_pyproject(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    cmp: str,
    req: str,
) -> None:
    monkeypatch.setenv("MIN_REQ", req)
    env = f"{sys.version_info[0]}{sys.version_info[1]}"
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env),
            "pyproject.toml": pyproject_toml_template,
            "test_file.py": test_file_template.format(cmp=cmp),
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()

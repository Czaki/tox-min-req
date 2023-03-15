import shutil
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
    coverage
"""

setup_py_template = """
from setuptools import setup

setup()
"""


pyproject_toml_template_base = """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test_package"
version = "0.0.1"
description = "Test package"
dependencies = [
    {deps}
]

[project.optional-dependencies]
test = [
    "pytest>=7.1.0",
]
"""

pyproject_toml_template = pyproject_toml_template_base.format(deps='    "six>=1.13.0",\n    "click>=7.1.2",\n')


test_file_template = """
import pytest
import six
import click

import sample_package

def test_pytest_version():
    assert pytest.__version__ {cmp} "7.1.0"
    
def test_six_version():
    assert six.__version__ {cmp} "1.13.0"
    
def test_click_version():
    assert click.__version__ {cmp} "7.1.2"
    
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


def test_preserve_constrains(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    tmp_path: "Path",
) -> None:
    monkeypatch.setenv("MIN_REQ", "1")
    (tmp_path / "constraints.txt").write_text("coverage==6.5.0")
    monkeypatch.setenv("PIP_CONSTRAINT", str(tmp_path / "constraints.txt"))
    env = f"{sys.version_info[0]}{sys.version_info[1]}"

    test_file_template_ = test_file_template.format(cmp="==")
    test_file_template_ += 'import coverage\ndef test_click_version():\n    assert coverage.__version__ == "6.5.0"\n'
    test_file_template_ += (
        'import os\ndef test_environ():\n    assert len(os.environ["PIP_CONSTRAINT"].split(" ")) == 2\n'
    )
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template_,
            "setup.py": setup_py_template,
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


test_file_template_six = """
import pytest
import six

import sample_package

def test_pytest_version():
    assert pytest.__version__ == "7.1.0"

def test_six_version():
    assert six.__version__ == "{six_version}"

def test_sample_package():
    assert sample_package.sample_function() == 42
"""


PYTHON_VER_LI = [
    ("3.7", "37", "1.10.0"),
    ("3.8", "38", "1.11.0"),
    ("3.9", "39", "1.12.0"),
    ("3.10", "310", "1.13.0"),
    ("3.11", "311", "1.14.0"),
]


@pytest.mark.parametrize(("python", "env", "target_six_version"), PYTHON_VER_LI)
def test_proper_version_handle(  # noqa: PLR0913
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    python: str,
    env: str,
    target_six_version: str,
) -> None:
    if not shutil.which(f"python{python}"):
        pytest.skip(f"Python {python} is not installed")
    monkeypatch.setenv("MIN_REQ", "1")
    constrains_list = "\n".join(
        f"    'six>={six_version}; python_version == \"{python_version}\"',"
        for python_version, _, six_version in PYTHON_VER_LI
    )
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env),
            "pyproject.toml": pyproject_toml_template_base.format(deps=constrains_list),
            "test_file.py": test_file_template_six.format(six_version=target_six_version),
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")
    result.assert_success()

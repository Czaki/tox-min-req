import os
import shutil
import sys
from typing import TYPE_CHECKING

import pytest
from tox.pytest import ToxProjectCreator, init_fixture  # noqa: F401

if TYPE_CHECKING:
    from pathlib import Path

tox_ini_template = """
[tox]
envlist = py{env}

[testenv]
extras = test
recreate = True
commands = pytest test_file.py
{extras}
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


@pytest.fixture(autouse=True)
def _clean_pip_constrains_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIP_CONSTRAINT", raising=False)


@pytest.mark.parametrize(("cmp", "req"), [("==", "1"), ("!=", "0")])
def test_setup_cfg_parse(
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
            "tox.ini": tox_ini_template.format(env=env, extras=""),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template.format(cmp=cmp),
            "setup.py": setup_py_template,
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


@pytest.mark.parametrize(("cmp", "req"), [("==", "1"), ("!=", "0")])
def test_pyproject_toml_parse(
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
            "tox.ini": tox_ini_template.format(env=env, extras=""),
            "pyproject.toml": pyproject_toml_template,
            "test_file.py": test_file_template.format(cmp=cmp),
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


@pytest.mark.parametrize(("cmp", "req"), [("==", "1"), ("!=", "0")])
def test_min_req_config(
    tox_project: ToxProjectCreator,
    data_dir: "Path",
    cmp: str,
    req: str,
) -> None:
    env = f"{sys.version_info[0]}{sys.version_info[1]}"
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env, extras=f"min_req={req}"),
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
            "tox.ini": tox_ini_template.format(env=env, extras=""),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template_,
            "setup.py": setup_py_template,
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


def test_additional_constrains(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
) -> None:
    monkeypatch.setenv("MIN_REQ", "1")
    env = f"{sys.version_info[0]}{sys.version_info[1]}"

    test_file_template_ = test_file_template.format(cmp="==")
    test_file_template_ += 'import coverage\ndef test_click_version():\n    assert coverage.__version__ == "6.5.0"\n'
    test_file_template_ = test_file_template_.replace("1.13.0", "1.14.0")

    req_str = "\n".join(
        f"    {val}"
        for val in ["coverage==6.5.0", "babel==2.6.0", "six==1.14.0", "-r '{project_dir}/constraints_dummy.txt'"]
    )

    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env, extras=f"min_req_constraints=\n{req_str}"),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template_,
            "setup.py": setup_py_template,
            "constraints_dummy.txt": "wheel==0.37.0",
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


def test_additional_constrains_full_path(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    tmp_path: "Path",
) -> None:
    monkeypatch.setenv("MIN_REQ", "1")
    env = f"{sys.version_info[0]}{sys.version_info[1]}"

    test_file_template_ = test_file_template.format(cmp="==")
    test_file_template_ += 'import coverage\ndef test_click_version():\n    assert coverage.__version__ == "6.5.0"\n'
    test_file_template_ = test_file_template_.replace("1.13.0", "1.14.0")

    req_str = "\n".join(
        f"    {val}"
        for val in ["coverage==6.5.0", "babel==2.6.0", "six==1.14.0", f"-r '{tmp_path}/constraints_dummy.txt'"]
    )

    with (tmp_path / "constraints_dummy.txt").open("w") as f:
        f.write("wheel==0.37.0")

    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env, extras=f"min_req_constraints=\n{req_str}"),
            "setup.cfg": setup_cfg_template,
            "test_file.py": test_file_template_,
            "setup.py": setup_py_template,
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")

    result.assert_success()


@pytest.mark.parametrize("full_path", [True, False])
@pytest.mark.parametrize("use_cli", [True, False])
def test_constrains_path(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    data_dir: "Path",
    tmp_path: "Path",
    *,
    full_path: bool,
    use_cli: bool,
) -> None:
    env = f"{sys.version_info[0]}{sys.version_info[1]}"
    monkeypatch.setenv("MIN_REQ", "1")
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env, extras=""),
            "pyproject.toml": pyproject_toml_template,
            "test_file.py": test_file_template.format(cmp="=="),
        },
        base=data_dir / "package_data",
    )

    env_path = tmp_path / "env"
    env_path.mkdir()

    if full_path:
        monkeypatch.setenv("TOX_MIN_REQ_CONSTRAINTS", str(env_path / "constraints.txt"))
    else:
        monkeypatch.setenv("TOX_MIN_REQ_CONSTRAINTS", str(env_path))

    expected_file = env_path / "constraints.txt"
    extra_args = []
    if use_cli:
        cli_path = tmp_path / "cli"
        cli_path.mkdir()
        expected_file = cli_path / "constraints.txt"
        extra_args = ["--min-req-constraints-path", str(cli_path / "constraints.txt") if full_path else str(cli_path)]

    result = project.run("run", *extra_args)

    result.assert_success()

    assert expected_file.exists()


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
    if not shutil.which(f"python{python}") and os.environ.get("REQUIRE_ALL_TEST", "0") == "0":
        pytest.skip(f"Python {python} is not installed")
    monkeypatch.setenv("MIN_REQ", "1")
    constrains_list = "\n".join(
        f"    'six>={six_version}; python_version == \"{python_version}\"',"
        for python_version, _, six_version in PYTHON_VER_LI
    )
    project = tox_project(
        {
            "tox.ini": tox_ini_template.format(env=env, extras=""),
            "pyproject.toml": pyproject_toml_template_base.format(deps=constrains_list),
            "test_file.py": test_file_template_six.format(six_version=target_six_version),
        },
        base=data_dir / "package_data",
    )

    result = project.run("run")
    result.assert_success()

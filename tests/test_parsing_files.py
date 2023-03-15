from typing import TYPE_CHECKING

from tox_min_req._parse_dependencies import parse_pyproject_toml, parse_setup_cfg, parse_single_requirement

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_setup_cfg_parse(data_dir: "Path", monkeypatch: "pytest.MonkeyPatch"):
    monkeypatch.setattr("sys.platform", "linux")
    setup_file = data_dir / "setup.cfg"

    constrains = {
        "pytest": "7.0.0",
        "pytest-cov": "2.5",
        "sphinx": "3.0.0",
        "scipy": "1.2.0",
    }

    assert parse_setup_cfg(setup_file, python_version="3.7", python_full_version="3.7.1") == {
        "numpy": "1.16.0",
        **constrains,
    }
    assert parse_setup_cfg(setup_file, python_version="3.8", python_full_version="3.8.3") == {
        "numpy": "1.18.0",
        **constrains,
    }
    monkeypatch.setattr("sys.platform", "win32")
    assert parse_setup_cfg(setup_file, python_version="3.8", python_full_version="3.8.3") == {
        "numpy": "1.18.0",
        "pandas": "0.25.0",
        **constrains,
    }


def test_pyproject_toml_parse(data_dir: "Path", monkeypatch: "pytest.MonkeyPatch"):
    monkeypatch.setattr("sys.platform", "linux")
    pyproject_file = data_dir / "pyproject.toml"

    constrains = {
        "pytest": "7.0.0",
        "pytest-cov": "2.5",
        "sphinx": "3.0.0",
        "scipy": "1.2.0",
    }

    assert parse_pyproject_toml(pyproject_file, python_version="3.7", python_full_version="3.7.1") == {
        "numpy": "1.16.0",
        **constrains,
    }
    assert parse_pyproject_toml(pyproject_file, python_version="3.8", python_full_version="3.8.3") == {
        "numpy": "1.18.0",
        **constrains,
    }
    monkeypatch.setattr("sys.platform", "win32")
    assert parse_pyproject_toml(pyproject_file, python_version="3.8", python_full_version="3.8.3") == {
        "numpy": "1.18.0",
        "pandas": "0.25.0",
        **constrains,
    }


def test_parse_single_requirement():
    p_ver, py_full_ver = "3.10", "3.10.1"
    assert parse_single_requirement("numpy==1.16.0", p_ver, py_full_ver) == {"numpy": "1.16.0"}
    assert parse_single_requirement("numpy>=1.16.0", p_ver, py_full_ver) == {"numpy": "1.16.0"}
    assert parse_single_requirement("numpy>=1.16.0 ; python_version < '3.8'", p_ver, py_full_ver) == {}
    assert parse_single_requirement("numpy[test]>=1.16.0", p_ver, py_full_ver) == {"numpy": "1.16.0"}

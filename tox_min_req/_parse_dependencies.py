"""Module to parse the dependencies from the setup.cfg and pyproject.toml files."""

import re
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Union

from packaging.requirements import Requirement

if sys.version_info < (3, 11):
    from tomli import loads as toml_loads
else:
    from tomllib import loads as toml_loads

version_constrains = re.compile(r"([a-zA-Z0-9_\-]+)([><=!]+)([0-9\.]+)")

__all__ = ("parse_setup_cfg", "parse_pyproject_toml", "parse_single_requirement")


def parse_single_requirement(line: str, python_version: str, python_full_version: str) -> Dict[str, str]:
    """
    Parse single requirement line. It resolve requirement against current system and provided python version.

    :param line: line with requirement
    :param python_version: major.minor version of python
    :param python_full_version: major.minor.patch version of python
    :return: empty dict if the requirement is not valid or the requirement name and version
    """
    req = Requirement(line)
    if req.marker is not None and not req.marker.evaluate(
        {"python_version": python_version, "python_full_version": python_full_version},
    ):
        return {}
    version_li = [str(x).replace(">=", "").replace("==", "") for x in req.specifier if ">=" in str(x) or "==" in str(x)]
    if version_li:
        return {req.name: version_li[0]}
    return {}


def _parse_setup_cfg_section(section: str, python_version: str, python_full_version: str) -> Dict[str, str]:
    res: Dict[str, str] = {}
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("#") or not line or ">=" not in line:
            continue
        res.update(parse_single_requirement(line, python_version, python_full_version))
    return res


def parse_setup_cfg(path: Union[str, Path], python_version: str, python_full_version: str) -> Dict[str, str]:
    """
    Parse the setup.cfg file and return a dict of the dependencies and their lower version constraints.

    :param path: path to setup.cfg file
    :param python_version: major.minor version of python
    :param python_full_version: major.minor.patch version of python
    :return: dict of the dependencies that fit to environment and their lower version constraints
    """
    config = ConfigParser()
    config.read(path)
    base_constrains = _parse_setup_cfg_section(
        config["options"]["install_requires"],
        python_version,
        python_full_version,
    )
    for extra in config["options.extras_require"]:
        base_constrains.update(
            _parse_setup_cfg_section(config["options.extras_require"][extra], python_version, python_full_version),
        )

    return base_constrains


def parse_pyproject_toml(path: Union[str, Path], python_version: str, python_full_version: str) -> Dict[str, str]:
    """
    Parse the pyproject.toml file and return a dict of the dependencies and their lower version constraints.

    :param path: path to pyproject.toml file
    :param python_version: major.minor version of python
    :param python_full_version: major.minor.patch version of python
    :return: dict of the dependencies that fit to environment and their lower version constraints
    """
    with Path(path).open() as f:
        data = toml_loads(f.read())
    base_constrains: Dict[str, str] = {}
    for line in data["project"]["dependencies"]:
        base_constrains.update(parse_single_requirement(line, python_version, python_full_version))
    for extra in data["project"]["optional-dependencies"]:
        for line in data["project"]["optional-dependencies"][extra]:
            base_constrains.update(parse_single_requirement(line, python_version, python_full_version))
    return base_constrains

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
    from tomlib import load as toml_loads

version_constrains = re.compile(r"([a-zA-Z0-9_\-]+)([><=!]+)([0-9\.]+)")


def _parse_single_requirement(line: str, python_version: str) -> Dict[str, str]:
    req = Requirement(line)
    if req.marker is not None and not req.marker.evaluate({"python_version": python_version}):
        return {}
    if version_li := [str(x).replace(">=", "") for x in req.specifier if ">=" in str(x)]:
        return {req.name: version_li[0]}
    return {}


def _parse_setup_cfg_section(section: str, python_version: str) -> Dict[str, str]:
    res: Dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("#") or not line or ">=" not in line:
            continue
        res |= _parse_single_requirement(line, python_version)
    return res


def parse_setup_cfg(path: Union[str, Path], python_version: str) -> Dict[str, str]:
    """Parse the setup.cfg file and return a dict of the dependencies and their lower version constraints."""
    config = ConfigParser()
    config.read(path)
    base_constrains = _parse_setup_cfg_section(config["options"]["install_requires"], python_version)
    for extra in config["options.extras_require"]:
        base_constrains.update(_parse_setup_cfg_section(config["options.extras_require"][extra], python_version))

    return base_constrains


def parse_pyproject_toml(path: Union[str, Path], python_version: str) -> Dict[str, str]:
    """Parse the pyproject.toml file and return a dict of the dependencies and their lower version constraints."""
    with Path(path).open() as f:
        data = toml_loads(f.read())
    base_constrains: Dict[str, str] = {}
    for line in data["project"]["dependencies"]:
        base_constrains |= _parse_single_requirement(line, python_version)
    for extra in data["project"]["optional-dependencies"]:
        for line in data["project"]["optional-dependencies"][extra]:
            base_constrains |= _parse_single_requirement(line, python_version)
    return base_constrains

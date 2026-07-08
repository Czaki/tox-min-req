"""Module to parse the dependencies from the setup.cfg and pyproject.toml files."""

from __future__ import annotations

import queue
import re
import sys
import warnings
from collections.abc import Sequence
from configparser import ConfigParser
from pathlib import Path

from packaging.requirements import Requirement

if sys.version_info < (3, 11):
    from tomli import loads as toml_loads
else:
    from tomllib import loads as toml_loads

version_constrains = re.compile(r"([a-zA-Z0-9_\-]+)([><=!]+)([0-9\.]+)")

__all__ = (
    "parse_pyproject_toml",
    "parse_setup_cfg",
    "parse_single_requirement",
)


def parse_single_requirement(
    line: str, python_version: str, python_full_version: str
) -> dict[str, str]:
    """
    Parse a single requirement line. It resolves requirement against the current system and the provided python version.

    :param line: line with requirement
    :param python_version: major.minor version of python
    :param python_full_version: major.minor.patch version of python
    :return: empty dict if the requirement is not valid or the requirement name and version
    """
    if isinstance(line, dict):
        return {}
    req = Requirement(line.split("#", maxsplit=1)[0])
    if req.marker is not None and not req.marker.evaluate(
        {
            "python_version": python_version,
            "python_full_version": python_full_version,
        },
    ):
        return {}
    version_li = [
        str(x).replace(">=", "").replace("==", "")
        for x in req.specifier
        if ">=" in str(x) or "==" in str(x)
    ]
    if version_li:
        return {req.name: version_li[0]}
    return {}


def _parse_setup_cfg_section(
    section: str, python_version: str, python_full_version: str
) -> dict[str, str]:
    res: dict[str, str] = {}
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("#") or not line or ">=" not in line:
            continue
        res.update(parse_single_requirement(line, python_version, python_full_version))
    return res


def parse_setup_cfg(
    path: str | Path,
    python_version: str,
    python_full_version: str,
    extras: Sequence[str] = (),
) -> dict[str, str]:
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
        if extra not in extras:
            continue
        base_constrains.update(
            _parse_setup_cfg_section(
                config["options.extras_require"][extra],
                python_version,
                python_full_version,
            ),
        )

    return base_constrains


def get_extras_from_dependency(dependency: str) -> Sequence[str]:
    """
    Get extras from the dependency string.

    :param dependency: dependency string
    :return: list of extras
    """
    return [
        x.strip()
        for x in dependency.split("[", maxsplit=2)[1]
        .split("]", maxsplit=1)[0]
        .split(",")
    ]


def get_all_extras_to_visit(
    optional_dependencies: dict[str, str],
    start_extras: Sequence[str],
    project_name: str,
) -> set[str]:
    """
    Get all extras that should be visited.

    :param optional_dependencies: dict of the optional dependencies
    :param start_extras: list of extras to start with
    :param project_name: name of the project to search for nested extras
    :return: set of extras that should be visited
    """
    visited_extras = set()
    extras_to_visit: queue.Queue[str] = queue.Queue()
    prefix = f"{project_name}["
    for extra in start_extras:
        extras_to_visit.put(extra)
    while not extras_to_visit.empty():
        extra = extras_to_visit.get()
        if extra in visited_extras:
            continue
        if extra not in optional_dependencies:
            warnings.warn(f"Extra {extra} not found in pyproject.toml", UserWarning)
            continue
        visited_extras.add(extra)
        for line in optional_dependencies[extra]:
            if not line.startswith(prefix):
                continue
            extras = get_extras_from_dependency(line)
            for extra in extras:
                extras_to_visit.put(extra)
    return visited_extras


def get_all_dependency_groups_to_visit(
    dependency_groups: dict[str, list[str]],
    start_dependency_groups: Sequence[str],
    project_name: str,
) -> tuple[set[str], set[str]]:
    """
    Get all dependency groups that should be visited.

    :param dependency_groups: dict of the dependency groups
    :param start_dependency_groups: list of dependency groups to start with
    :return: set of dependency groups that should be visited and set of required extras
    """
    visited_dependency_groups = set()
    required_extras: set[str] = set()
    dependency_groups_to_visit: queue.Queue[str] = queue.Queue()
    prefix = f"{project_name}["
    for group in start_dependency_groups:
        dependency_groups_to_visit.put(group)
    while not dependency_groups_to_visit.empty():
        group = dependency_groups_to_visit.get()
        if group in visited_dependency_groups:
            continue
        if group not in dependency_groups:
            warnings.warn(
                f"Dependency group {group} not found in pyproject.toml", UserWarning
            )
            continue
        visited_dependency_groups.add(group)
        for line in dependency_groups[group]:
            if isinstance(line, dict):
                dependency_groups_to_visit.put(line["include-group"])
            elif line.startswith(prefix):
                extras = get_extras_from_dependency(line)
                required_extras.update(extras)

    return visited_dependency_groups, required_extras


def parse_pyproject_toml(
    path: str | Path,
    python_version: str,
    python_full_version: str,
    extras: Sequence[str] = (),
    dependency_groups: Sequence[str] = (),
) -> dict[str, str]:
    """
    Parse the pyproject.toml file and return a dict of the dependencies and their lower version constraints.

    :param path: path to pyproject.toml file
    :param python_version: major.minor version of python
    :param python_full_version: major.minor.patch version of python
    :param extras: list of extras to include
    :param dependency_groups: list of dependency groups to include
    :return: dict of the dependencies that fit to environment and their lower version constraints
    """
    with Path(path).open() as f:
        data = toml_loads(f.read())
    base_constrains: dict[str, str] = {}
    for line in data["project"]["dependencies"]:
        base_constrains.update(
            parse_single_requirement(line, python_version, python_full_version)
        )
    project_name = data["project"]["name"]
    if extras:
        extras_to_visit = get_all_extras_to_visit(
            data["project"]["optional-dependencies"],
            extras,
            project_name,
        )
    else:
        extras_to_visit = set()

    if dependency_groups:
        dependency_groups_to_visit, additional_extras = (
            get_all_dependency_groups_to_visit(
                data["dependency-groups"],
                dependency_groups,
                project_name,
            )
        )
    else:
        dependency_groups_to_visit = set()
        additional_extras = set()

    for extra in extras_to_visit | additional_extras:
        for line in data["project"]["optional-dependencies"][extra]:
            base_constrains.update(
                parse_single_requirement(line, python_version, python_full_version)
            )
    for group in dependency_groups_to_visit:
        for line in data["dependency-groups"][group]:
            base_constrains.update(
                parse_single_requirement(line, python_version, python_full_version)
            )
    return base_constrains

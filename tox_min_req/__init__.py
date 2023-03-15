# SPDX-FileCopyrightText: 2023-present Grzegorz Bokota <bokota+github@gmail.com>
#
# SPDX-License-Identifier: MIT
"""tox plugin for simplify minimal requirements tests by creating minimal constrains file."""
from tox_min_req._parse_dependencies import parse_pyproject_toml, parse_setup_cfg, parse_single_requirement
from tox_min_req._version import __version__

__all__ = ("__version__", "parse_setup_cfg", "parse_pyproject_toml", "parse_single_requirement")

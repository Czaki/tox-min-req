from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tox import __version__ as tox_version
from tox.plugin import impl
from tox.tox_env.errors import Fail
from tox.tox_env.python.runner import PythonRun

from ._parse_dependencies import (
    parse_pyproject_toml,
    parse_setup_cfg,
    parse_single_requirement,
)

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State
    from tox.tox_env.api import EnvConfigSet, ToxEnv


CONSTRAINTS_FILE_NAME = "min_req_constraints.txt"
# the same check as tox uses to parse the ``constraints`` setting
_POSIX = sys.platform != "win32"


def _write_constrains_file(
    tox_env: ToxEnv, dependencies: dict[str, str], extra_lines: list[str]
) -> Path:
    if tox_env.options.min_req_constraints_path:
        base_path = Path(tox_env.options.min_req_constraints_path)
        constrain_file = (
            base_path / CONSTRAINTS_FILE_NAME if base_path.is_dir() else base_path
        )
    elif os.environ.get("TOX_MIN_REQ_CONSTRAINTS", ""):
        base_path = Path(os.environ["TOX_MIN_REQ_CONSTRAINTS"])
        constrain_file = (
            base_path / CONSTRAINTS_FILE_NAME if base_path.is_dir() else base_path
        )
    else:
        constrain_file = tox_env.env_tmp_dir.parent / CONSTRAINTS_FILE_NAME

    with constrain_file.open("w") as f:
        f.write("\n".join(f"{n}=={v}" for n, v in dependencies.items()))
        f.write("\n")
        f.write("\n".join(extra_lines))

    if tox_env.environment_variables.get("PIP_CONSTRAINT", ""):
        tox_env.environment_variables["PIP_CONSTRAINT"] += f" {constrain_file!s}"
    else:
        tox_env.environment_variables["PIP_CONSTRAINT"] = str(constrain_file)

    if tox_env.environment_variables.get("UV_CONSTRAINT", ""):
        tox_env.environment_variables["UV_CONSTRAINT"] += f" {constrain_file!s}"
    else:
        tox_env.environment_variables["UV_CONSTRAINT"] = str(constrain_file)

    return constrain_file


def _add_to_tox_constraints(tox_env: ToxEnv, deps: Any, constrain_file: Path) -> None:
    """
    Pass the constraints file to uv as a command line constraint when needed.

    uv ignores ``UV_CONSTRAINT`` when a ``-c`` option is passed on the command
    line. tox does that for ``-c`` lines in ``deps``, for the generated
    constraints of ``constrain_package_deps`` (when the package dependencies are
    installed) and, since tox-uv 1.36.0, for the tox ``constraints`` setting
    (tox>=4.28). In these cases the file is added to the ``constraints``
    setting, which tox passes to uv as ``-c``. With a nonempty ``constraints``
    setting tox also stops adding the ``constrain_package_deps`` constraints.
    pip reads ``PIP_CONSTRAINT`` together with ``-c``, so it needs nothing more.
    """
    if type(tox_env.installer).__module__.partition(".")[0] != "tox_uv":
        return
    has_setting = "constraints" in tox_env.conf
    args = list(tox_env.conf["constraints"].as_root_args) if has_setting else []
    deps_args = getattr(deps, "as_root_args", [])
    deps_constraints = any(arg.startswith(("-c", "--constraint")) for arg in deps_args)
    package_constraints = (
        "constrain_package_deps" in tox_env.conf
        and tox_env.conf["constrain_package_deps"]
    )
    if not args and not deps_constraints and not package_constraints:
        return
    definition = next(
        (d for d in tox_env.conf.get_configs() if "constraints" in d.keys), None
    )
    if not hasattr(definition, "overwrite"):
        # ``constraints`` was added in tox 4.28.0 and ``overwrite`` in 4.58.0
        msg = (
            "tox-min-req: uv ignores UV_CONSTRAINT when constraints are passed "
            "with -c (from 'deps', 'constrain_package_deps' or the 'constraints' "
            "setting); applying the "
            f"minimum versions then requires tox>=4.58.0, found {tox_version}"
        )
        raise Fail(msg)
    # tox splits each entry with ``shlex.split(..., posix=sys.platform != "win32")``.
    # On POSIX quotes are removed, so quoting keeps paths with spaces in one piece.
    # On Windows quotes are kept as part of the file name, so paths cannot be quoted
    # and paths with spaces cannot be passed.
    if not _POSIX and " " in str(constrain_file):
        msg = (
            f"tox-min-req: tox cannot pass a constraints file with spaces in its "
            f"path on Windows ({constrain_file}); use --min-req-constraints-path "
            "or TOX_MIN_REQ_CONSTRAINTS to write it to a path without spaces"
        )
        raise Fail(msg)
    names = [*args[1::2], str(constrain_file)]
    raw = "\n".join(f'"{name}"' if _POSIX else name for name in names)
    definition.overwrite(  # type: ignore[union-attr]
        type(tox_env.conf["constraints"]).factory(tox_env.core["toxinidir"], raw)
    )


@impl
def tox_on_install(tox_env: ToxEnv, arguments: Any, section: str, of_type: str) -> None:
    # Do not check ``section``: tox passes ``PythonRun`` but runners from
    # plugins (e.g. tox-uv's ``UvVenvRunner``) may pass their own class name.
    # Other run envs (e.g. PEP 723 runners) do not register ``extras``.
    if of_type != "deps" or not isinstance(tox_env, PythonRun):
        return
    if os.environ.get("MIN_REQ", "0") != "1" and not tox_env.conf["min_req"]:
        return

    project_path = tox_env.core["package_root"]
    python_version = ".".join(str(x) for x in tox_env.base_python.version_info[:2])
    python_full_version = ".".join(str(x) for x in tox_env.base_python.version_info[:3])
    extras = tox_env.conf["extras"]
    dependency_groups = tox_env.conf["dependency_groups"]
    if (project_path / "setup.cfg").exists():
        dependencies = parse_setup_cfg(
            project_path / "setup.cfg", python_version, python_full_version, extras
        )
    elif (project_path / "pyproject.toml").exists():
        dependencies = parse_pyproject_toml(
            project_path / "pyproject.toml",
            python_version,
            python_full_version,
            extras,
            dependency_groups,
        )
    else:  # pragma: no cover
        return

    extra_lines = []

    if tox_env.conf["min_req_constraints"]:
        for line in tox_env.conf["min_req_constraints"].split("\n"):
            strip_line = line.strip()
            if strip_line.startswith(("-r", "-c")):
                if "{project_dir}" in strip_line:
                    strip_line = strip_line.replace("{project_dir}", str(project_path))
                extra_lines.append(strip_line)
            else:
                dependencies.update(
                    parse_single_requirement(
                        strip_line, python_version, python_full_version
                    )
                )

    constrain_file = _write_constrains_file(tox_env, dependencies, extra_lines)
    _add_to_tox_constraints(tox_env, arguments, constrain_file)


@impl
def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
    env_conf.add_config(
        keys=["min_req"],
        of_type=bool,
        default=False,
        desc="Set to true to use the minimum required version of the dependencies",
    )
    env_conf.add_config(
        keys=["min_req_constraints"],
        of_type=str,
        default="",
        desc="List of additional constraints to use when min_req is set to true, "
        "could override the minimum required version of the dependencies",
    )


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_argument(
        "--min-req-constraints-path",
        type=str,
        default="",
        help="Path to directory where the constraints.txt file will be created. "
        "If not set, the constraints file will be created in the tox temporary directory. "
        "Because of pip using space as separator, the path should not contain spaces.",
    )

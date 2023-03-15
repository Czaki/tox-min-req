import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from tox.plugin import impl

from ._parse_dependencies import parse_pyproject_toml, parse_setup_cfg, parse_single_requirement

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State
    from tox.tox_env.api import EnvConfigSet, ToxEnv


def _write_constrains_file(tox_env: "ToxEnv", dependencies: Dict[str, str], extra_lines: List[str]) -> Path:
    if tox_env.options.min_req_constraints_path:
        base_path = Path(tox_env.options.min_req_constraints_path)
        constrain_file = base_path / "constraints.txt" if base_path.is_dir() else base_path
    elif os.environ.get("TOX_MIN_REQ_CONSTRAINTS", ""):
        base_path = Path(os.environ["TOX_MIN_REQ_CONSTRAINTS"])
        constrain_file = base_path / "constraints.txt" if base_path.is_dir() else base_path
    else:
        constrain_file = tox_env.env_tmp_dir / "constraints.txt"

    with constrain_file.open("w") as f:
        f.write("\n".join(f"{n}=={v}" for n, v in dependencies.items()))
        f.write("\n")
        f.write("\n".join(extra_lines))

    if "PIP_CONSTRAINT" in tox_env.environment_variables:
        tox_env.environment_variables["PIP_CONSTRAINT"] += f" {str(constrain_file)}"
    else:
        tox_env.environment_variables["PIP_CONSTRAINT"] = str(constrain_file)

    return constrain_file


@impl
def tox_on_install(tox_env: "ToxEnv", arguments: Any, section: str, of_type: str) -> None:  # noqa: ARG001, ANN401
    if of_type != "deps" and section != "PythonRun":
        return
    if os.environ.get("MIN_REQ", "0") != "1" and not tox_env.conf["min_req"]:
        return

    project_path = tox_env.core._root  # noqa: SLF001
    python_version = ".".join(str(x) for x in tox_env.base_python.version_info[:2])
    python_full_version = ".".join(str(x) for x in tox_env.base_python.version_info[:3])
    if (project_path / "setup.cfg").exists():
        dependencies = parse_setup_cfg(project_path / "setup.cfg", python_version, python_full_version)
    elif (project_path / "pyproject.toml").exists():
        dependencies = parse_pyproject_toml(project_path / "pyproject.toml", python_version, python_full_version)
    else:  # pragma: no cover
        return

    extra_lines = []

    if tox_env.conf["min_req_constraints"]:
        for line in tox_env.conf["min_req_constraints"].split("\n"):
            strip_line = line.strip()
            if strip_line.startswith("-r"):
                if "{project_dir}" in strip_line:
                    strip_line = strip_line.replace("{project_dir}", str(project_path))
                extra_lines.append(strip_line)
            else:
                dependencies.update(parse_single_requirement(strip_line, python_version, python_full_version))

    _write_constrains_file(tox_env, dependencies, extra_lines)


@impl
def tox_add_env_config(env_conf: "EnvConfigSet", state: "State") -> None:  # noqa: ARG001
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
def tox_add_option(parser: "ToxParser") -> None:
    parser.add_argument(
        "--min-req-constraints-path",
        type=str,
        default="",
        help="Path to directory where the constraints.txt file will be created. "
        "If not set, the constraints file will be created in the tox temporary directory. "
        "Because of pip using space as separator, the path should not contain spaces.",
    )

import os
from typing import TYPE_CHECKING, Any

from tox.plugin import impl

from ._parse_dependencies import parse_pyproject_toml, parse_setup_cfg

if TYPE_CHECKING:
    from tox.session.state import State
    from tox.tox_env.api import EnvConfigSet, ToxEnv


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
    else:
        return

    constrain_file = tox_env.env_tmp_dir / "constraints.txt"

    with constrain_file.open("w") as f:
        f.write("\n".join(f"{n}=={v}" for n, v in dependencies.items()))

    if "PIP_CONSTRAINT" in tox_env.environment_variables:
        tox_env.environment_variables["PIP_CONSTRAINT"] += f" {str(constrain_file)}"
    else:
        tox_env.environment_variables["PIP_CONSTRAINT"] = str(constrain_file)


@impl
def tox_add_env_config(env_conf: "EnvConfigSet", state: "State") -> None:  # noqa: ARG001
    env_conf.add_config(
        keys=["min_req"],
        of_type=bool,
        default=False,
        desc="Set to true to use the minimum required version of the dependencies",
    )

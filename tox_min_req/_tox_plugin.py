import os
from typing import TYPE_CHECKING, Any

from tox.plugin import impl

from ._parse_dependencies import parse_pyproject_toml, parse_setup_cfg

if TYPE_CHECKING:
    from tox.tox_env.api import ToxEnv


@impl
def tox_on_install(tox_env: "ToxEnv", arguments: Any, section: str, of_type: str) -> None:  # noqa: ARG001, ANN401
    if of_type == "deps" and section == "PythonRun":
        if "MIN_REQ" not in os.environ or os.environ["MIN_REQ"] == "0":
            return

        project_path = tox_env.core._root  # noqa: SLF001
        if (project_path / "setup.cfg").exists():
            dependencies = parse_setup_cfg(project_path / "setup.cfg", "3.8.0")
        elif (project_path / "pyproject.toml").exists():
            dependencies = parse_pyproject_toml(project_path / "pyproject.toml", "3.8.0")
        else:
            return

        constrain_file = tox_env.env_tmp_dir / "constraints.txt"

        with constrain_file.open("w") as f:
            f.write("\n".join(f"{n}=={v}" for n, v in dependencies.items()))

        tox_env.environment_variables["PIP_CONSTRAINT"] = str(constrain_file)

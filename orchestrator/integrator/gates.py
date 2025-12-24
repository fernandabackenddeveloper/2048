from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agent_factory.tools.docker_tool import DockerTool
from agent_factory.tools.shell_tool import AllowedCommandRunner


def run_integration_gates(integrator_root: Path, docker_image: str) -> Tuple[bool, Dict[str, Any]]:
    runner = AllowedCommandRunner()
    docker = DockerTool(runner=runner, image=docker_image)

    gates: List[Dict[str, Any]] = [
        {"name": "fetch_modules", "cmd": ["python", "scripts/fetch_modules.py"]},
        {"name": "pytest", "cmd": ["pytest", "-q"]},
    ]

    results: List[Dict[str, Any]] = []
    ok_all = True
    mount = str(integrator_root.resolve())

    for gate in gates:
        code, out, err = docker.run(gate["cmd"], mount_dir=mount)
        passed = code == 0
        ok_all = ok_all and passed
        results.append(
            {
                "gate": gate["name"],
                "passed": passed,
                "stdout": out[-4000:],
                "stderr": err[-4000:],
                "code": code,
            }
        )

    return ok_all, {"gates": results}

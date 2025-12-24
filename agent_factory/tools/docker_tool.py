from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from agent_factory.tools.shell_tool import AllowedCommandRunner


@dataclass
class DockerTool:
    runner: AllowedCommandRunner
    image: str

    def run(
        self,
        cmd: List[str],
        mount_dir: str,
        workdir: str = "/work",
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        cache_mounts = [
            "--mount",
            "type=volume,src=agent_factory_pip_cache,dst=/cache/pip",
            "--mount",
            "type=volume,src=agent_factory_trivy_cache,dst=/cache/trivy",
            "--mount",
            "type=volume,src=agent_factory_gh_cache,dst=/cache/gh",
            "--mount",
            "type=volume,src=agent_factory_xdg_cache,dst=/cache/xdg",
        ]
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{mount_dir}:{workdir}",
            "-w",
            workdir,
        ] + cache_mounts

        if env:
            for k, v in env.items():
                docker_cmd += ["-e", f"{k}={v}"]

        docker_cmd += [self.image] + cmd
        result = self.runner.run(docker_cmd)
        return result.returncode, result.stdout, result.stderr

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from agent_factory.tools.docker_tool import DockerTool
from agent_factory.tools.shell_tool import AllowedCommandRunner


@dataclass
class GitHubPublisherDocker:
    repo_root: Path
    image: str

    def _docker(self) -> DockerTool:
        runner = AllowedCommandRunner()
        runner.extend_allowlist(["docker"])
        return DockerTool(runner=runner, image=self.image)

    def _env(self) -> dict:
        return {
            "GH_TOKEN": os.getenv("GH_TOKEN", ""),
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
        }

    def run(self, cmd: list[str]) -> Tuple[int, str, str]:
        docker = self._docker()
        return docker.run(cmd, mount_dir=str(self.repo_root.resolve()), env=self._env())

    def ensure_repo(self, owner: str, repo: str, visibility: str = "private") -> bool:
        code, _, _ = self.run(["gh", "repo", "view", f"{owner}/{repo}"])
        if code == 0:
            return True
        vis = "--private" if visibility == "private" else "--public"
        code, _, _ = self.run(["gh", "repo", "create", f"{owner}/{repo}", vis, "--confirm"])
        return code == 0

    def push(self, owner: str, repo: str, branch: str = "main") -> None:
        url = f"https://github.com/{owner}/{repo}.git"
        cmds = [
            ["git", "init"],
            ["git", "checkout", "-B", branch],
            ["git", "add", "-A"],
            ["git", "commit", "-m", "Agent Factory publish"],
            ["git", "remote", "remove", "origin"],
            ["git", "remote", "add", "origin", url],
            ["git", "push", "-u", "origin", branch, "--force-with-lease"],
        ]
        for c in cmds:
            self.run(c)

    def release(self, tag: str, title: str, notes_file: Path, asset: Path) -> None:
        self.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--title",
                title,
                "--notes-file",
                str(notes_file),
                str(asset),
            ]
        )

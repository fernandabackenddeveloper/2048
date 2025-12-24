from __future__ import annotations

import subprocess
from pathlib import Path

from agent_factory.tools.shell_tool import AllowedCommandRunner


class GitTool:
    def __init__(self, runner: AllowedCommandRunner | None = None) -> None:
        self.runner = runner or AllowedCommandRunner()
        self.runner.extend_allowlist(["git"])

    def init_repo(self, path: Path) -> subprocess.CompletedProcess[str]:
        path.mkdir(parents=True, exist_ok=True)
        return self.runner.run(["git", "init"], cwd=str(path))

    def commit_all(self, path: Path, message: str) -> subprocess.CompletedProcess[str]:
        self.runner.run(["git", "add", "."], cwd=str(path))
        return self.runner.run(["git", "commit", "-m", message], cwd=str(path))

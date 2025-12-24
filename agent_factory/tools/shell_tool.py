from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence


@dataclass
class AllowedCommandRunner:
    allowlist: List[str] = field(
        default_factory=lambda: [
            "python",
            "pytest",
            "echo",
            "ls",
            "docker",
        ]
    )

    def run(self, command: Sequence[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        if not command:
            raise ValueError("Command cannot be empty")
        if command[0] not in self.allowlist:
            raise PermissionError(f"Command '{command[0]}' not in allowlist: {self.allowlist}")
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)

    def run_string(self, command: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        return self.run(shlex.split(command), cwd=cwd)

    def extend_allowlist(self, extra: Iterable[str]) -> None:
        for cmd in extra:
            if cmd not in self.allowlist:
                self.allowlist.append(cmd)

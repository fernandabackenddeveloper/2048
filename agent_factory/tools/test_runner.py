from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from agent_factory.tools.shell_tool import AllowedCommandRunner


@dataclass
class TestRunner:
    __test__ = False
    runner: AllowedCommandRunner = field(default_factory=AllowedCommandRunner)

    def run_pytest(self, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        return self.runner.run(["pytest"], cwd=cwd)

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass
class DockerTool:
    """Lightweight helper to check docker availability."""

    def is_available(self) -> bool:
        return shutil.which("docker") is not None

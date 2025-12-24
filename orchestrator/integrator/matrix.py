from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def build_matrix(project: str) -> Dict[str, Any]:
    return {
        "project": project,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "targets": [
            {"os": "windows", "arch": "x86_64", "status": "untested", "notes": ["Run via Docker Desktop"]},
            {"os": "linux", "arch": "x86_64", "status": "untested", "notes": ["CI runner recommended"]},
            {"os": "macos", "arch": "arm64", "status": "untested", "notes": ["Requires macOS runner"]},
        ],
    }

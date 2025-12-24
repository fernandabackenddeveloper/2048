from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


MAX_LINES = 800


@dataclass
class ReviewerAgent:
    repo_root: Path

    def run(self, files_changed: Optional[List[str]] = None) -> Dict[str, Any]:
        repo = self.repo_root
        issues: List[str] = []

        for py in repo.rglob("*.py"):
            lines = py.read_text(encoding="utf-8").splitlines()
            if len(lines) > MAX_LINES:
                issues.append(f"{py}: too many lines ({len(lines)})")

            for i, l in enumerate(lines):
                if "TODO" in l:
                    issues.append(f"{py}:{i+1} contains TODO")
                if l.strip().startswith("print("):
                    issues.append(f"{py}:{i+1} uses print()")

        return {
            "status": "fail" if issues else "ok",
            "issues": issues,
        }

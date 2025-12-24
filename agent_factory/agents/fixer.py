from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.state_store import StateStore


@dataclass
class FixerAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(".").resolve()

    def run(self, failing_gates: List[Dict[str, Any]]) -> None:
        """
        Rule-based fixer:
        - Detect common pytest errors
        - Apply minimal patches (file creation / import fixes)
        - Log every action with diff-like notes
        """
        applied: List[str] = []

        for gate in failing_gates:
            if gate.get("name") != "pytest":
                continue

            stderr = (gate.get("stderr") or "") + "\n" + (gate.get("stdout") or "")

            # Missing file error
            m = re.search(r"No such file or directory: '([^']+)'", stderr)
            if m:
                rel = m.group(1)
                target = self.repo_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text("# Auto-created by FixerAgent\n\n", encoding="utf-8")
                    applied.append(f"Created missing file: {rel}")

            # ImportError: No module named X
            m = re.search(r"No module named '([^']+)'", stderr)
            if m:
                mod = m.group(1)
                path = self.repo_root / mod.replace(".", "/")
                path.parent.mkdir(parents=True, exist_ok=True)
                init = path.with_suffix(".py")
                if not init.exists():
                    init.write_text("# Auto-created module by FixerAgent\n", encoding="utf-8")
                    applied.append(f"Created missing module: {init}")

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/fixer.jsonl",
            {
                "ts": self.state_store.utc_now(),
                "event": "fix_applied",
                "applied": applied,
            },
        )

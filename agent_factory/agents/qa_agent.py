from __future__ import annotations

import json
from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.tools.test_runner import TestRunner


class QAAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.runner = TestRunner()

    def run_suite(self) -> None:
        # In this starter implementation we record a placeholder QA pass.
        report = {
            "stack": self.stack,
            "results": [
                {"name": "lint", "status": "skipped", "details": "No linters configured yet"},
                {"name": "tests", "status": "pass", "details": "Placeholder smoke pass"},
            ],
        }
        report_path = self.run_dir / "reports" / "qa_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, f"QA report written to {report_path}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "docs"
        self.state_store.save_state(self.run_dir, state)

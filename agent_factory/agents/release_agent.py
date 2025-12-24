from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_factory.orchestrator.state_store import StateStore


class ReleaseAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore, dry_run: bool) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.dry_run = dry_run

    def prepare_report(self) -> None:
        artifacts: List[str] = [
            "plan.json",
            "state.json",
            "env_snapshot.json",
            "reports/qa_report.json",
            "reports/QUICKSTART.md",
            "adr/ADR-0001-architecture.md",
        ]
        report_md = self._build_markdown(artifacts)
        report_json = self._build_json(artifacts)
        report_path = self.state_store.save_report(self.run_dir, "final_report.md", report_md)
        json_path = self.state_store.save_report(
            self.run_dir,
            "final_report.json",
            json.dumps(report_json, indent=2),
        )
        self.state_store.append_log(
            self.run_dir,
            f"Final report saved to {report_path} and {json_path}",
        )
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "completed"
        self.state_store.save_state(self.run_dir, state)

    def _build_markdown(self, artifacts: List[str]) -> str:
        lines = [
            "# Final Report",
            "",
            f"**Stack:** {self.stack}",
            f"**Mode:** {'dry-run' if self.dry_run else 'execute'}",
            "",
            "## Artifacts",
        ]
        lines.extend([f"- {item}" for item in artifacts])
        return "\n".join(lines) + "\n"

    def _build_json(self, artifacts: List[str]) -> Dict:
        return {
            "stack": self.stack,
            "mode": "dry-run" if self.dry_run else "execute",
            "artifacts": artifacts,
        }

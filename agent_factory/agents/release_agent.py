from __future__ import annotations

from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore


class ReleaseAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store

    def prepare_report(self) -> None:
        report_lines = [
            "# Final Report",
            "",
            f"**Stack:** {self.stack}",
            "",
            "## Artifacts",
            "- plan.json",
            "- state.json",
            "- reports/qa_report.json",
            "- reports/QUICKSTART.md",
            "- adr/ADR-0001.md",
        ]
        report_path = self.state_store.save_report(self.run_dir, "final_report.md", "\n".join(report_lines) + "\n")
        self.state_store.append_log(self.run_dir, f"Final report saved to {report_path}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "completed"
        self.state_store.save_state(self.run_dir, state)

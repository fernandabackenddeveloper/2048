from __future__ import annotations

from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore


class DocsAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store

    def write_quickstart(self) -> None:
        docs_dir = self.run_dir / "reports"
        docs_dir.mkdir(parents=True, exist_ok=True)
        content = "\n".join(
            [
                "# Quickstart",
                "",
                f"**Stack:** {self.stack}",
                "",
                "## Run the orchestrator",
                "```bash",
                "python -m agent_factory.orchestrator.main --prompt \"Build a sample\" --project demo",
                "```",
                "",
                "Artifacts are stored under `agent_factory/runs/<project>` including plan, ADRs, and QA reports.",
            ]
        )
        quickstart = docs_dir / "QUICKSTART.md"
        quickstart.write_text(content + "\n", encoding="utf-8")
        self.state_store.append_log(self.run_dir, f"Quickstart generated at {quickstart}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "release"
        self.state_store.save_state(self.run_dir, state)

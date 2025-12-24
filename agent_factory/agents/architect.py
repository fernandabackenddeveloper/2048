from __future__ import annotations

from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore


class Architect:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store

    def compose_adr(self) -> None:
        title = "Initial Architecture and Stack Choice"
        context = f"Project targets stack '{self.stack}' with automated agents."
        decision = (
            "Adopt Python orchestrator with stack plugins; run in sandboxed shell; "
            "record tasks and decisions in run directory."
        )
        adr_path = self.state_store.add_decision(
            self.run_dir,
            title,
            context,
            decision,
            slug="architecture",
        )
        self.state_store.append_log(self.run_dir, f"ADR created at {adr_path}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "scaffold"
        self.state_store.save_state(self.run_dir, state)

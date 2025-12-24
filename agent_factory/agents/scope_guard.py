from __future__ import annotations

from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore


class ScopeGuard:
    """Sanity-check prompt scope and record acceptance."""

    def __init__(self, run_dir: Path, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.state_store = state_store

    def validate(self) -> None:
        prompt = (self.run_dir / "inputs" / "input_prompt.md").read_text(encoding="utf-8")
        if not prompt.strip():
            raise ValueError("Prompt is empty; cannot proceed.")
        self.state_store.append_log(self.run_dir, "Scope guard passed")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "ingest"
        self.state_store.save_state(self.run_dir, state)

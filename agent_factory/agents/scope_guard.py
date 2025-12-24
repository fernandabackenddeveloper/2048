from __future__ import annotations

from pathlib import Path
from typing import List

from agent_factory.orchestrator.state_store import StateStore

FORBIDDEN_IF_NOT_IN_PROMPT = [
    "payment",
    "billing",
    "stripe",
    "subscription",
    "authentication",
    "oauth",
    "sso",
    "crypto",
    "wallet",
]


class ScopeGuard:
    """Scope guard to detect out-of-prompt features."""

    def __init__(self, run_dir: Path, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.state_store = state_store

    def validate(self) -> None:
        prompt = (self.run_dir / "inputs" / "input_prompt.md").read_text(encoding="utf-8")
        prompt_lower = prompt.lower()
        plan_path = self.run_dir / "plan.json"
        if not plan_path.exists():
            raise ValueError("Plan is missing; cannot run scope guard.")
        plan = plan_path.read_text(encoding="utf-8")
        violations: List[str] = []

        import json

        data = json.loads(plan)
        for milestone in data.get("milestones", []):
            for feature in milestone.get("features", []):
                for task in feature.get("tasks", []):
                    desc = (task.get("description") or "").lower()
                    for kw in FORBIDDEN_IF_NOT_IN_PROMPT:
                        if kw in desc and kw not in prompt_lower:
                            violations.append(f"{task.get('id')} contains '{kw}' not present in prompt")
        if violations:
            self.state_store.append_log(
                self.run_dir, f"Scope guard failed: {violations[0]}", kind="error"
            )
            raise ValueError("Scope drift detected: " + "; ".join(violations[:5]))

        self.state_store.append_log(self.run_dir, "Scope guard passed")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "architecture"
        self.state_store.save_state(self.run_dir, state)

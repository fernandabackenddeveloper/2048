from __future__ import annotations

import json
from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.planning import generate_plan


class ChiefPlanner:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store

    def ingest(self) -> None:
        self.state_store.append_log(self.run_dir, "Prompt ingested")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "plan"
        self.state_store.save_state(self.run_dir, state)

    def plan(self) -> None:
        prompt = (self.run_dir / "inputs" / "input_prompt.md").read_text(encoding="utf-8")
        plan = generate_plan(prompt_text=prompt, project=self.state_store.read_state(self.run_dir)["project"], stack=self.stack)
        (self.run_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, "Plan created")
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/planner.jsonl",
            {
                "ts": self.state_store.utc_now(),
                "event": "plan_generated",
                "milestones": [m["id"] for m in plan["milestones"]],
            },
        )
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "architecture"
        state["tasks"] = plan["milestones"]
        self.state_store.save_state(self.run_dir, state)

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from agent_factory.orchestrator.state_store import StateStore


@dataclass
class Milestone:
    id: str
    summary: str
    definition_of_done: List[str]
    tasks: List[str]


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
        milestones = self._build_milestones(prompt)
        plan = {
            "milestones": [asdict(milestone) for milestone in milestones],
            "stack": self.stack,
        }
        (self.run_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, "Plan created")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "architecture"
        state["tasks"] = plan["milestones"]
        self.state_store.save_state(self.run_dir, state)

    def _build_milestones(self, prompt: str) -> List[Milestone]:
        """Create a lightweight milestone plan from the prompt text."""
        headline = prompt.strip().splitlines()[0] if prompt.strip() else "Project"
        return [
            Milestone(
                id="M1",
                summary=f"Backlog + scaffolding for {headline}",
                definition_of_done=[
                    "Backlog JSON saved",
                    "ADR for initial stack choice saved",
                ],
                tasks=[
                    "Capture prompt",
                    "Select stack plugin",
                    "Record acceptance criteria",
                ],
            ),
            Milestone(
                id="M2",
                summary="Scaffold runnable skeleton",
                definition_of_done=[
                    "Skeleton files created",
                    "Stack rules applied",
                    "Baseline lint/test commands recorded",
                ],
                tasks=[
                    "Generate scaffold summary",
                    "Document allowed commands",
                    "Record docker usage expectations",
                ],
            ),
            Milestone(
                id="M3",
                summary="QA + docs + release summary",
                definition_of_done=[
                    "Smoke QA recorded",
                    "Quickstart documentation written",
                    "Final report generated",
                ],
                tasks=[
                    "Capture QA outcomes",
                    "Document how to extend",
                    "Publish final report",
                ],
            ),
        ]

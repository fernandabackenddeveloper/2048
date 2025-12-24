from __future__ import annotations

import json
import os
from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.planning import generate_plan
from agent_factory.orchestrator.llm.adapter import LLMError, OpenAICompatibleAdapter
from agent_factory.orchestrator.validators import validate_plan_schema


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
        source = "deterministic"
        reason = "default"

        try:
            adapter = OpenAICompatibleAdapter(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )

            system_prompt_path = (
                Path(__file__).resolve().parents[2] / "orchestrator" / "llm" / "prompts" / "planner.system.txt"
            )
            system_prompt = system_prompt_path.read_text(encoding="utf-8")
            llm_plan = adapter.generate_json(system_prompt, prompt)
            llm_plan.setdefault("project", self.state_store.read_state(self.run_dir)["project"])
            llm_plan.setdefault("stack", self.stack)
            llm_plan.setdefault("created_at", self.state_store.utc_now())

            ok, msg = validate_plan_schema(Path(__file__).resolve().parents[2], llm_plan)
            if ok:
                plan = llm_plan
                source = "llm"
                reason = msg
            else:
                plan = generate_plan(
                    prompt_text=prompt,
                    project=self.state_store.read_state(self.run_dir)["project"],
                    stack=self.stack,
                )
                source = "deterministic"
                reason = msg
        except Exception as e:
            plan = generate_plan(
                prompt_text=prompt,
                project=self.state_store.read_state(self.run_dir)["project"],
                stack=self.stack,
            )
            source = "deterministic"
            reason = f"LLM unavailable/invalid: {type(e).__name__}: {e}"

        (self.run_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, "Plan created")
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/planner.jsonl",
            {
                "ts": self.state_store.utc_now(),
                "event": "plan_generated",
                "source": source,
                "reason": reason,
                "milestones": [m.get("id") for m in plan.get("milestones", [])],
            },
        )
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "scope_guard"
        state["tasks"] = plan.get("milestones", [])
        self.state_store.save_state(self.run_dir, state)

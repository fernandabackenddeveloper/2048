from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.sandbox import create_sandbox, merge_sandbox
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.task_graph import iter_plan_tasks
from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter


@dataclass
class ImplementerAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(".").resolve()

    def run(self) -> None:
        plan_path = self.run_dir / "plan.json"
        if not plan_path.exists():
            raise FileNotFoundError(plan_path)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        api_key = os.getenv("OPENAI_API_KEY")
        adapter = None
        if api_key:
            adapter = OpenAICompatibleAdapter(
                api_key=api_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )

        for _, _, task in iter_plan_tasks(plan):
            task_id = task.get("id")
            sandbox = create_sandbox(self.repo_root, self.state_store.read_state(self.run_dir)["project"], task_id)

            if adapter is None:
                task["status"] = "skipped"
                self.state_store.append_jsonl(
                    self.run_dir,
                    "logs/implementer.jsonl",
                    {
                        "ts": self.state_store.utc_now(),
                        "event": "implementer_invoked",
                        "task": task_id,
                        "sandbox": str(sandbox),
                        "status": "skipped",
                        "reason": "No LLM configured",
                    },
                )
                continue

            prompt = {
                "task": task,
                "rules": {
                    "write_minimal_code": True,
                    "no_scope_creep": True,
                    "tests_must_pass": True,
                },
            }

            # Placeholder: in this step we only log intent; future steps will apply patches.
            self.state_store.append_jsonl(
                self.run_dir,
                "logs/implementer.jsonl",
                {
                    "ts": self.state_store.utc_now(),
                    "event": "implementer_invoked",
                    "task": task_id,
                    "sandbox": str(sandbox),
                    "status": "completed",
                },
            )
            task["status"] = "done"

            merge_sandbox(self.repo_root, sandbox)

        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        state = self.state_store.read_state(self.run_dir)
        state["tasks"] = plan.get("milestones", [])
        self.state_store.save_state(self.run_dir, state)

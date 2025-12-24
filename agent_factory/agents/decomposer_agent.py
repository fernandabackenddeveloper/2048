from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from agent_factory.orchestrator.spec_pipeline import (
    _load_schema,
    _validate,
    backlog_to_markdown,
    write_json,
    write_md,
)
from agent_factory.orchestrator.state_store import StateStore


def _hint(desc: str) -> List[str]:
    s = desc.lower()
    hints: List[str] = []
    if "test" in s:
        hints.append("tests/")
    if "doc" in s or "readme" in s:
        hints.append("docs/")
    if "docker" in s:
        hints.append("docker/")
    if "orchestrator" in s:
        hints.append("orchestrator/")
    if "dashboard" in s:
        hints.append("apps/dashboard/")
    return hints


@dataclass
class DecomposerAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict

    def run(self, prd: Dict[str, Any], specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        repo_root = Path(__file__).resolve().parents[2]
        run_root = self.run_dir
        schema = _load_schema(repo_root, "orchestrator/specs/schemas/backlog.schema.json")

        backlog: Dict[str, Any] = {
            "milestones": [
                {
                    "id": "M1",
                    "features": [
                        {
                            "id": "F1",
                            "tasks": [],
                        }
                    ],
                }
            ]
        }

        tid = 1
        tasks: List[Dict[str, Any]] = []
        for sp in specs:
            domain = sp.get("domain")
            module = sp.get("module")
            t1 = {
                "id": f"T{tid:03d}",
                "description": f"Implement {domain}.{module} minimal skeleton per spec",
                "expected_output": f"Module {domain}.{module} exists and imports",
                "dod": ["imports work", "smoke test exists"],
                "owner": "implementer",
                "status": "todo",
                "depends_on": [],
                "touch_hints": [f"{domain}/", f"{module}/"] + _hint(module or ""),
            }
            tid += 1
            t2 = {
                "id": f"T{tid:03d}",
                "description": f"Add tests for {domain}.{module} acceptance_tests",
                "expected_output": "pytest passes for module tests",
                "dod": ["tests written", "pytest passes"],
                "owner": "qa",
                "status": "todo",
                "depends_on": [t1["id"]],
                "touch_hints": ["tests/"] + _hint(module or ""),
            }
            tid += 1
            tasks.extend([t1, t2])

        backlog["milestones"][0]["features"][0]["tasks"] = tasks
        source = "deterministic"

        if os.getenv("OPENAI_API_KEY"):
            adapter = OpenAICompatibleAdapter(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
            system_prompt = (repo_root / "orchestrator/prompts/decomposer.system.txt").read_text(encoding="utf-8")
            user = json.dumps({"prd": prd, "specs": specs}, indent=2)
            try:
                candidate = adapter.generate_json(system_prompt, user)
                ok, msg = _validate(schema, candidate)
                if ok:
                    backlog = candidate
                    source = "llm"
                else:
                    source = f"fallback(schema): {msg}"
            except Exception as e:  # pragma: no cover - safety fallback
                source = f"fallback(error): {type(e).__name__}"

        write_json(run_root / "backlog" / "backlog.json", backlog)
        write_md(run_root / "backlog" / "backlog.md", "Backlog", backlog_to_markdown(backlog))
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/decomposer.jsonl",
            {"event": "backlog_generated", "source": source},
        )
        return backlog

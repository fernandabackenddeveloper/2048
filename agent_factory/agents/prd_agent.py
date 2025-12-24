from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from agent_factory.orchestrator.spec_pipeline import (
    _load_schema,
    _validate,
    prd_to_markdown,
    write_json,
    write_md,
)
from agent_factory.orchestrator.state_store import StateStore


@dataclass
class PRDAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict

    def run(self, prompt_text: str) -> Dict[str, Any]:
        repo_root = Path(__file__).resolve().parents[2]
        schema = _load_schema(repo_root, "orchestrator/specs/schemas/prd.schema.json")
        run_root = self.run_dir

        def fallback() -> Dict[str, Any]:
            return {
                "project": self.state_store.read_state(self.run_dir)["project"],
                "vision": "Deliver a modular system based on user prompt.",
                "personas": [{"name": "Builder", "goals": ["Create complex projects reliably"]}],
                "use_cases": ["Generate repo, code, tests, docs, releases from a prompt"],
                "non_goals": ["No unrequested features"],
                "requirements": [
                    {"id": "R1", "type": "functional", "text": "Generate repo with code/tests/docs"},
                    {"id": "R2", "type": "non_functional", "text": "Gates must pass in Docker sandbox"},
                ],
                "success_metrics": ["All gates pass", "Release artifact produced"],
                "milestones": [
                    {"id": "M1", "name": "MVP", "definition_of_done": ["plan/spec/backlog created", "tests pass", "artifact zip"]}
                ],
            }

        prd = fallback()
        source = "deterministic"

        if os.getenv("OPENAI_API_KEY"):
            adapter = OpenAICompatibleAdapter(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
            system_prompt = (repo_root / "orchestrator/prompts/prd.system.txt").read_text(encoding="utf-8")
            try:
                candidate = adapter.generate_json(system_prompt, prompt_text)
                ok, msg = _validate(schema, candidate)
                if ok:
                    prd = candidate
                    source = "llm"
                else:
                    source = f"fallback(schema): {msg}"
            except Exception as e:  # pragma: no cover - safety fallback
                source = f"fallback(error): {type(e).__name__}"

        write_json(run_root / "prd" / "prd.json", prd)
        write_md(run_root / "prd" / "prd.md", "PRD", prd_to_markdown(prd))

        adr_path = run_root / "adr" / "ADR-PRD-0001-scope.md"
        adr_body = "\n".join(
            [
                f"# PRD Scope for {prd.get('project')}",
                "",
                f"**Vision:** {prd.get('vision')}",
                "",
                "## Non-goals",
                *[f"- {item}" for item in prd.get("non_goals", [])],
            ]
        )
        adr_path.write_text(adr_body + "\n", encoding="utf-8")

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/prd.jsonl",
            {"event": "prd_generated", "source": source},
        )
        return prd

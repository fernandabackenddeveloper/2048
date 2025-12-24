from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from agent_factory.orchestrator.state_store import StateStore


@dataclass
class DirectorAgent:
    run_dir: Path
    repo_root: Path
    store: StateStore

    def run(self, prd: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
        out = {
            "domain": spec.get("domain"),
            "module": spec.get("module"),
            "boundaries": [f"{spec.get('domain')}/", f"{spec.get('module')}/"],
            "test_strategy": ["smoke test import", "unit tests for interfaces"],
            "risks": ["scope creep", "missing acceptance tests"],
            "recommended_capabilities": [spec.get("domain"), spec.get("module")],
        }

        if os.getenv("OPENAI_API_KEY"):
            adapter = OpenAICompatibleAdapter(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
            sys = (self.repo_root / "orchestrator/prompts/director.system.txt").read_text(encoding="utf-8")
            user = json.dumps({"prd": prd, "spec": spec}, indent=2)
            try:
                cand = adapter.generate_json(sys, user)
                if isinstance(cand, dict) and cand.get("domain") and cand.get("module"):
                    out = cand
            except Exception:
                pass

        self.store.append_jsonl(
            self.run_dir,
            "logs/director.jsonl",
            {"event": "director_output", "domain": out.get("domain"), "module": out.get("module")},
        )
        return out

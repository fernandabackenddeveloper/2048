from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from agent_factory.orchestrator.spec_pipeline import _load_schema, _validate, spec_to_markdown, write_json, write_md
from agent_factory.orchestrator.state_store import StateStore

DEFAULT_MODULES: List[Tuple[str, str]] = [
    ("core", "orchestrator"),
    ("core", "tools"),
    ("core", "qa"),
    ("core", "plugin_system"),
    ("ui", "dashboard"),
    ("release", "publisher"),
]


@dataclass
class SpecAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict

    def run(self, prd: Dict[str, Any], modules: List[Tuple[str, str]] | None = None) -> List[Dict[str, Any]]:
        repo_root = Path(__file__).resolve().parents[2]
        run_root = self.run_dir
        schema = _load_schema(repo_root, "orchestrator/specs/schemas/spec.schema.json")
        modules = modules or DEFAULT_MODULES
        out: List[Dict[str, Any]] = []

        adapter = None
        if os.getenv("OPENAI_API_KEY"):
            adapter = OpenAICompatibleAdapter(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
        system_prompt = (repo_root / "orchestrator/prompts/spec.system.txt").read_text(encoding="utf-8")

        for domain, module in modules:
            spec = {
                "domain": domain,
                "module": module,
                "overview": f"{domain}.{module} module.",
                "interfaces": [{"name": "api", "inputs": ["context"], "outputs": ["result"]}],
                "data_models": [],
                "constraints": ["No scope creep", "Must be testable"],
                "acceptance_tests": [f"{domain}.{module} has smoke tests passing"],
            }
            source = "deterministic"

            if adapter:
                user = json.dumps({"prd": prd, "domain": domain, "module": module}, indent=2)
                try:
                    candidate = adapter.generate_json(system_prompt, user)
                    ok, msg = _validate(schema, candidate)
                    if ok:
                        spec = candidate
                        source = "llm"
                    else:
                        source = f"fallback(schema): {msg}"
                except Exception as e:  # pragma: no cover - safety fallback
                    source = f"fallback(error): {type(e).__name__}"

            out.append(spec)
            write_json(run_root / f"specs/{domain}/{module}.json", spec)
            write_md(run_root / f"specs/{domain}/{module}.md", f"Spec {domain}.{module}", spec_to_markdown(spec))

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/specs.jsonl",
            {"event": "specs_generated", "count": len(out)},
        )
        return out

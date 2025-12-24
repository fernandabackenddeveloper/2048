from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.patching import PatchError, apply_patch, rollback, snapshot
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from orchestrator.vault.vault import Vault
from orchestrator.vault.retrieval import retrieve


@dataclass
class FixerAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(".").resolve()

    def run(self, failing_gates: List[Dict[str, Any]]) -> None:
        """
        LLM-powered fixer with deterministic fallback.
        - If no API key, fallback to rule-based fixer.
        - Otherwise request a unified diff, apply in sandbox, rollback on failure.
        """
        if not os.getenv("OPENAI_API_KEY"):
            self._rule_based(failing_gates)
            return

        vault = Vault(self.repo_root / "knowledge")
        gate_texts = []
        for gate in failing_gates:
            gate_texts.append(str(gate.get("stderr") or ""))
            gate_texts.append(str(gate.get("stdout") or ""))
        query = "\n".join(gate_texts)[:4000]
        hits = retrieve(vault, query=query, tags=None, top_k=6)
        context_pack = [{"id": h.id, "title": h.title, "path": h.path, "snippet": h.snippet} for h in hits]

        adapter = OpenAICompatibleAdapter(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

        system_prompt = (
            self.repo_root
            / "orchestrator"
            / "llm"
            / "prompts"
            / "fixer.system.txt"
        ).read_text(encoding="utf-8")

        context = {"gates": failing_gates, "vault_context": context_pack}
        diff = adapter.generate_text(system_prompt=system_prompt, user_prompt=json.dumps(context, indent=2))

        if not diff.strip():
            return

        snap = snapshot(self.repo_root)
        try:
            apply_patch(self.repo_root, diff)
            self.state_store.append_jsonl(
                self.run_dir,
                "logs/fixer.jsonl",
                {
                    "ts": self.state_store.utc_now(),
                    "event": "llm_patch_applied",
                },
            )
        except PatchError as e:
            rollback(snap, self.repo_root)
            self.state_store.append_jsonl(
                self.run_dir,
                "logs/fixer.jsonl",
                {
                    "ts": self.state_store.utc_now(),
                    "event": "llm_patch_failed",
                    "error": str(e),
                },
            )

    def _rule_based(self, failing_gates: List[Dict[str, Any]]) -> None:
        applied: List[str] = []

        for gate in failing_gates:
            if gate.get("name") != "pytest":
                continue

            stderr = (gate.get("stderr") or "") + "\n" + (gate.get("stdout") or "")

            # Missing file error
            m = re.search(r"No such file or directory: '([^']+)'", stderr)
            if m:
                rel = m.group(1)
                target = self.repo_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text("# Auto-created by FixerAgent\n\n", encoding="utf-8")
                    applied.append(f"Created missing file: {rel}")

            # ImportError: No module named X
            m = re.search(r"No module named '([^']+)'", stderr)
            if m:
                mod = m.group(1)
                path = self.repo_root / mod.replace(".", "/")
                path.parent.mkdir(parents=True, exist_ok=True)
                init = path.with_suffix(".py")
                if not init.exists():
                    init.write_text("# Auto-created module by FixerAgent\n", encoding="utf-8")
                    applied.append(f"Created missing module: {init}")

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/fixer.jsonl",
            {
                "ts": self.state_store.utc_now(),
                "event": "fix_applied",
                "applied": applied,
            },
        )

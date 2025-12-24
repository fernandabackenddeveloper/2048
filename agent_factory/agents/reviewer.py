from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.vault.vault import Vault
from orchestrator.vault.retrieval import retrieve


MAX_LINES = 800


@dataclass
class ReviewerAgent:
    repo_root: Path

    def run(self, files_changed: Optional[List[str]] = None) -> Dict[str, Any]:
        repo = self.repo_root
        issues: List[str] = []

        vault = Vault(repo / "knowledge")
        query = "code review guidelines" if not files_changed else "review " + ", ".join(files_changed)
        hits = retrieve(vault, query=query, tags=None, top_k=4)
        context_pack = [{"id": h.id, "title": h.title, "path": h.path, "snippet": h.snippet} for h in hits]

        for py in repo.rglob("*.py"):
            lines = py.read_text(encoding="utf-8").splitlines()
            if len(lines) > MAX_LINES:
                issues.append(f"{py}: too many lines ({len(lines)})")

            for i, l in enumerate(lines):
                if "TODO" in l:
                    issues.append(f"{py}:{i+1} contains TODO")
                if l.strip().startswith("print("):
                    issues.append(f"{py}:{i+1} uses print()")

        return {
            "status": "fail" if issues else "ok",
            "issues": issues,
            "vault_context": context_pack,
        }

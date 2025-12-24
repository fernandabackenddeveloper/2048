from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.vault.vault import Vault
from orchestrator.vault.ingest import add_local_file


@dataclass
class KnowledgeHarvester:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(__file__).resolve().parents[2]

    def run(self) -> None:
        vault = Vault(self.repo_root / "knowledge")
        vault.ensure()

        targets: List[Path] = []
        for rel in ["docs", "orchestrator", "stacks", "runs"]:
            p = self.repo_root / rel
            if p.exists():
                targets.append(p)

        ingested = 0
        for base in targets:
            base_name = base.name
            for f in base.rglob("*"):
                if f.is_file() and f.suffix.lower() in [".md", ".txt", ".json", ".yaml", ".yml"]:
                    add_local_file(
                        vault=vault,
                        file_path=f,
                        title=f"repo:{f.relative_to(self.repo_root)}",
                        tags=["repo_file", base_name or "repo"],
                    )
                    ingested += 1

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/vault.jsonl",
            {"ts": self.state_store.utc_now(), "event": "harvest_complete", "files_ingested": ingested},
        )

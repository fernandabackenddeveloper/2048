from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.vault.vault import Vault


@dataclass
class KnowledgeCurator:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(__file__).resolve().parents[2]

    def run(self) -> None:
        vault = Vault(self.repo_root / "knowledge")
        vault.ensure()
        manifest = vault.load_manifest()
        out_dir = vault.root / "summaries"
        out_dir.mkdir(parents=True, exist_ok=True)

        for doc in manifest[:200]:
            p = vault.root / doc["path"]
            if p.suffix.lower() not in [".md", ".txt", ".json", ".yaml", ".yml"]:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()[:80]
            (out_dir / f"{doc['id']}.summary.md").write_text(
                f"# Summary: {doc['title']}\n\n" + "\n".join(lines),
                encoding="utf-8",
            )

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/vault.jsonl",
            {"ts": self.state_store.utc_now(), "event": "curation_complete", "summaries": min(len(manifest), 200)},
        )

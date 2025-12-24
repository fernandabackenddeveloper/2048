from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Vault:
    root: Path

    @property
    def sources(self) -> Path:
        return self.root / "sources"

    @property
    def ingest(self) -> Path:
        return self.root / "ingest"

    @property
    def index_dir(self) -> Path:
        return self.root / "index"

    @property
    def manifest_path(self) -> Path:
        return self.index_dir / "manifest.json"

    @property
    def inverted_path(self) -> Path:
        return self.index_dir / "inverted.json"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache" / "retrieval"

    def ensure(self) -> None:
        for p in [
            self.sources,
            self.ingest,
            self.index_dir,
            self.cache_dir,
            self.root / "summaries",
            self.root / "citations",
        ]:
            p.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self.manifest_path.write_text("[]", encoding="utf-8")
        if not self.inverted_path.exists():
            self.inverted_path.write_text("{}", encoding="utf-8")

    def load_manifest(self) -> List[Dict[str, Any]]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save_manifest(self, rows: List[Dict[str, Any]]) -> None:
        self.manifest_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_inverted(self) -> Dict[str, List[str]]:
        return json.loads(self.inverted_path.read_text(encoding="utf-8"))

    def save_inverted(self, inv: Dict[str, List[str]]) -> None:
        self.inverted_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")

from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from orchestrator.vault.vault import Vault


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] if s else "doc"


def add_local_file(vault: Vault, file_path: Path, title: str, tags: List[str]) -> Dict[str, Any]:
    vault.ensure()
    file_path = file_path.resolve()
    digest = sha256_file(file_path)

    doc_id = digest[:12]
    dest = vault.sources / f"{doc_id}-{slug(title)}{file_path.suffix.lower()}"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)

    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    doc = {
        "id": doc_id,
        "title": title,
        "source_type": "local_file",
        "path": str(dest.relative_to(vault.root)),
        "sha256": digest,
        "tags": sorted(list(set([t.lower() for t in tags]))),
        "created_at": now,
        "updated_at": now,
        "meta": {"original_path": str(file_path)},
    }

    manifest = vault.load_manifest()
    for m in manifest:
        if m.get("sha256") == digest:
            return m
    manifest.append(doc)
    vault.save_manifest(manifest)
    return doc


def add_note(vault: Vault, title: str, content: str, tags: List[str]) -> Dict[str, Any]:
    vault.ensure()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    doc_id = digest[:12]
    dest = vault.sources / f"{doc_id}-{slug(title)}.md"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    doc = {
        "id": doc_id,
        "title": title,
        "source_type": "note",
        "path": str(dest.relative_to(vault.root)),
        "sha256": digest,
        "tags": sorted(list(set([t.lower() for t in tags]))),
        "created_at": now,
        "updated_at": now,
        "meta": {},
    }
    manifest = vault.load_manifest()
    for m in manifest:
        if m.get("sha256") == digest:
            return m
    manifest.append(doc)
    vault.save_manifest(manifest)
    return doc

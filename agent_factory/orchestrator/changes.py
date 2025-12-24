from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Set


def _hash_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def snapshot_hashes(root: Path, ignore_dirs: Set[str] | None = None) -> Dict[str, str]:
    ignore_dirs = ignore_dirs or {".git", ".venv", "__pycache__", "runs"}
    out: Dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        parts = set(p.parts)
        if any(d in parts for d in ignore_dirs):
            continue
        rel = str(p.relative_to(root))
        out[rel] = _hash_file(p)
    return out


def diff_hashes(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, List[str]]:
    b = set(before.keys())
    a = set(after.keys())
    created = sorted(list(a - b))
    deleted = sorted(list(b - a))
    modified = sorted([k for k in (a & b) if before[k] != after[k]])
    return {"created": created, "deleted": deleted, "modified": modified}


def changed_files(changes: Dict[str, List[str]]) -> Set[str]:
    return set(changes.get("created", [])) | set(changes.get("deleted", [])) | set(changes.get("modified", []))

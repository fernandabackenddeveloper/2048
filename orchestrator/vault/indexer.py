from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set
import re

from orchestrator.vault.vault import Vault

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def read_doc_text(vault: Vault, doc: Dict[str, str]) -> str:
    p = vault.root / doc["path"]
    if not p.exists():
        return ""
    if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".zip", ".exe", ".dll"]:
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def rebuild_index(vault: Vault) -> None:
    vault.ensure()
    inv: Dict[str, Set[str]] = {}
    manifest = vault.load_manifest()

    for doc in manifest:
        text = read_doc_text(vault, doc)
        toks = set(tokenize(text))
        for tk in toks:
            inv.setdefault(tk, set()).add(doc["id"])

    vault.save_inverted({k: sorted(list(v)) for k, v in inv.items()})

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.vault.indexer import read_doc_text, tokenize
from orchestrator.vault.vault import Vault


@dataclass
class RetrievedDoc:
    id: str
    title: str
    score: float
    snippet: str
    path: str
    tags: List[str]


def _cache_key(q: Dict[str, Any]) -> str:
    s = json.dumps(q, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _snippet(text: str, query_tokens: List[str], max_len: int = 600) -> str:
    lowered = text.lower()
    pos = None
    for tk in query_tokens:
        i = lowered.find(tk)
        if i != -1:
            pos = i
            break
    if pos is None:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    start = max(0, pos - 200)
    end = min(len(text), pos + 400)
    out = text[start:end]
    return out + ("..." if end < len(text) else "")


def retrieve(
    vault: Vault,
    query: str,
    tags: Optional[List[str]] = None,
    top_k: int = 8,
    min_score: float = 0.1,
) -> List[RetrievedDoc]:
    vault.ensure()
    q = {"query": query, "tags": sorted([t.lower() for t in (tags or [])]), "top_k": top_k, "min_score": min_score}
    key = _cache_key(q)
    cache_file = vault.cache_dir / f"{key}.json"
    if cache_file.exists():
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        return [RetrievedDoc(**r) for r in raw]

    inv = vault.load_inverted()
    manifest = vault.load_manifest()
    by_id = {m["id"]: m for m in manifest}

    q_tokens = tokenize(query)
    scores: Dict[str, float] = {}

    for tk in q_tokens:
        for doc_id in inv.get(tk, []):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0

    if q["tags"]:
        want = set(q["tags"])
        scores = {did: sc for did, sc in scores.items() if want.issubset(set(by_id[did].get("tags", [])))}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    out: List[RetrievedDoc] = []
    for did, sc in ranked:
        doc = by_id[did]
        text = read_doc_text(vault, doc)
        snip = _snippet(text, q_tokens)
        if sc >= min_score:
            out.append(
                RetrievedDoc(
                    id=did,
                    title=doc["title"],
                    score=float(sc),
                    snippet=snip,
                    path=doc["path"],
                    tags=doc.get("tags", []),
                )
            )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps([r.__dict__ for r in out], indent=2, ensure_ascii=False), encoding="utf-8")
    return out

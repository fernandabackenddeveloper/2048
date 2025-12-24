from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict


def read_lock(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def write_lock(p: Path, lock: Dict[str, Any]) -> None:
    lock["generated_at"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    p.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")


def update_module(lock: Dict[str, Any], name_or_repo: str, version: str, ref: str) -> Dict[str, Any]:
    for m in lock.get("modules", []):
        if m.get("name") == name_or_repo or m.get("repo") == name_or_repo:
            m["version"] = version
            m["ref"] = ref
            return lock
    lock.setdefault("modules", []).append({"name": name_or_repo, "repo": name_or_repo, "version": version, "ref": ref})
    return lock

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def compose_manifest(modules: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    return {"modules": [{"repo": m["repo"], "path": m.get("path", "")} for m in modules]}


def write_compose_manifest(path: Path, manifest: Dict[str, List[Dict[str, str]]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

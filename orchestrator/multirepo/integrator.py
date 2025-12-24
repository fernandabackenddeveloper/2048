from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def build_module_lock(multirepo: Dict[str, Any], default_tag: str = "v0.1.0") -> Dict[str, Any]:
    return {
        "owner": multirepo.get("owner", ""),
        "modules": [{"repo": m["repo"], "tag": default_tag} for m in multirepo.get("modules", [])],
    }


def write_module_lock(path: Path, lock: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

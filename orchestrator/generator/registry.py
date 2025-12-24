from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

REG_PATH = Path("orchestrator/generator/generated_registry.json")


def load_registry(repo_root: Path) -> Dict[str, Any]:
    p = repo_root / REG_PATH
    if not p.exists():
        return {"agents": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def save_registry(repo_root: Path, reg: Dict[str, Any]) -> None:
    p = repo_root / REG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")

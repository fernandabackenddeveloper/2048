from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def build_fsm(spec: Dict[str, any]) -> Dict[str, any]:
    domain = spec.get("domain", "core")
    module = spec.get("module", "module")
    return {
        "name": f"{domain}.{module}.fsm",
        "initial_state": "Idle",
        "states": ["Idle", "Selecting", "Transforming", "Editing"],
        "transitions": [
            {"from": "Idle", "event": "click", "to": "Selecting"},
            {"from": "Selecting", "event": "drag", "to": "Transforming"},
            {"from": "Transforming", "event": "release", "to": "Idle"},
        ],
    }


def write_fsm(run_dir: Path, fsm: Dict[str, any]) -> Path:
    out = run_dir / "models" / "fsm.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fsm, indent=2), encoding="utf-8")
    return out

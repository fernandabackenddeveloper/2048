from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from orchestrator.ultracomplex.undo_redo.model import default_undo_model


def build_undo_model(spec: Dict[str, any]) -> List[Dict[str, str]]:
    return default_undo_model()


def write_undo_model(run_dir: Path, model: List[Dict[str, str]]) -> Path:
    out = run_dir / "models" / "undo_model.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(json.dumps(model, indent=2), encoding="utf-8")
    return out

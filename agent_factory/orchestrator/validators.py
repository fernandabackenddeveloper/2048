from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from jsonschema import Draft202012Validator


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan_schema(repo_root: Path, plan: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates plan against orchestrator/schemas/plan.schema.json (Draft 2020-12).
    Returns (ok, message).
    """
    schemas_dir = repo_root / "orchestrator" / "schemas"
    plan_schema = load_json(schemas_dir / "plan.schema.json")
    task_schema = load_json(schemas_dir / "task.schema.json")

    plan_schema = dict(plan_schema)
    plan_schema.setdefault("$defs", {})
    plan_schema["$defs"]["task"] = task_schema

    def _rewrite_refs(obj: Any) -> None:
        if isinstance(obj, dict):
            if obj.get("$ref") == "task.schema.json":
                obj["$ref"] = "#/$defs/task"
            for v in obj.values():
                _rewrite_refs(v)
        elif isinstance(obj, list):
            for v in obj:
                _rewrite_refs(v)

    _rewrite_refs(plan_schema)

    v = Draft202012Validator(plan_schema)
    errors = sorted(v.iter_errors(plan), key=lambda e: list(e.path))

    if not errors:
        return True, "Plan schema OK"

    lines = []
    for e in errors[:3]:
        path = ".".join([str(p) for p in e.path]) or "<root>"
        lines.append(f"{path}: {e.message}")
    return False, "Schema validation failed: " + " | ".join(lines)

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - fallback if jsonschema unavailable
    class Draft202012Validator:  # type: ignore
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def iter_errors(self, *_: Any, **__: Any):  # pragma: no cover
            return []


def _load_schema(repo_root: Path, rel: str) -> Dict[str, Any]:
    return json.loads((repo_root / rel).read_text(encoding="utf-8"))


def _validate(schema: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, str]:
    v = Draft202012Validator(schema)
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if not errs:
        return True, "ok"
    e = errs[0]
    path = ".".join([str(p) for p in e.path]) or "<root>"
    return False, f"{path}: {e.message}"


def write_md(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def prd_to_markdown(prd: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"## Vision\n{prd['vision']}\n")
    lines.append("## Personas")
    for p in prd["personas"]:
        lines.append(f"- **{p['name']}**: " + "; ".join(p["goals"]))
    lines.append("\n## Use cases")
    for u in prd["use_cases"]:
        lines.append(f"- {u}")
    lines.append("\n## Non-goals")
    for n in prd["non_goals"]:
        lines.append(f"- {n}")
    lines.append("\n## Requirements")
    for r in prd["requirements"]:
        lines.append(f"- `{r['id']}` ({r['type']}): {r['text']}")
    lines.append("\n## Success metrics")
    for m in prd["success_metrics"]:
        lines.append(f"- {m}")
    lines.append("\n## Milestones")
    for ms in prd["milestones"]:
        lines.append(f"- **{ms['id']} {ms['name']}**: " + "; ".join(ms["definition_of_done"]))
    return "\n".join(lines)


def spec_to_markdown(spec: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"## Overview\n{spec['overview']}\n")
    lines.append("## Interfaces")
    for it in spec["interfaces"]:
        lines.append(f"- **{it['name']}**\n  - inputs: {', '.join(it['inputs'])}\n  - outputs: {', '.join(it['outputs'])}")
    lines.append("\n## Data models")
    for m in spec["data_models"]:
        lines.append(f"- {m}")
    lines.append("\n## Constraints")
    for c in spec["constraints"]:
        lines.append(f"- {c}")
    lines.append("\n## Acceptance tests")
    for t in spec["acceptance_tests"]:
        lines.append(f"- {t}")
    return "\n".join(lines)


def backlog_to_markdown(backlog: Dict[str, Any]) -> str:
    lines = []
    for ms in backlog["milestones"]:
        lines.append(f"## {ms['id']}")
        for feat in ms["features"]:
            lines.append(f"### {feat['id']}")
            for t in feat["tasks"]:
                lines.append(f"- `{t['id']}` ({t['owner']}) deps={t['depends_on']} hints={t['touch_hints']}\n  - {t['description']}")
    return "\n".join(lines)


def backlog_to_plan(project: str, stack: str, backlog: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "project": project,
        "stack": stack,
        "created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "definition_of_done": ["All gates pass", "Docs + report produced"],
        "milestones": backlog["milestones"],
        "capabilities": {"from": "prd+spec"},
        "input_prompt_excerpt": "",
    }

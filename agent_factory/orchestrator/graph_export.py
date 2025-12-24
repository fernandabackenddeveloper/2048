from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def export_plan_dot(plan: Dict[str, Any], out_path: Path) -> None:
    """
    Exports a DOT graph:
    - Milestones as clusters
    - Tasks as nodes
    - depends_on as edges
    """
    lines: List[str] = []
    lines.append("digraph Plan {")
    lines.append('  rankdir="LR";')
    lines.append('  node [shape=box];')

    for ms in plan.get("milestones", []):
        ms_id = ms.get("id", "M?")
        lines.append(f"  subgraph cluster_{ms_id} {{")
        lines.append(f'    label="{ms_id}: {ms.get("title","")}";')

        for feat in ms.get("features", []):
            for task in feat.get("tasks", []):
                tid = task["id"]
                label = tid + "\\n" + (task.get("owner") or "")
                lines.append(f'    "{tid}" [label="{label}"];')
        lines.append("  }")

    all_tasks: Dict[str, Dict[str, Any]] = {}
    for ms in plan.get("milestones", []):
        for feat in ms.get("features", []):
            for task in feat.get("tasks", []):
                all_tasks[task["id"]] = task

    for tid, task in all_tasks.items():
        for dep in task.get("depends_on", []) or []:
            if dep in all_tasks:
                lines.append(f'  "{dep}" -> "{tid}";')

    lines.append("}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

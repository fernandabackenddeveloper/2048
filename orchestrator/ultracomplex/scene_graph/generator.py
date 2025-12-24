from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def build_scene_graph(spec: Dict[str, any]) -> Dict[str, any]:
    return {
        "node_types": ["Scene", "Object", "Mesh", "Material"],
        "edges": [
            {"from": "Scene", "to": "Object", "type": "contains"},
            {"from": "Object", "to": "Mesh", "type": "owns"},
            {"from": "Object", "to": "Material", "type": "references"},
        ],
        "invariants": [
            "Each Mesh has exactly one owning Object",
            "Cycles are forbidden",
            "Material may be shared between Objects",
        ],
    }


def write_scene_graph(run_dir: Path, graph: Dict[str, any]) -> Path:
    out = run_dir / "models" / "scene_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return out

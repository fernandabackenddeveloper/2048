from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.ultracomplex.scene_graph.generator import build_scene_graph, write_scene_graph


@dataclass
class SceneGraphAgent:
    run_dir: Path
    stack: str
    state_store: StateStore

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        graph = build_scene_graph(spec)
        path = write_scene_graph(self.run_dir, graph)
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/ultracomplex.jsonl",
            {"ts": self.state_store.utc_now(), "event": "scene_graph_generated", "path": str(path)},
        )
        return graph

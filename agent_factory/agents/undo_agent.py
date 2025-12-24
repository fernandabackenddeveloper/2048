from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.ultracomplex.undo_redo.generator import build_undo_model, write_undo_model


@dataclass
class UndoAgent:
    run_dir: Path
    stack: str
    state_store: StateStore

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        model = build_undo_model(spec)
        path = write_undo_model(self.run_dir, model)
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/ultracomplex.jsonl",
            {"ts": self.state_store.utc_now(), "event": "undo_model_generated", "path": str(path)},
        )
        return model

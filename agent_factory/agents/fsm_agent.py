from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.ultracomplex.fsm.generator import build_fsm, write_fsm


@dataclass
class FSMAgent:
    run_dir: Path
    stack: str
    state_store: StateStore

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        fsm = build_fsm(spec)
        path = write_fsm(self.run_dir, fsm)
        self.state_store.append_jsonl(
            self.run_dir, "logs/ultracomplex.jsonl", {"ts": self.state_store.utc_now(), "event": "fsm_generated", "path": str(path)}
        )
        return fsm

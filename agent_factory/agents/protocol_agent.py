from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.ultracomplex.protocols.generator import build_protocol, write_protocol


@dataclass
class ProtocolAgent:
    run_dir: Path
    stack: str
    state_store: StateStore

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        protocol = build_protocol(spec)
        path = write_protocol(self.run_dir, protocol)
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/ultracomplex.jsonl",
            {"ts": self.state_store.utc_now(), "event": "protocol_generated", "path": str(path)},
        )
        return protocol

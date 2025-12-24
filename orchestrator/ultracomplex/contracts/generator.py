from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def generate_contract_tests(fsm: Dict[str, Any], scene_graph: Dict[str, Any], protocol: Dict[str, Any]) -> str:
    lines: List[str] = [
        "def test_fsm_transitions_are_defined():",
        "    transitions = " + repr(fsm.get("transitions", [])),
        "    for t in transitions:",
        "        assert t.get('from') and t.get('event') and t.get('to')",
        "",
        "def test_scene_graph_invariants_present():",
        "    invariants = " + repr(scene_graph.get("invariants", [])),
        "    assert invariants",
        "",
        "def test_protocol_endpoints_present():",
        "    endpoints = " + repr(protocol.get("endpoints", [])),
        "    assert endpoints",
    ]
    return "\n".join(lines) + "\n"


def write_contract_tests(run_dir: Path, content: str) -> Path:
    out = run_dir / "models" / "contract_tests.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out

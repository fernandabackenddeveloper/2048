from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def build_protocol(spec: Dict[str, any]) -> Dict[str, any]:
    domain = spec.get("domain", "core")
    module = spec.get("module", "module")
    return {
        "name": f"{domain}.{module}.plugin_api",
        "version": "1.0.0",
        "endpoints": [
            {"name": "register", "input": "PluginInfo", "output": "Status"},
            {"name": "on_load", "input": "Context", "output": "void"},
            {"name": "on_unload", "input": "Context", "output": "void"},
        ],
        "compatibility": "backward-compatible within major",
    }


def write_protocol(run_dir: Path, protocol: Dict[str, any]) -> Path:
    out = run_dir / "models" / "protocols.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    return out

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class Capability:
    name: str
    tags: List[str]
    docker_image: str
    concurrency: int
    budget: Dict[str, Any]


def load_capabilities(repo_root: Path) -> Dict[str, Capability]:
    data = yaml.safe_load((repo_root / "orchestrator/marketplace/capabilities.yaml").read_text(encoding="utf-8"))
    out = {}
    for name, cfg in data.get("capabilities", {}).items():
        out[name] = Capability(
            name=name,
            tags=[t.lower() for t in cfg.get("tags", [])],
            docker_image=cfg.get("docker_image", ""),
            concurrency=int(cfg.get("concurrency", 1)),
            budget=cfg.get("budget", {}),
        )
    return out


def _score(cap: Capability, text: str) -> int:
    s = text.lower()
    return sum(1 for t in cap.tags if t in s)


def pick_capability(caps: Dict[str, Capability], task: Dict[str, Any], spec_hint: str = "") -> Capability:
    blob = " ".join(
        [
            task.get("description", ""),
            task.get("expected_output", ""),
            " ".join(task.get("touch_hints") or []),
            spec_hint,
        ]
    )
    ranked = sorted([(_score(c, blob), c) for c in caps.values()], key=lambda x: x[0], reverse=True)
    if ranked and ranked[0][0] > 0:
        return ranked[0][1]
    return caps.get("core_orchestrator") or list(caps.values())[0]

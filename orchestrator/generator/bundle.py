from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def merge_generated_capabilities(repo_root: Path, reg: Dict[str, Any]) -> Path:
    cap_path = repo_root / "orchestrator" / "marketplace" / "capabilities.yaml"
    data: Dict[str, Any] = {"capabilities": {}}
    if cap_path.exists():
        data = yaml.safe_load(cap_path.read_text(encoding="utf-8")) or {"capabilities": {}}

    for agent_id, meta in reg.get("agents", {}).items():
        data.setdefault("capabilities", {})
        data["capabilities"][agent_id] = {
            "tags": meta.get("tags", []),
            "director": "DirectorAgent",
            "squad": meta.get("class"),
            "docker_image": meta.get("docker_image", ""),
            "concurrency": 1,
            "budget": {"max_tasks_inflight": 6, "max_fix_attempts": 6},
            "boundaries": meta.get("boundaries", []),
        }

    cap_path.parent.mkdir(parents=True, exist_ok=True)
    cap_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return cap_path

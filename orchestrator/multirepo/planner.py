from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def derive_modules(project: str, owner: str, specs: List[Dict[str, Any]], stack: str, docker_image: str) -> Dict[str, Any]:
    grouped: Dict[str, List[str]] = {}
    for sp in specs:
        grouped.setdefault(sp["domain"], []).append(sp["module"])

    modules = []
    for domain, mods in grouped.items():
        repo = f"af-{project}-{domain}".replace("_", "-")
        modules.append(
            {
                "name": domain,
                "repo": repo,
                "domains": [f"{domain}/{m}" for m in mods],
                "stack": stack,
                "docker_image": docker_image,
            }
        )

    return {
        "project": project,
        "owner": owner,
        "integrator_repo": f"af-{project}-integrator".replace("_", "-"),
        "modules": modules,
    }


def write_multirepo_plan(run_root: Path, plan: Dict[str, Any]) -> Path:
    out = run_root / "multirepo" / "multirepo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

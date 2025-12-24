from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.github_publisher_docker import GitHubPublisherDocker
from orchestrator.integrator.versioning import bump, classify_changes


def read_version_pyproject(repo: Path) -> str:
    p = repo / "pyproject.toml"
    if not p.exists():
        return "0.1.0"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'version\\s*=\\s*"(.*?)"', txt)
    return m.group(1) if m else "0.1.0"


def write_version_pyproject(repo: Path, version: str) -> None:
    p = repo / "pyproject.toml"
    txt = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""
    if "version" in txt:
        txt = re.sub(r'version\\s*=\\s*"(.*?)"', f'version = "{version}"', txt)
    else:
        txt += f'\\n[project]\\nversion = "{version}"\\n'
    p.write_text(txt, encoding="utf-8")


@dataclass
class ModuleReleaseAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict[str, Any]

    def run(
        self,
        owner: str,
        repo_name: str,
        module_root: Path,
        changed_files: List[str],
        docker_image: str,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        old_v = read_version_pyproject(module_root)
        level = classify_changes(changed_files)
        new_v = bump(old_v, level)

        meta = {"repo": repo_name, "version": new_v, "ref": f"refs/tags/v{new_v}"}

        if dry_run:
            return meta

        write_version_pyproject(module_root, new_v)
        pub_cfg = (self.config.get("publisher", {}) or {}).get("github", {}) or {}

        publisher = GitHubPublisherDocker(
            repo_root=module_root,
            image=docker_image,
        )
        publisher.ensure_repo(owner, repo_name, visibility=pub_cfg.get("repo_visibility", "private"))
        publisher.push(owner, repo_name, branch=pub_cfg.get("default_branch", "main"))
        publisher.release(
            tag=f"v{new_v}",
            title=f"{repo_name} v{new_v}",
            notes_file=(module_root / "README.md"),
            asset=(module_root / "README.md"),
        )

        out = module_root / "release.meta.json"
        out.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

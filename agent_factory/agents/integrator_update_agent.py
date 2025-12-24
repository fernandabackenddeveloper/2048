from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.github_publisher_docker import GitHubPublisherDocker
from orchestrator.integrator.lock import read_lock, update_module, write_lock


@dataclass
class IntegratorUpdateAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict[str, Any]

    def run(
        self,
        owner: str,
        integrator_repo: str,
        integrator_root: Path,
        updates: List[Dict[str, Any]],
        docker_image: str,
        *,
        dry_run: bool = False,
    ) -> None:
        lock_path = integrator_root / "module.lock.json"
        lock = read_lock(lock_path)

        for up in updates:
            lock = update_module(lock, up.get("repo") or up.get("name"), up["version"], up["ref"])

        if dry_run:
            return

        write_lock(lock_path, lock)
        pub_cfg = (self.config.get("publisher", {}) or {}).get("github", {}) or {}
        publisher = GitHubPublisherDocker(repo_root=integrator_root, image=docker_image)
        publisher.ensure_repo(owner, integrator_repo, visibility=pub_cfg.get("repo_visibility", "private"))
        publisher.push(owner, integrator_repo, branch=pub_cfg.get("default_branch", "main"))

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from orchestrator.github_publisher_docker import GitHubPublisherDocker


@dataclass
class MultiRepoPublisher:
    repo_root: Path
    image: str

    def publish_repo_folder(self, owner: str, repo: str, folder: Path, visibility: str = "private") -> None:
        pub = GitHubPublisherDocker(repo_root=folder, image=self.image)
        ok = pub.ensure_repo(owner, repo, visibility=visibility)
        if not ok:
            raise RuntimeError(f"Cannot create/view {owner}/{repo}")
        pub.push(owner, repo, branch="main")
        notes = folder / "README.md"
        pub.release("v0.1.0", f"{repo} v0.1.0", str(notes), str(notes))

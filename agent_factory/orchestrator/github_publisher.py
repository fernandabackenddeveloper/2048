from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitHubPublisher:
    repo_root: Path
    owner: str
    repo: str
    visibility: str = "private"
    default_branch: str = "main"
    remote_name: str = "origin"

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=str(self.repo_root), text=True, capture_output=True)

    def ensure_auth(self) -> None:
        if not (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")):
            raise RuntimeError("Missing GH_TOKEN or GITHUB_TOKEN for GitHub publishing")

    def ensure_repo(self) -> None:
        view = self._run(["gh", "repo", "view", f"{self.owner}/{self.repo}"])
        if view.returncode == 0:
            return
        vis = "--private" if self.visibility == "private" else "--public"
        create = self._run(["gh", "repo", "create", f"{self.owner}/{self.repo}", vis, "--confirm"])
        if create.returncode != 0:
            raise RuntimeError(f"gh repo create failed: {create.stderr or create.stdout}")

    def ensure_git_initialized(self) -> None:
        if not (self.repo_root / ".git").exists():
            r = self._run(["git", "init"])
            if r.returncode != 0:
                raise RuntimeError(r.stderr or r.stdout)
        self._run(["git", "checkout", "-B", self.default_branch])

    def ensure_remote(self) -> None:
        url = f"https://github.com/{self.owner}/{self.repo}.git"
        remotes = self._run(["git", "remote", "-v"]).stdout
        if self.remote_name not in remotes:
            r = self._run(["git", "remote", "add", self.remote_name, url])
            if r.returncode != 0:
                raise RuntimeError(r.stderr or r.stdout)

    def commit_all(self, message: str) -> None:
        self._run(["git", "add", "-A"])
        self._run(["git", "commit", "-m", message])

    def push(self) -> None:
        r = self._run(["git", "push", "-u", self.remote_name, self.default_branch, "--force-with-lease"])
        if r.returncode != 0:
            raise RuntimeError(r.stderr or r.stdout)

    def release(self, tag: str, title: str, notes_file: Path, asset: Optional[Path] = None) -> None:
        cmd = ["gh", "release", "create", tag, "--title", title, "--notes-file", str(notes_file)]
        if asset and asset.exists():
            cmd.append(str(asset))
        r = self._run(cmd)
        if r.returncode != 0:
            raise RuntimeError(r.stderr or r.stdout)

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def create_sandbox(repo_root: Path, project: str, task_id: str) -> Path:
    base = repo_root / "runs" / project / "sandboxes"
    base.mkdir(parents=True, exist_ok=True)

    sandbox = base / task_id
    if sandbox.exists():
        shutil.rmtree(sandbox)

    shutil.copytree(
        repo_root,
        sandbox,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "runs"),
    )
    return sandbox


def merge_sandbox(repo_root: Path, sandbox: Path) -> None:
    for src in sandbox.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(sandbox)
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class PatchError(Exception):
    pass


def apply_patch(repo_root: Path, diff_text: str) -> None:
    """
    Apply unified diff using `patch`.
    Raises PatchError on failure.
    """
    try:
        result = subprocess.run(
            ["patch", "-p1", "--forward", "--reject-file=-"],
            cwd=str(repo_root),
            input=diff_text,
            text=True,
            capture_output=True,
        )
    except Exception as e:  # pragma: no cover - subprocess error surface
        raise PatchError(str(e))

    if result.returncode != 0:
        raise PatchError(result.stderr or result.stdout)


def snapshot(repo_root: Path) -> Path:
    """
    Create a full snapshot copy for rollback.
    """
    tmp = Path(tempfile.mkdtemp(prefix="agent-factory-snap-"))
    shutil.copytree(repo_root, tmp / "repo", dirs_exist_ok=True)
    return tmp


def rollback(snapshot_dir: Path, repo_root: Path) -> None:
    if repo_root.exists():
        shutil.rmtree(repo_root)
    shutil.copytree(snapshot_dir / "repo", repo_root, dirs_exist_ok=True)

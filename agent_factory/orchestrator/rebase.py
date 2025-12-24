from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent_factory.orchestrator.patching import apply_patch


def recreate_sandbox_from_repo(repo_root: Path, sandbox_path: Path) -> None:
    """
    Replace sandbox content with a fresh copy of repo_root (current state).
    Keeps sandbox folder path stable.
    """
    if sandbox_path.exists():
        shutil.rmtree(sandbox_path)
    shutil.copytree(
        repo_root,
        sandbox_path,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "runs"),
    )


def rerun_gates_in_sandbox(sandbox: Path) -> bool:
    r = subprocess.run(["pytest", "-q"], cwd=str(sandbox))
    return r.returncode == 0


def rebase_and_reapply(repo_root: Path, sandbox: Path, tests_diff: str, code_diff: str) -> bool:
    recreate_sandbox_from_repo(repo_root, sandbox)

    apply_patch(sandbox, Path(tests_diff).read_text(encoding="utf-8"))
    apply_patch(sandbox, Path(code_diff).read_text(encoding="utf-8"))

    return rerun_gates_in_sandbox(sandbox)

from __future__ import annotations

import shutil
from pathlib import Path


def ensure_modules_dir(integrator_root: Path) -> Path:
    d = integrator_root / "modules"
    d.mkdir(parents=True, exist_ok=True)
    return d


def module_folder_name(repo: str) -> str:
    return repo.replace("/", "__")


def wipe_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)

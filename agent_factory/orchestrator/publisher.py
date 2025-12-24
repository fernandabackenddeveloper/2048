from __future__ import annotations

import datetime
import subprocess
import zipfile
from pathlib import Path


def make_zip(repo_root: Path, out_zip: Path) -> Path:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in repo_root.rglob("*"):
            if p.is_dir():
                continue
            parts = set(p.parts)
            if ".git" in parts or ".venv" in parts or "runs" in parts or "__pycache__" in parts:
                continue
            z.write(p, str(p.relative_to(repo_root)))
    return out_zip


def write_changelog(reports_dir: Path, state: dict) -> Path:
    ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    p = reports_dir / "CHANGELOG.md"
    gates = state.get("gates", [])
    passed = sum(1 for g in gates if g.get("passed"))
    failed = sum(1 for g in gates if not g.get("passed"))
    p.write_text(
        f"# Changelog\n\nGenerated: {ts}\n\n- Gates passed: {passed}\n- Gates failed: {failed}\n",
        encoding="utf-8",
    )
    return p


def git_tag(repo_root: Path, tag: str) -> None:
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], cwd=str(repo_root), check=False)

from __future__ import annotations

import re
from typing import List

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump(version: str, level: str) -> str:
    m = SEMVER_RE.match(version.strip())
    if not m:
        return "0.1.0"
    maj, mi, pa = map(int, m.groups())
    if level == "major":
        return f"{maj+1}.0.0"
    if level == "minor":
        return f"{maj}.{mi+1}.0"
    return f"{maj}.{mi}.{pa+1}"


def classify_changes(changed_files: List[str]) -> str:
    if any(f.startswith("src/") for f in changed_files):
        if any("interface" in f.lower() or "api" in f.lower() for f in changed_files):
            return "minor"
        return "patch"
    return "patch"

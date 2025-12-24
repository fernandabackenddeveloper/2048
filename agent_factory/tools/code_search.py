from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


def find_strings(paths: Iterable[Path], needle: str) -> List[str]:
    matches: List[str] = []
    for path in paths:
        if path.is_file() and needle in path.read_text(encoding="utf-8"):
            matches.append(str(path))
    return matches

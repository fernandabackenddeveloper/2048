from __future__ import annotations

from typing import List


def default_invariants() -> List[str]:
    return [
        "Each Mesh has exactly one owning Object",
        "Cycles are forbidden",
        "Material may be shared between Objects",
    ]

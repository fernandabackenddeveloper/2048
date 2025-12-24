from __future__ import annotations

from typing import Dict, List, Set


def changed_set(changes: Dict[str, List[str]]) -> Set[str]:
    return set(changes.get("created", [])) | set(changes.get("deleted", [])) | set(changes.get("modified", []))


def has_conflict(changes_a: Dict, changes_b: Dict) -> bool:
    return not changed_set(changes_a).isdisjoint(changed_set(changes_b))

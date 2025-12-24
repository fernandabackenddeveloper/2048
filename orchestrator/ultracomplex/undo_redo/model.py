from __future__ import annotations

from typing import Dict, List


def default_undo_model() -> List[Dict[str, str]]:
    return [
        {"command": "Select", "do": "select", "undo": "deselect", "scope": "scene"},
        {"command": "Transform", "do": "apply_transform", "undo": "revert_transform", "scope": "scene"},
        {"command": "Edit", "do": "apply_edit", "undo": "revert_edit", "scope": "object"},
    ]

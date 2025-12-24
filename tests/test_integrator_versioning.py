from pathlib import Path

from orchestrator.integrator.lock import read_lock, update_module, write_lock
from orchestrator.integrator.versioning import bump, classify_changes


def test_bump_and_classify() -> None:
    assert bump("0.1.0", "patch") == "0.1.1"
    assert bump("0.1.0", "minor") == "0.2.0"
    assert classify_changes(["src/api.py"]) == "minor"
    assert classify_changes(["docs/readme.md"]) == "patch"


def test_lock_update_roundtrip(tmp_path: Path) -> None:
    lock_path = tmp_path / "module.lock.json"
    lock = {"owner": "o", "integrator": "i", "modules": [{"name": "core", "repo": "core", "version": "0.1.0", "ref": "r"}]}
    write_lock(lock_path, lock)

    loaded = read_lock(lock_path)
    updated = update_module(loaded, "core", "0.1.1", "refs/tags/v0.1.1")
    write_lock(lock_path, updated)

    final = read_lock(lock_path)
    assert final["modules"][0]["version"] == "0.1.1"
    assert "generated_at" in final

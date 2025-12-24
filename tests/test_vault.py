from pathlib import Path

from orchestrator.vault import RetrievedDoc, Vault, add_local_file, add_note, rebuild_index, retrieve


def test_ingest_and_retrieve_builds_index(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "vault")
    note = add_note(vault, "Onboarding Notes", "Agents collaborate in the orchestrator.", ["Notes", "Agents"])

    source_file = tmp_path / "plan.txt"
    source_file.write_text("This plan covers orchestrator architecture and agents.", encoding="utf-8")
    doc = add_local_file(vault, source_file, "Architecture Plan", ["Reference", "Agents"])

    assert (vault.root / note["path"]).exists()
    assert (vault.root / doc["path"]).exists()

    manifest = vault.load_manifest()
    assert {entry["id"] for entry in manifest} == {note["id"], doc["id"]}
    assert manifest[0]["tags"] == sorted(manifest[0]["tags"])

    rebuild_index(vault)
    results = retrieve(vault, "orchestrator")
    ids = {r.id for r in results}
    assert doc["id"] in ids

    tag_results = retrieve(vault, "agents", tags=["notes"])
    assert any(r.id == note["id"] for r in tag_results)


def test_retrieve_uses_cache_when_available(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "vault")
    add_note(vault, "Cache Test", "Caching retrieval responses for later reuse.", ["cache"])
    rebuild_index(vault)

    first = retrieve(vault, "caching", tags=["cache"])
    assert first
    assert isinstance(first[0], RetrievedDoc)

    inverted = vault.inverted_path
    inverted.write_text("{}", encoding="utf-8")
    cached = retrieve(vault, "caching", tags=["cache"])
    assert [r.id for r in cached] == [r.id for r in first]
    assert any(vault.cache_dir.glob("*.json"))


def test_vault_ingest_index_retrieve(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "knowledge")
    vault.ensure()
    add_note(vault, "Test Doc", "Blender clone requires scene graph and renderer", ["rendering", "scene"])
    rebuild_index(vault)
    hits = retrieve(vault, "scene graph renderer", top_k=3)
    assert len(hits) >= 1
    assert hits[0].id

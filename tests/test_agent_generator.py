import json
from pathlib import Path


def test_generated_registry_exists() -> None:
    reg_path = Path("orchestrator/generator/generated_registry.json")
    assert reg_path.exists()
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert "agents" in data

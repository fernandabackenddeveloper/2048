from pathlib import Path

from orchestrator.planning import generate_plan
from orchestrator.validators import validate_plan_schema


def test_plan_schema_validation_passes_for_deterministic() -> None:
    repo_root = Path(".").resolve()
    plan = generate_plan("Build something web", project="x", stack="web_fullstack")
    ok, msg = validate_plan_schema(repo_root, plan)
    assert ok, msg

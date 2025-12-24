from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def validate_plan_schema(repo_root: Path, plan: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Lightweight schema validation for plans produced by generate_plan.
    We avoid an external jsonschema dependency by performing structured
    checks directly against the expected shape from orchestrator/schemas.
    """

    def _require(condition: bool, path: str, message: str, errors: List[str]) -> None:
        if not condition:
            errors.append(f"{path}: {message}")

    errors: List[str] = []
    _require(isinstance(plan, dict), "<root>", "plan must be a mapping", errors)
    if errors:
        return False, "Schema validation failed: " + " | ".join(errors)

    required_root = ["project", "stack", "created_at", "definition_of_done", "milestones"]
    for key in required_root:
        _require(key in plan, "<root>", f"missing required field '{key}'", errors)

    _require(isinstance(plan.get("definition_of_done"), list), "definition_of_done", "must be a list", errors)
    if isinstance(plan.get("definition_of_done"), list):
        _require(
            all(isinstance(item, str) for item in plan["definition_of_done"]),
            "definition_of_done",
            "items must be strings",
            errors,
        )

    milestones = plan.get("milestones", [])
    _require(isinstance(milestones, list), "milestones", "must be a list", errors)

    def _validate_tasks(tasks: Iterable[Any], base_path: str) -> None:
        owners = {"scaffolder", "qa", "fixer", "docs", "release"}
        for idx, task in enumerate(tasks):
            path = f"{base_path}[{idx}]"
            _require(isinstance(task, dict), path, "task must be a mapping", errors)
            if not isinstance(task, dict):
                continue
            for field in ["id", "description", "expected_output", "dod", "owner", "status"]:
                _require(field in task, path, f"missing required field '{field}'", errors)
            _require(isinstance(task.get("id"), str), f"{path}.id", "must be a string", errors)
            _require(isinstance(task.get("description"), str), f"{path}.description", "must be a string", errors)
            _require(isinstance(task.get("expected_output"), str), f"{path}.expected_output", "must be a string", errors)
            _require(isinstance(task.get("dod"), list), f"{path}.dod", "must be a list", errors)
            if isinstance(task.get("dod"), list):
                _require(all(isinstance(item, str) for item in task["dod"]), f"{path}.dod", "items must be strings", errors)
            _require(task.get("owner") in owners, f"{path}.owner", f"must be one of {sorted(owners)}", errors)
            _require(task.get("status") == "todo", f"{path}.status", "must equal 'todo'", errors)
            if "depends_on" in task:
                _require(isinstance(task["depends_on"], list), f"{path}.depends_on", "must be a list", errors)
                if isinstance(task.get("depends_on"), list):
                    _require(
                        all(isinstance(d, str) for d in task["depends_on"]),
                        f"{path}.depends_on",
                        "items must be strings",
                        errors,
                    )

    if isinstance(milestones, list):
        for mi, milestone in enumerate(milestones):
            m_path = f"milestones[{mi}]"
            _require(isinstance(milestone, dict), m_path, "must be a mapping", errors)
            if not isinstance(milestone, dict):
                continue
            for field in ["id", "title", "features"]:
                _require(field in milestone, m_path, f"missing required field '{field}'", errors)
            _require(isinstance(milestone.get("id"), str), f"{m_path}.id", "must be a string", errors)
            _require(isinstance(milestone.get("title"), str), f"{m_path}.title", "must be a string", errors)
            features = milestone.get("features", [])
            _require(isinstance(features, list), f"{m_path}.features", "must be a list", errors)
            if isinstance(features, list):
                for fi, feature in enumerate(features):
                    f_path = f"{m_path}.features[{fi}]"
                    _require(isinstance(feature, dict), f_path, "must be a mapping", errors)
                    if not isinstance(feature, dict):
                        continue
                    for field in ["id", "title", "tasks"]:
                        _require(field in feature, f_path, f"missing required field '{field}'", errors)
                    _require(isinstance(feature.get("id"), str), f"{f_path}.id", "must be a string", errors)
                    _require(isinstance(feature.get("title"), str), f"{f_path}.title", "must be a string", errors)
                    tasks = feature.get("tasks", [])
                    _require(isinstance(tasks, list), f"{f_path}.tasks", "must be a list", errors)
                    if isinstance(tasks, list):
                        _validate_tasks(tasks, f"{f_path}.tasks")

    if errors:
        return False, "Schema validation failed: " + " | ".join(errors)
    return True, "Plan schema OK"

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Literal, Optional, Tuple

TaskStatus = Literal["pending", "in_progress", "completed", "failed"]


@dataclass
class Task:
    id: str
    description: str
    owner: str
    expected_output: str
    status: TaskStatus = "pending"
    depends_on: List[str] = field(default_factory=list)
    details: Optional[dict] = None


def build_default_tasks(project_name: str) -> List[Task]:
    """Create a minimal, deterministic backlog."""
    return [
        Task(
            id="ingest",
            description=f"Ingest prompt for {project_name}",
            owner="Chief Planner",
            expected_output="input_prompt.md saved",
        ),
        Task(
            id="plan",
            description="Generate backlog, milestones, and DoD",
            owner="Chief Planner",
            expected_output="plan.json",
            depends_on=["ingest"],
        ),
        Task(
            id="scope_guard",
            description="Validate scope for generated plan",
            owner="Scope Guard",
            expected_output="Scope validation recorded",
            depends_on=["plan"],
        ),
        Task(
            id="architecture",
            description="Draft initial ADR and architecture notes",
            owner="Architect",
            expected_output="ADR-0001.md",
            depends_on=["scope_guard"],
        ),
        Task(
            id="scaffold",
            description="Produce repository scaffold and stack selection",
            owner="Scaffolder",
            expected_output="scaffold metadata and logs",
            depends_on=["architecture"],
        ),
        Task(
            id="implement",
            description="Fan-out implementation across tasks",
            owner="Implementer",
            expected_output="tasks executed in sandboxes",
            depends_on=["scaffold"],
        ),
        Task(
            id="qa",
            description="Run lint/test smoke placeholder",
            owner="QA Agent",
            expected_output="qa_report.json",
            depends_on=["scaffold"],
        ),
        Task(
            id="docs",
            description="Generate quickstart documentation",
            owner="Docs Agent",
            expected_output="README or quickstart updated",
            depends_on=["qa"],
        ),
        Task(
            id="release",
            description="Summarize outputs and prepare final report",
            owner="Release Agent",
            expected_output="final_report.md",
            depends_on=["docs"],
        ),
    ]


def iter_plan_tasks(plan: Dict[str, any]) -> Iterator[Tuple[Dict, Dict, Dict]]:
    for milestone in plan.get("milestones", []):
        for feature in milestone.get("features", []):
            for task in feature.get("tasks", []):
                yield milestone, feature, task

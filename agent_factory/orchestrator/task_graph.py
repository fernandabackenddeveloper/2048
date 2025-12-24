from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

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
            id="scope_guard",
            description="Validate prompt scope and preconditions",
            owner="Scope Guard",
            expected_output="Scope validation recorded",
        ),
        Task(
            id="ingest",
            description=f"Ingest prompt for {project_name}",
            owner="Chief Planner",
            expected_output="input_prompt.md saved",
            depends_on=["scope_guard"],
        ),
        Task(
            id="plan",
            description="Generate backlog, milestones, and DoD",
            owner="Chief Planner",
            expected_output="plan.json",
            depends_on=["ingest"],
        ),
        Task(
            id="architecture",
            description="Draft initial ADR and architecture notes",
            owner="Architect",
            expected_output="ADR-0001.md",
            depends_on=["plan"],
        ),
        Task(
            id="scaffold",
            description="Produce repository scaffold and stack selection",
            owner="Scaffolder",
            expected_output="scaffold metadata and logs",
            depends_on=["architecture"],
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

from __future__ import annotations

import datetime
from typing import Any, Dict, List
import re


def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _task(
    tid: str,
    desc: str,
    expected: str,
    dod: List[str],
    owner: str,
    depends_on: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "id": tid,
        "description": desc,
        "expected_output": expected,
        "dod": dod,
        "owner": owner,
        "status": "todo",
        "depends_on": depends_on or [],
        "touch_hints": infer_touch_hints(desc),
    }


def infer_touch_hints(task_desc: str) -> List[str]:
    s = task_desc.lower()
    hints: List[str] = []
    if "test" in s or "pytest" in s:
        hints.append("tests/")
    if "readme" in s or "docs" in s:
        hints.append("docs/")
    if "docker" in s:
        hints.append("Dockerfile")
    if "ci" in s or "github actions" in s:
        hints.append("ci/")
    if "orchestrator" in s:
        hints.append("orchestrator/")
    return hints


def detect_capabilities(prompt_text: str) -> Dict[str, bool]:
    p = prompt_text.lower()
    return {
        "wants_ci": True,
        "wants_docker": True,
        "wants_tests": True,
        "wants_docs": True,
        "mentions_godot": "godot" in p,
        "mentions_web": any(k in p for k in ["web", "api", "frontend", "backend"]),
    }


def generate_plan(prompt_text: str, project: str, stack: str) -> Dict[str, Any]:
    caps = detect_capabilities(prompt_text)

    definition_of_done = [
        "Build passes",
        "Lint passes (if configured by stack)",
        "Tests pass",
        "README + docs exist",
        "Final report generated (md + json)",
        "State + logs written in runs/<project>/",
    ]

    milestones = []

    # M1 Scaffold
    milestones.append(
        {
            "id": "M1",
            "title": "Scaffold + baseline tooling",
            "features": [
                {
                    "id": "F1",
                    "title": "Repo scaffold",
                    "tasks": [
                        _task(
                            "M1_T1",
                            "Create baseline scaffold in runs/<project>/workspace from stack template",
                            "workspace populated with template files",
                            ["workspace exists", "template copied"],
                            "scaffolder",
                        ),
                        _task(
                            "M1_T2",
                            "Ensure CI config exists and is valid",
                            "ci/github_actions.yml present",
                            ["CI file exists", "CI references pytest"],
                            "scaffolder",
                        ),
                    ],
                }
            ],
        }
    )

    # M2 QA + Fix loop
    milestones.append(
        {
            "id": "M2",
            "title": "QA gates + fix loop",
            "features": [
                {
                    "id": "F1",
                    "title": "Quality gates",
                    "tasks": [
                        _task(
                            "M2_T1",
                            "Run stack gates (build/lint/test) and capture GateResults",
                            "state.json contains gate results",
                            ["GateResults recorded", "Failing gates include stdout/stderr"],
                            "qa",
                            depends_on=["M1_T1", "M1_T2"],
                        ),
                        _task(
                            "M2_T2",
                            "On failures, apply minimal patches up to max retries and log attempts",
                            "fixer.jsonl contains fix attempts; incidents on exhaustion",
                            ["Max retries enforced", "Incident created on exhaustion"],
                            "fixer",
                            depends_on=["M1_T1", "M1_T2"],
                        ),
                    ],
                }
            ],
        }
    )

    # M3 Docs + Release
    milestones.append(
        {
            "id": "M3",
            "title": "Docs + final reports",
            "features": [
                {
                    "id": "F1",
                    "title": "Documentation and reporting",
                    "tasks": [
                        _task(
                            "M3_T1",
                            "Write docs/architecture.md + optional ui style guide placeholders",
                            "docs created",
                            ["docs/architecture.md exists"],
                            "docs",
                            depends_on=["M1_T1", "M1_T2"],
                        ),
                        _task(
                            "M3_T2",
                            "Write final_report.md and final_report.json",
                            "reports generated",
                            ["final_report.md exists", "final_report.json exists"],
                            "release",
                            depends_on=["M2_T1", "M2_T2", "M3_T1"],
                        ),
                    ],
                }
            ],
        }
    )

    return {
        "project": project,
        "stack": stack,
        "created_at": utc_now(),
        "definition_of_done": definition_of_done,
        "milestones": milestones,
        "input_prompt_excerpt": prompt_text[:5000],
        "capabilities": caps,
    }

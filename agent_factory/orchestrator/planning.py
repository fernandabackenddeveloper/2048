from __future__ import annotations

import datetime
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _task(tid: str, desc: str, expected: str, dod: List[str], owner: str) -> Dict[str, Any]:
    return {
        "id": tid,
        "description": desc,
        "expected_output": expected,
        "dod": dod,
        "owner": owner,
        "status": "todo",
    }


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
                            "T1",
                            "Create baseline scaffold in runs/<project>/workspace from stack template",
                            "workspace populated with template files",
                            ["workspace exists", "template copied"],
                            "scaffolder",
                        ),
                        _task(
                            "T2",
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
                            "T1",
                            "Run stack gates (build/lint/test) and capture GateResults",
                            "state.json contains gate results",
                            ["GateResults recorded", "Failing gates include stdout/stderr"],
                            "qa",
                        ),
                        _task(
                            "T2",
                            "On failures, apply minimal patches up to max retries and log attempts",
                            "fixer.jsonl contains fix attempts; incidents on exhaustion",
                            ["Max retries enforced", "Incident created on exhaustion"],
                            "fixer",
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
                            "T1",
                            "Write docs/architecture.md + optional ui style guide placeholders",
                            "docs created",
                            ["docs/architecture.md exists"],
                            "docs",
                        ),
                        _task(
                            "T2",
                            "Write final_report.md and final_report.json",
                            "reports generated",
                            ["final_report.md exists", "final_report.json exists"],
                            "release",
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

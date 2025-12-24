from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from agent_factory.agents.implementer import ImplementerAgent
from agent_factory.orchestrator.state_store import StateStore


def implement_task_worker(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Picklable worker for ProcessPool.
    args:
      - repo_root
      - runs_dir
      - project
      - stack
      - task
    """
    repo_root = Path(args["repo_root"])
    runs_dir = Path(args["runs_dir"])
    project = args["project"]
    stack_name = args["stack"]
    task = args["task"]

    store = StateStore(base_path=runs_dir)
    run_dir = runs_dir / project

    implementer = ImplementerAgent(run_dir=run_dir, stack=stack_name, state_store=store, repo_root=repo_root)
    return implementer.run(task)

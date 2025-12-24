from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

from agent_factory.orchestrator.router import TaskRouter
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.task_graph import Task, build_default_tasks
from agent_factory.agents.chief_planner import ChiefPlanner
from agent_factory.agents.architect import Architect
from agent_factory.agents.scaffolder import Scaffolder
from agent_factory.agents.qa_agent import QAAgent
from agent_factory.agents.docs_agent import DocsAgent
from agent_factory.agents.release_agent import ReleaseAgent


def run_pipeline(prompt: str, project_name: str, stack: str = "web_fullstack") -> Path:
    state_store = StateStore(base_path=Path("agent_factory") / "runs")
    run_dir = state_store.init_run(project_name, prompt, stack)

    tasks = build_default_tasks(project_name)
    state_store.save_plan(run_dir, tasks)

    agents = _build_agents(run_dir, stack, state_store)
    router = TaskRouter(tasks)

    def _runner(task: Task) -> None:
        agents[task.id]()

    router.run(_runner)
    return run_dir


def _build_agents(run_dir: Path, stack: str, state_store: StateStore) -> Dict[str, callable]:
    chief_planner = ChiefPlanner(run_dir, stack, state_store)
    architect = Architect(run_dir, stack, state_store)
    scaffolder = Scaffolder(run_dir, stack, state_store)
    qa_agent = QAAgent(run_dir, stack, state_store)
    docs_agent = DocsAgent(run_dir, stack, state_store)
    release_agent = ReleaseAgent(run_dir, stack, state_store)

    return {
        "ingest": chief_planner.ingest,
        "plan": chief_planner.plan,
        "architecture": architect.compose_adr,
        "scaffold": scaffolder.scaffold,
        "qa": qa_agent.run_suite,
        "docs": docs_agent.write_quickstart,
        "release": release_agent.prepare_report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Agent Factory pipeline.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", type=str, help="Prompt text to ingest.")
    group.add_argument("--prompt-file", type=Path, help="Path to a prompt file.")
    parser.add_argument("--project", type=str, default="sample-project", help="Project name.")
    parser.add_argument(
        "--stack", type=str, default="web_fullstack", help="Stack plugin to use (default: web_fullstack)."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    else:
        prompt = args.prompt
    run_dir = run_pipeline(prompt=prompt, project_name=args.project, stack=args.stack)
    print(f"Run completed. Artifacts stored in: {run_dir}")


if __name__ == "__main__":
    main()

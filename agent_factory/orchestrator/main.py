from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

from agent_factory.orchestrator.router import TaskRouter
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.task_graph import Task, build_default_tasks
from agent_factory.agents.chief_planner import ChiefPlanner
from agent_factory.agents.architect import Architect
from agent_factory.agents.scope_guard import ScopeGuard
from agent_factory.agents.scaffolder import Scaffolder
from agent_factory.agents.qa_agent import QAAgent
from agent_factory.agents.docs_agent import DocsAgent
from agent_factory.agents.release_agent import ReleaseAgent


def run_pipeline(
    prompt: str,
    project_name: str,
    stack: Optional[str] = None,
    *,
    config_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Path:
    config = load_config(config_path)
    resolved_stack = stack or config.get("default_stack", "web_fullstack")
    run_root = Path(config.get("run_root", "runs"))

    state_store = StateStore(base_path=run_root)
    run_dir = state_store.init_run(
        project_name=project_name,
        prompt=prompt,
        stack=resolved_stack,
        config=config,
    )

    tasks = build_default_tasks(project_name)
    state_store.save_plan(run_dir, tasks)

    agents = _build_agents(run_dir, resolved_stack, state_store, config, dry_run)
    router = TaskRouter(tasks)

    def _runner(task: Task) -> None:
        agents[task.id]()

    router.run(_runner)
    return run_dir


def _build_agents(
    run_dir: Path,
    stack: str,
    state_store: StateStore,
    config: Dict,
    dry_run: bool,
) -> Dict[str, callable]:
    scope_guard = ScopeGuard(run_dir, state_store)
    chief_planner = ChiefPlanner(run_dir, stack, state_store)
    architect = Architect(run_dir, stack, state_store)
    scaffolder = Scaffolder(run_dir, stack, state_store, config=config, dry_run=dry_run)
    qa_agent = QAAgent(run_dir, stack, state_store, dry_run=dry_run)
    docs_agent = DocsAgent(run_dir, stack, state_store)
    release_agent = ReleaseAgent(run_dir, stack, state_store, dry_run=dry_run)

    return {
        "scope_guard": scope_guard.validate,
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
    parser.add_argument("--config", type=Path, help="Path to a custom config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing external commands.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    else:
        prompt = args.prompt
    run_dir = run_pipeline(
        prompt=prompt,
        project_name=args.project,
        stack=args.stack,
        config_path=args.config,
        dry_run=args.dry_run,
    )
    print(json.dumps({"run_dir": str(run_dir), "status": "completed"}))
    print("Done")


if __name__ == "__main__":
    main()


def load_config(config_path: Optional[Path] = None) -> Dict:
    """Load configuration from provided path or packaged default."""
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    search_paths.append(Path("config.yaml"))
    search_paths.append(Path("agent_factory") / "orchestrator" / "config.yaml")

    for path in search_paths:
        if path.exists():
            return json.loads(path.read_text()) if path.suffix == ".json" else _load_yaml(path)
    return {}


def _load_yaml(path: Path) -> Dict:
    import yaml  # type: ignore

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

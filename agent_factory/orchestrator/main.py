from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from agent_factory.orchestrator.router import TaskRouter
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.task_graph import Task, build_default_tasks, iter_plan_tasks
from agent_factory.agents.chief_planner import ChiefPlanner
from agent_factory.agents.architect import Architect
from agent_factory.agents.scope_guard import ScopeGuard
from agent_factory.agents.scaffolder import Scaffolder
from agent_factory.agents.implementer import ImplementerAgent
from agent_factory.agents.qa_agent import QAAgent
from agent_factory.agents.docs_agent import DocsAgent
from agent_factory.agents.release_agent import ReleaseAgent
from agent_factory.orchestrator.pool_process import run_process_pool, schedule_batches
from agent_factory.orchestrator.merge_lock import MergeLock
from agent_factory.orchestrator.sandbox import merge_sandbox
from agent_factory.orchestrator.changes import changed_files
from agent_factory.orchestrator.worker import implement_task_worker


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
    implementer = ImplementerAgent(run_dir, stack, state_store)
    qa_agent = QAAgent(run_dir, stack, state_store, dry_run=dry_run)
    docs_agent = DocsAgent(run_dir, stack, state_store)
    release_agent = ReleaseAgent(run_dir, stack, state_store, dry_run=dry_run)

    return {
        "scope_guard": scope_guard.validate,
        "ingest": chief_planner.ingest,
        "plan": chief_planner.plan,
        "architecture": architect.compose_adr,
        "scaffold": scaffolder.scaffold,
        "implement": lambda: _fan_out(run_dir, implementer, state_store, config),
        "qa": qa_agent.run_suite,
        "docs": docs_agent.write_quickstart,
        "release": release_agent.prepare_report,
    }

def _fan_out(run_dir: Path, implementer: ImplementerAgent, state_store: StateStore, config: Dict) -> None:
    plan_path = run_dir / "plan.json"
    if not plan_path.exists():
        return
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    todo_tasks = []
    for _, _, task in iter_plan_tasks(plan):
        if task.get("status") == "todo":
            todo_tasks.append(task)

    # Heuristic touch hints
    for t in todo_tasks:
        owner = (t.get("owner") or "")
        if owner == "docs":
            t["touch_hints"] = list(set((t.get("touch_hints") or []) + ["docs/"]))
        elif owner == "qa":
            t["touch_hints"] = list(set((t.get("touch_hints") or []) + ["tests/"]))
        elif owner == "scaffolder":
            t["touch_hints"] = list(set((t.get("touch_hints") or []) + ["orchestrator/", "ci/", "Dockerfile", "Makefile"]))
        else:
            t["touch_hints"] = t.get("touch_hints") or []

    batches = schedule_batches(todo_tasks)
    state_store.append_jsonl(
        run_dir,
        "logs/pool.jsonl",
        {"ts": state_store.utc_now(), "event": "batches_scheduled", "batches": [[t["id"] for t in b] for b in batches]},
    )

    max_workers = int(config.get("implementer_pool", {}).get("max_workers", 2))
    lock = MergeLock(lockfile=run_dir / "locks" / "merge.lock")
    merged_files = set()

    def _work(t: Dict[str, Any]) -> Dict[str, Any]:
        args = {
            "repo_root": str(Path(".").resolve()),
            "runs_dir": str(run_dir.parent),
            "project": run_dir.name,
            "stack": t.get("owner", "web_fullstack"),
            "task": t,
        }
        return implement_task_worker(args)

    all_results = []
    for batch in batches:
        batch_results = run_process_pool(batch, _work, max_workers=max_workers)
        all_results.extend(batch_results)

        res_by_id = {r.task_id: r.result for r in batch_results}
        for _, _, task in iter_plan_tasks(plan):
            tid = task["id"]
            if tid not in res_by_id:
                continue
            result = res_by_id[tid]
            status = result.get("status")
            if status == "ready_to_merge":
                change_set = changed_files(result.get("changes", {}))
                if merged_files & change_set:
                    task["status"] = "failed"
                    continue
                lock.acquire()
                try:
                    merge_sandbox(Path("."), Path(result["sandbox"]))
                    merged_files |= change_set
                    task["status"] = "done"
                finally:
                    lock.release()
            elif status == "skipped":
                task["status"] = "skipped"
            else:
                task["status"] = "failed"

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    state = state_store.read_state(run_dir)
    state["tasks"] = plan.get("milestones", [])
    state_store.save_state(run_dir, state)


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

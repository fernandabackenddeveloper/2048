from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from agent_factory.agents.knowledge_harvester import KnowledgeHarvester
from agent_factory.agents.knowledge_curator import KnowledgeCurator
from agent_factory.agents.module_scaffolder import ModuleScaffolder
from agent_factory.agents.integrator_scaffolder import IntegratorScaffolder
from agent_factory.agents.module_release_agent import ModuleReleaseAgent
from agent_factory.agents.integrator_update_agent import IntegratorUpdateAgent
from agent_factory.agents.agent_generator import AgentGenerator
from agent_factory.agents.fsm_agent import FSMAgent
from agent_factory.agents.scene_graph_agent import SceneGraphAgent
from agent_factory.agents.protocol_agent import ProtocolAgent
from agent_factory.agents.undo_agent import UndoAgent
from agent_factory.orchestrator.pool_process import run_process_pool, schedule_batches
from agent_factory.orchestrator.merge_lock import MergeLock
from agent_factory.orchestrator.sandbox import merge_sandbox
from agent_factory.orchestrator.worker import implement_task_worker
from agent_factory.orchestrator.dag import topo_sort
from agent_factory.orchestrator.conflicts import has_conflict
from agent_factory.orchestrator.rebase import rebase_and_reapply
from agent_factory.agents.prd_agent import PRDAgent
from agent_factory.agents.spec_agent import SpecAgent
from agent_factory.agents.decomposer_agent import DecomposerAgent
from agent_factory.orchestrator.spec_pipeline import backlog_to_plan
from agent_factory.orchestrator.marketplace.router import load_capabilities, pick_capability
from agent_factory.orchestrator.marketplace.budget import BudgetManager
from agent_factory.orchestrator.marketplace.scheduler import CapabilityScheduler
from orchestrator.integrator.gates import run_integration_gates
from orchestrator.integrator.matrix import build_matrix
from orchestrator.integrator.lock import read_lock, write_lock, update_module
from orchestrator.multirepo.planner import derive_modules, write_multirepo_plan
from orchestrator.multirepo.publisher import MultiRepoPublisher
from orchestrator.vault.vault import Vault
from orchestrator.vault.indexer import rebuild_index


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

    agents = _build_agents(run_dir, resolved_stack, state_store, config, dry_run, prompt)
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
    prompt_text: str,
) -> Dict[str, callable]:
    scope_guard = ScopeGuard(run_dir, state_store)
    chief_planner = ChiefPlanner(run_dir, stack, state_store)
    architect = Architect(run_dir, stack, state_store)
    scaffolder = Scaffolder(run_dir, stack, state_store, config=config, dry_run=dry_run)
    implementer = ImplementerAgent(run_dir, stack, state_store)
    qa_agent = QAAgent(run_dir, stack, state_store, dry_run=dry_run)
    docs_agent = DocsAgent(run_dir, stack, state_store)
    release_agent = ReleaseAgent(run_dir, stack, state_store, dry_run=dry_run)
    prd_agent = PRDAgent(run_dir, stack, state_store, config=config)
    spec_agent = SpecAgent(run_dir, stack, state_store, config=config)
    decomposer_agent = DecomposerAgent(run_dir, stack, state_store, config=config)
    knowledge_harvester = KnowledgeHarvester(run_dir, stack, state_store)
    knowledge_curator = KnowledgeCurator(run_dir, stack, state_store)
    module_scaffolder = ModuleScaffolder(run_dir, stack, state_store)
    integrator_scaffolder = IntegratorScaffolder(run_dir, stack, state_store)
    module_release_agent = ModuleReleaseAgent(run_dir, stack, state_store, config=config)
    integrator_update_agent = IntegratorUpdateAgent(run_dir, stack, state_store, config=config)
    agent_generator = AgentGenerator(run_dir, stack, state_store, config=config, repo_root=Path(__file__).resolve().parents[2])
    fsm_agent = FSMAgent(run_dir, stack, state_store)
    scene_graph_agent = SceneGraphAgent(run_dir, stack, state_store)
    protocol_agent = ProtocolAgent(run_dir, stack, state_store)
    undo_agent = UndoAgent(run_dir, stack, state_store)
    repo_root = Path(__file__).resolve().parents[2]

    plan_state: Dict[str, Any] = {}

    def run_prd() -> None:
        plan_state["prd"] = prd_agent.run(prompt_text)

    def run_spec() -> None:
        prd = plan_state.get("prd") or {}
        plan_state["specs"] = spec_agent.run(prd)

    def run_decomposer() -> None:
        prd = plan_state.get("prd") or {}
        specs = plan_state.get("specs") or []
        backlog = decomposer_agent.run(prd, specs)
        plan_state["backlog"] = backlog
        plan = backlog_to_plan(project=state_store.read_state(run_dir)["project"], stack=stack, backlog=backlog)
        (run_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        state = state_store.read_state(run_dir)
        state["tasks"] = plan.get("milestones", [])
        state_store.save_state(run_dir, state)

    def run_multirepo_planner() -> None:
        specs = plan_state.get("specs") or []
        owner = (config.get("publisher", {}).get("github", {}) or {}).get("owner", "your-owner")
        docker_image = (
            config.get("tooling", {}).get("docker", {}).get("image", "agent-factory/runner-web_fullstack:0.1.0")
        )
        multirepo = derive_modules(
            project=state_store.read_state(run_dir)["project"], owner=owner, specs=specs, stack=stack, docker_image=docker_image
        )
        plan_state["multirepo"] = multirepo
        write_multirepo_plan(run_dir, multirepo)

        workspace = run_dir / "modules_workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        for module in multirepo.get("modules", []):
            module_scaffolder.run(module, workspace)

        integrator_scaffolder.run(multirepo, workspace)

        publisher_cfg = config.get("publisher", {}).get("github", {}) or {}
        if publisher_cfg.get("enabled"):
            pub = MultiRepoPublisher(repo_root=repo_root, image=docker_image)
            visibility = publisher_cfg.get("repo_visibility", "private")
            for module in multirepo.get("modules", []):
                pub.publish_repo_folder(owner, module["repo"], workspace / module["repo"], visibility=visibility)
            pub.publish_repo_folder(owner, multirepo["integrator_repo"], workspace / multirepo["integrator_repo"], visibility=visibility)

    def run_agent_generator() -> None:
        prd = plan_state.get("prd") or {}
        specs = plan_state.get("specs") or []
        agent_generator.run(prd, specs, caps={})
        # Merge generated capabilities into marketplace
        from orchestrator.generator.registry import load_registry
        from orchestrator.generator.bundle import merge_generated_capabilities

        reg = load_registry(repo_root)
        merge_generated_capabilities(repo_root, reg)

    def run_ultracomplex_models() -> None:
        specs = plan_state.get("specs") or []
        first_spec = specs[0] if specs else {"domain": "core", "module": "orchestrator"}
        fsm = fsm_agent.run(first_spec)
        graph = scene_graph_agent.run(first_spec)
        protocol = protocol_agent.run(first_spec)
        undo_model = undo_agent.run(first_spec)

        from orchestrator.ultracomplex.contracts import generate_contract_tests, write_contract_tests

        content = generate_contract_tests(fsm, graph, protocol)
        write_contract_tests(run_dir, content)

    def run_knowledge_harvest() -> None:
        knowledge_harvester.run()
        vault = Vault(repo_root / "knowledge")
        rebuild_index(vault)

    def run_knowledge_curator() -> None:
        knowledge_curator.run()

    def run_release() -> None:
        multirepo = plan_state.get("multirepo") or {}
        workspace = run_dir / "modules_workspace"
        updates: List[Dict[str, Any]] = []
        pub_cfg = (config.get("publisher", {}) or {}).get("github", {}) or {}
        owner = pub_cfg.get("owner", "your-owner")
        docker_image = (config.get("tooling", {}).get("docker", {}) or {}).get(
            "image", "agent-factory/runner-web_fullstack:0.1.0"
        )

        reports_dir = run_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        if multirepo and workspace.exists():
            for module in multirepo.get("modules", []):
                module_root = workspace / module["repo"]
                if not module_root.exists():
                    continue
                # Placeholder heuristic; in a real run use actual change manifest
                changed_files = ["src/"] if not dry_run else []
                meta = module_release_agent.run(
                    owner=owner,
                    repo_name=module["repo"],
                    module_root=module_root,
                    changed_files=changed_files,
                    docker_image=docker_image,
                    dry_run=dry_run,
                )
                updates.append(meta)

            integrator_root = workspace / multirepo.get("integrator_repo", "")
            if integrator_root.exists() and updates:
                if dry_run:
                    lock_path = integrator_root / "module.lock.json"
                    lock = read_lock(lock_path)
                    for up in updates:
                        lock = update_module(lock, up.get("repo"), up["version"], up["ref"])
                    write_lock(lock_path, lock)
                    gates_result = {"gates": []}
                    ok_all = True
                else:
                    integrator_update_agent.run(
                        owner=owner,
                        integrator_repo=multirepo["integrator_repo"],
                        integrator_root=integrator_root,
                        updates=updates,
                        docker_image=docker_image,
                        dry_run=False,
                    )
                    ok_all, gates_result = run_integration_gates(integrator_root, docker_image)

                (reports_dir / "integration_gates.json").write_text(
                    json.dumps(gates_result, indent=2),
                    encoding="utf-8",
                )
                matrix = build_matrix(state_store.read_state(run_dir)["project"])
                (reports_dir / "compat_matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")
        else:
            matrix = build_matrix(state_store.read_state(run_dir)["project"])
            (reports_dir / "compat_matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")

        release_agent.prepare_report()

    return {
        "scope_guard": scope_guard.validate,
        "ingest": chief_planner.ingest,
        "prd": run_prd,
        "spec": run_spec,
        "decomposer": run_decomposer,
        "agent_generator": run_agent_generator,
        "ultracomplex_models": run_ultracomplex_models,
        "multirepo_plan": run_multirepo_planner,
        "knowledge_harvester": run_knowledge_harvest,
        "knowledge_curator": run_knowledge_curator,
        "architecture": architect.compose_adr,
        "scaffold": scaffolder.scaffold,
        "implement": lambda: _fan_out(run_dir, implementer, state_store, config),
        "qa": qa_agent.run_suite,
        "docs": docs_agent.write_quickstart,
        "release": run_release,
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

    todo_tasks = topo_sort(todo_tasks)

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
    merged: Dict[str, list] = {"created": [], "deleted": [], "modified": []}
    repo_root = Path(__file__).resolve().parents[2]

    def merge_union(base: Dict[str, list], inc: Dict[str, list]) -> Dict[str, list]:
        for k in ["created", "deleted", "modified"]:
            base[k] = sorted(list(set(base[k]) | set(inc.get(k, []))))
        return base

    def _work(t: Dict[str, Any]) -> Dict[str, Any]:
        args = {
            "repo_root": str(Path(".").resolve()),
            "runs_dir": str(run_dir.parent),
            "project": run_dir.name,
            "stack": t.get("owner", "web_fullstack"),
            "task": t,
        }
        return implement_task_worker(args)

    repo_root = Path(__file__).resolve().parents[2]
    caps = load_capabilities(repo_root)
    budgets = BudgetManager({c.name: c.budget for c in caps.values()})
    sched = CapabilityScheduler({c.name: c.concurrency for c in caps.values()})

    for _, _, task in iter_plan_tasks(plan):
        task["capability"] = pick_capability(caps, task).name

    queue = [t for _, _, t in iter_plan_tasks(plan) if t.get("status") == "todo"]
    while queue:
        progressed = False
        for task in list(queue):
            cap = task.get("capability")
            if not budgets.can_start(cap) or not sched.can_run(cap):
                continue
            budgets.started(cap)
            sched.start(cap)
            state_store.append_jsonl(
                run_dir,
                "logs/dispatch.jsonl",
                {"ts": state_store.utc_now(), "task": task["id"], "capability": cap},
            )
            queue.remove(task)
            res = _work(task)

            status = res.get("status")
            if status == "ready_to_merge":
                if has_conflict(merged, res.get("changes", {})):
                    patches = res.get("patches") or {}
                    tests_diff = patches.get("tests")
                    code_diff = patches.get("code")

                    if tests_diff and code_diff:
                        ok = rebase_and_reapply(repo_root, Path(res["sandbox"]), tests_diff, code_diff)
                        state_store.append_jsonl(
                            run_dir,
                            "logs/conflicts.jsonl",
                            {
                                "ts": state_store.utc_now(),
                                "task": task["id"],
                                "event": "rebase_attempt",
                                "result": "ok" if ok else "fail",
                            },
                        )
                        if ok:
                            lock.acquire()
                            try:
                                merge_sandbox(repo_root, Path(res["sandbox"]))
                                merged = merge_union(merged, res.get("changes", {}))
                                task["status"] = "done"
                            finally:
                                lock.release()
                            sched.finish(cap)
                            budgets.finished(cap)
                            progressed = True
                            continue

                    task["status"] = "blocked"
                    state_store.append_jsonl(
                        run_dir,
                        "logs/conflicts.jsonl",
                        {
                            "ts": state_store.utc_now(),
                            "task": task["id"],
                            "event": "merge_blocked_overlap",
                            "changes": res.get("changes", {}),
                            "note": "Rebase failed or missing patches",
                        },
                    )
                else:
                    lock.acquire()
                    try:
                        merge_sandbox(repo_root, Path(res["sandbox"]))
                        merged = merge_union(merged, res.get("changes", {}))
                        task["status"] = "done"
                    finally:
                        lock.release()
            elif status == "skipped":
                task["status"] = "skipped"
            else:
                task["status"] = status or "failed"

            sched.finish(cap)
            budgets.finished(cap)
            progressed = True
        if not progressed:
            break

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

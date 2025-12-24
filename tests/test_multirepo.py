import json
from pathlib import Path

from agent_factory.agents.integrator_scaffolder import IntegratorScaffolder
from agent_factory.agents.module_scaffolder import ModuleScaffolder
from agent_factory.orchestrator.state_store import StateStore
from orchestrator.multirepo.planner import derive_modules, write_multirepo_plan


def test_derive_modules_groups_by_domain(tmp_path: Path) -> None:
    specs = [
        {"domain": "core", "module": "orchestrator"},
        {"domain": "core", "module": "tools"},
        {"domain": "ui", "module": "dashboard"},
    ]

    plan = derive_modules("demo", "owner", specs, "web_fullstack", "image")
    assert plan["integrator_repo"] == "af-demo-integrator"
    assert len(plan["modules"]) == 2
    domains = {m["name"] for m in plan["modules"]}
    assert {"core", "ui"} == domains

    out_path = write_multirepo_plan(tmp_path, plan)
    assert out_path.exists()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["project"] == "demo"


def test_scaffolders_create_module_and_integrator(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    state_store = StateStore(tmp_path)

    module = {"repo": "af-demo-core", "domains": ["core/orchestrator"]}
    workspace = tmp_path / "ws"
    module_root = ModuleScaffolder(run_dir, "stack", state_store).run(module, workspace)
    assert (module_root / "README.md").exists()
    assert (module_root / "tests" / "test_smoke.py").exists()

    multirepo = {"integrator_repo": "af-demo-integrator", "owner": "owner", "modules": [module]}
    integrator_root = IntegratorScaffolder(run_dir, "stack", state_store).run(multirepo, workspace)
    assert (integrator_root / "module.lock.json").exists()
    lock = json.loads((integrator_root / "module.lock.json").read_text(encoding="utf-8"))
    assert lock["modules"][0]["repo"] == "af-demo-core"
    assert lock["modules"][0]["version"] == "0.1.0"
    assert (integrator_root / "scripts" / "fetch_modules.py").exists()
    assert (integrator_root / "ci" / "github_actions_integrator.yml").exists()

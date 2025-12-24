from pathlib import Path

import yaml

from agent_factory.orchestrator.main import run_pipeline


def test_run_pipeline_creates_artifacts(tmp_path: Path) -> None:
    prompt = "Test project for agent factory."
    project_name = "unit-test"
    repo_root = Path(__file__).resolve().parents[1]
    cwd = tmp_path
    config_path = cwd / "config.yaml"
    config = {
        "default_stack": "web_fullstack",
        "run_root": str(cwd / "runs"),
        "stack_root": str(repo_root / "stacks"),
        "sandbox": {"allow_commands": ["python", "pytest"]},
    }
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(cwd)
        run_dir = run_pipeline(
            prompt=prompt,
            project_name=project_name,
            stack="web_fullstack",
            config_path=config_path,
            dry_run=True,
        )
        assert run_dir.exists()
        assert (run_dir / "plan.json").exists()
        assert (run_dir / "state.json").exists()
        assert (run_dir / "env_snapshot.json").exists()
        assert (run_dir / "reports" / "final_report.md").exists()
        final_json = (run_dir / "reports" / "final_report.json").read_text(encoding="utf-8")
        assert "dry-run" in final_json
    finally:
        os.chdir(original_cwd)

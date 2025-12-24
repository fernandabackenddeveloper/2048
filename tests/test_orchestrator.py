from pathlib import Path

from agent_factory.orchestrator.main import run_pipeline


def test_run_pipeline_creates_artifacts(tmp_path: Path) -> None:
    prompt = "Test project for agent factory."
    project_name = "unit-test"
    # Run pipeline in a temporary cwd by monkeypatching the runs path via chdir.
    # The orchestrator writes into agent_factory/runs relative to CWD.
    cwd = tmp_path
    (cwd / "agent_factory").mkdir()
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(cwd)
        run_dir = run_pipeline(
            prompt=prompt,
            project_name=project_name,
            stack="web_fullstack",
            dry_run=True,
        )
        assert run_dir.exists()
        assert (run_dir / "plan.json").exists()
        assert (run_dir / "state.json").exists()
        assert (run_dir / "env_snapshot.json").exists()
        assert (run_dir / "reports" / "final_report.md").exists()
        assert (run_dir / "reports" / "final_report.json").exists()
    finally:
        os.chdir(original_cwd)

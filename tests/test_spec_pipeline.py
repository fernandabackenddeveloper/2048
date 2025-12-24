from pathlib import Path

from agent_factory.orchestrator.main import run_pipeline


def test_prd_spec_backlog_files_exist_after_run(tmp_path: Path) -> None:
    prompt = "Create a sample project."
    project_name = "spec-test"
    repo_root = Path(__file__).resolve().parents[1]
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                f"default_stack: web_fullstack",
                f"run_root: {tmp_path}/runs",
                f"stack_root: {repo_root}/stacks",
                "sandbox:",
                "  allow_commands:",
                "    - python",
                "    - pytest",
            ]
        ),
        encoding="utf-8",
    )

    run_dir = run_pipeline(
        prompt=prompt,
        project_name=project_name,
        stack="web_fullstack",
        config_path=config_path,
        dry_run=True,
    )

    assert (run_dir / "prd" / "prd.json").exists()
    assert (run_dir / "prd" / "prd.md").exists()
    assert (run_dir / "specs" / "core" / "orchestrator.json").exists()
    assert (run_dir / "backlog" / "backlog.json").exists()

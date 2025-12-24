from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.graph_export import export_plan_dot
from agent_factory.orchestrator.publisher import git_tag, make_zip, write_changelog
from agent_factory.orchestrator.github_publisher import GitHubPublisher
from agent_factory.orchestrator.github_publisher_docker import GitHubPublisherDocker


class ReleaseAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore, dry_run: bool) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.dry_run = dry_run
        self.repo_root = Path(".").resolve()

    def prepare_report(self) -> None:
        artifacts: List[str] = [
            "plan.json",
            "state.json",
            "env_snapshot.json",
            "reports/qa_report.json",
            "reports/QUICKSTART.md",
            "adr/ADR-0001-architecture.md",
            "reports/plan.dot",
            "reports/artifact_repo.zip",
            "reports/CHANGELOG.md",
        ]
        state = self.state_store.read_state(self.run_dir)
        config = state.get("config", {})
        results = state.get("test_results", [])
        reports_dir = self.run_dir / "reports"
        plan = json.loads((self.run_dir / "plan.json").read_text(encoding="utf-8"))
        export_plan_dot(plan, reports_dir / "plan.dot")
        make_zip(self.repo_root, reports_dir / "artifact_repo.zip")
        write_changelog(reports_dir, state)
        git_tag(self.repo_root, tag=f"v0.1.{state.get('fix_attempts',0)}")
        self._publish_to_github(config, reports_dir, state)

        overall_status = self._compute_status(results)
        report_md = self._build_markdown(artifacts, overall_status)
        report_json = self._build_json(artifacts, overall_status, results)
        report_path = self.state_store.save_report(self.run_dir, "final_report.md", report_md)
        json_path = self.state_store.save_report(
            self.run_dir,
            "final_report.json",
            json.dumps(report_json, indent=2),
        )
        self.state_store.append_log(
            self.run_dir,
            f"Final report saved to {report_path} and {json_path}",
        )
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "completed"
        self.state_store.save_state(self.run_dir, state)

    def _build_markdown(self, artifacts: List[str], status: str) -> str:
        lines = [
            "# Final Report",
            "",
            f"**Stack:** {self.stack}",
            f"**Mode:** {'dry-run' if self.dry_run else 'execute'}",
            f"**Status:** {status}",
            "",
            "## Artifacts",
        ]
        lines.extend([f"- {item}" for item in artifacts])
        return "\n".join(lines) + "\n"

    def _build_json(self, artifacts: List[str], status: str, results: List[Dict]) -> Dict:
        return {
            "stack": self.stack,
            "mode": "dry-run" if self.dry_run else "execute",
            "status": status,
            "tests": results,
            "artifacts": artifacts,
        }

    def _compute_status(self, results: List[Dict]) -> str:
        if self.dry_run:
            return "dry-run"
        if not results:
            return "unknown"
        if all(result.get("status") in {"pass", "skipped"} for result in results):
            return "success"
        return "failed"

    def _publish_to_github(self, config: Dict, reports_dir: Path, state: Dict) -> None:
        pub_cfg = (config.get("publisher") or {}).get("github") or {}
        if not pub_cfg.get("enabled"):
            return
        try:
            tooling_cfg = (config.get("tooling") or {}).get("docker") or {}
            use_docker = bool(tooling_cfg.get("enabled"))
            project = self.state_store.read_state(self.run_dir)["project"]
            if use_docker:
                publisher = GitHubPublisherDocker(
                    repo_root=self.repo_root,
                    image=tooling_cfg.get("image", "agent-factory-runner:latest"),
                )
                publisher.ensure_repo(pub_cfg["owner"], project, pub_cfg.get("repo_visibility", "private"))
                publisher.push(pub_cfg["owner"], project, branch=pub_cfg.get("default_branch", "main"))
                release_cfg = pub_cfg.get("release", {})
                if release_cfg.get("enabled"):
                    tag = f"v0.1.{state.get('fix_attempts',0)}"
                    publisher.release(
                        tag=tag,
                        title=f"{project} {tag}",
                        notes_file=(reports_dir / "CHANGELOG.md"),
                        asset=(reports_dir / "artifact_repo.zip"),
                    )
            else:
                publisher = GitHubPublisher(
                    repo_root=self.repo_root,
                    owner=pub_cfg["owner"],
                    repo=project,
                    visibility=pub_cfg.get("repo_visibility", "private"),
                    default_branch=pub_cfg.get("default_branch", "main"),
                    remote_name=pub_cfg.get("remote_name", "origin"),
                )
                publisher.ensure_auth()
                publisher.ensure_repo()
                publisher.ensure_git_initialized()
                publisher.ensure_remote()
                publisher.commit_all(message=f"Agent Factory run: {project}")
                publisher.push()

                release_cfg = pub_cfg.get("release", {})
                if release_cfg.get("enabled"):
                    tag = f"v0.1.{state.get('fix_attempts',0)}"
                    publisher.release(
                        tag=tag,
                        title=f"{project} {tag}",
                        notes_file=(reports_dir / "CHANGELOG.md"),
                        asset=(reports_dir / "artifact_repo.zip"),
                    )
        except Exception as e:
            self.state_store.append_log(self.run_dir, f"GitHub publish skipped: {e}", kind="warn")

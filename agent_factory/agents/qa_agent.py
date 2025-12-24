from __future__ import annotations

import json
import os
import shlex
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Sequence

import yaml  # type: ignore

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.tools.test_runner import TestRunner
from agent_factory.tools.docker_tool import DockerTool
from agent_factory.tools.shell_tool import AllowedCommandRunner


class QAAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore, dry_run: bool) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.dry_run = dry_run
        self.runner = TestRunner()
        self.stack_root = Path(self.state_store.read_state(run_dir)["config"].get("stack_root", "stacks"))
        self.stack_rules = self._load_stack_rules()
        allowlist = self.stack_rules.get("allowlist", [])
        if allowlist:
            self.runner.runner.allowlist = list(allowlist)
        self.repo_root = Path(".").resolve()

    def run_suite(self) -> None:
        checks = self._load_checks()
        results: List[Dict] = []
        run_reports = str((self.state_store.base_path / self.state_store.read_state(self.run_dir)["project"] / "reports").resolve())
        cfg = self.state_store.read_state(self.run_dir).get("config", {})
        docker_cfg = (cfg.get("tooling") or {}).get("docker") or {}
        use_docker = bool(docker_cfg.get("enabled"))
        runner_image = docker_cfg.get("image", "agent-factory/runner-base:0.1.0")
        stack_runner = (self.stack_rules.get("docker_runner") or {}).get("image")
        if stack_runner:
            runner_image = stack_runner
        docker_runner = DockerTool(
            runner=AllowedCommandRunner(allowlist=self.runner.runner.allowlist + ["docker"]),
            image=runner_image,
        )

        for check in checks:
            cmd = self._prepare_command(check, run_reports)
            if self.dry_run:
                results.append(
                    {
                        "name": check.get("name"),
                        "status": "skipped",
                        "command": " ".join(cmd) if cmd else "",
                        "attempts": 0,
                        "details": "Dry-run: command not executed",
                    }
                )
                continue
            result = self._run_check(check, cmd, use_docker=use_docker, docker_runner=docker_runner)
            results.append(result)

        report = {"stack": self.stack, "results": results, "dry_run": self.dry_run}
        report_path = self.run_dir / "reports" / "qa_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, f"QA report written to {report_path}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "docs"
        state["test_results"] = results
        state["gates"] = results
        self.state_store.save_state(self.run_dir, state)

    def _prepare_command(self, check: Dict, run_reports: str) -> List[str]:
        raw_cmd: Sequence[str] | str | None = check.get("cmd") or check.get("command")
        if not raw_cmd:
            return []
        if isinstance(raw_cmd, str):
            cmd_list = shlex.split(raw_cmd)
        else:
            cmd_list = list(raw_cmd)
        return [c.replace("{RUN_REPORTS_DIR}", run_reports) for c in cmd_list]

    def _load_checks(self) -> List[Dict]:
        checks_path = self.stack_root / self.stack / "checks.yaml"
        if not checks_path.exists():
            return []
        data = yaml.safe_load(checks_path.read_text(encoding="utf-8")) or {}
        if "gates" in data:
            return data.get("gates", {}).get("commands", []) or []
        return data.get("checks", [])

    def _load_stack_rules(self) -> Dict:
        rules_path = self.stack_root / self.stack / "rules.yaml"
        if not rules_path.exists():
            return {}
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        return data

    def _run_check(self, check: Dict, command: List[str], use_docker: bool, docker_runner: DockerTool) -> Dict:
        max_attempts = int(check.get("max_attempts", 6))
        attempts = 0
        if not command:
            return {
                "name": check.get("name"),
                "status": "skipped",
                "command": "",
                "attempts": 0,
                "details": "No command specified",
            }
        self.runner.runner.extend_allowlist([command[0]])
        if not use_docker and shutil.which(command[0]) is None:
            return {
                "name": check.get("name"),
                "status": "skipped",
                "command": " ".join(command),
                "attempts": 0,
                "details": f"Command {command[0]} not available",
            }

        cwd = check.get("cwd")
        while attempts < max_attempts:
            attempts += 1
            if use_docker:
                env = {
                    "GH_TOKEN": os.getenv("GH_TOKEN", ""),
                    "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                    "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
                    "OPENAI_MODEL": os.getenv("OPENAI_MODEL", ""),
                }
                code, out, err = docker_runner.run(
                    command,
                    mount_dir=str(self.repo_root.resolve()),
                    env=env,
                )
                result = subprocess.CompletedProcess(command, code, out, err)
            else:
                result = self.runner.runner.run(command, cwd=str(Path(cwd)) if cwd else None)
            if result.returncode == 0:
                return {
                    "name": check.get("name"),
                    "status": "pass",
                    "command": " ".join(command),
                    "attempts": attempts,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            self.state_store.append_fixer_log(
                self.run_dir,
                {
                    "check": check.get("name"),
                    "command": " ".join(command),
                    "attempt": attempts,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        incident_path = self.state_store.create_incident(
            self.run_dir,
            title=f"Check failed: {check.get('name')}",
            body=f"Command `{' '.join(command)}` failed after {max_attempts} attempts.",
        )
        return {
            "name": check.get("name"),
            "status": "failed",
            "command": " ".join(command),
            "attempts": attempts,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "incident": str(incident_path),
        }

    def _exec_command(self, command: str) -> subprocess.CompletedProcess[str]:
        runner = self.runner.runner
        runner.extend_allowlist([shlex.split(command)[0]])
        return runner.run_string(command, cwd=str(Path.cwd()))

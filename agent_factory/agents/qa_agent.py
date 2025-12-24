from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List

import yaml  # type: ignore

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.tools.test_runner import TestRunner


class QAAgent:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore, dry_run: bool) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.dry_run = dry_run
        self.runner = TestRunner()
        self.stack_root = Path(self.state_store.read_state(run_dir)["config"].get("stack_root", "stacks"))

    def run_suite(self) -> None:
        checks = self._load_checks()
        results = []
        for check in checks:
            if self.dry_run:
                results.append(
                    {
                        "name": check["name"],
                        "status": "skipped",
                        "command": check["command"],
                        "attempts": 0,
                        "details": "Dry-run: command not executed",
                    }
                )
                continue
            result = self._run_check(check)
            results.append(result)

        report = {"stack": self.stack, "results": results, "dry_run": self.dry_run}
        report_path = self.run_dir / "reports" / "qa_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, f"QA report written to {report_path}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "docs"
        state["test_results"] = results
        self.state_store.save_state(self.run_dir, state)

    def _load_checks(self) -> List[Dict]:
        checks_path = self.stack_root / self.stack / "checks.yaml"
        if not checks_path.exists():
            return []
        data = yaml.safe_load(checks_path.read_text(encoding="utf-8")) or {}
        return data.get("checks", [])

    def _run_check(self, check: Dict) -> Dict:
        command = check["command"]
        max_attempts = int(check.get("max_attempts", 6))
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            result = self._exec_command(command)
            if result.returncode == 0:
                return {
                    "name": check["name"],
                    "status": "pass",
                    "command": command,
                    "attempts": attempts,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            self.state_store.append_fixer_log(
                self.run_dir,
                {
                    "check": check["name"],
                    "command": command,
                    "attempt": attempts,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        incident_path = self.state_store.create_incident(
            self.run_dir,
            title=f"Check failed: {check['name']}",
            body=f"Command `{command}` failed after {max_attempts} attempts.",
        )
        return {
            "name": check["name"],
            "status": "failed",
            "command": command,
            "attempts": attempts,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "incident": str(incident_path),
        }

    def _exec_command(self, command: str) -> subprocess.CompletedProcess[str]:
        # Allow the first token of the command if not already in the allowlist.
        runner = self.runner.runner
        runner.extend_allowlist([shlex.split(command)[0]])
        return runner.run_string(command, cwd=str(Path.cwd()))

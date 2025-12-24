from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import platform
import sys

from agent_factory.orchestrator.task_graph import Task


class StateStore:
    """Manage state and artifacts for a run."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def init_run(self, project_name: str, prompt: str, stack: str, config: Dict[str, Any]) -> Path:
        run_dir = self.base_path / project_name
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "adr").mkdir(parents=True, exist_ok=True)
        (run_dir / "incidents").mkdir(parents=True, exist_ok=True)
        (run_dir / "inputs").mkdir(parents=True, exist_ok=True)

        input_path = run_dir / "inputs" / "input_prompt.md"
        input_path.write_text(prompt.strip() + "\n", encoding="utf-8")

        state = {
            "project": project_name,
            "stack": stack,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "current_gate": "ingest",
            "tasks": [],
            "test_results": [],
            "decisions": [],
            "config": config,
        }
        self._write_json(run_dir / "state.json", state)
        self._write_env_snapshot(run_dir, stack, config)
        return run_dir

    def save_plan(self, run_dir: Path, tasks: List[Task]) -> Path:
        payload = {"tasks": [asdict(task) for task in tasks]}
        path = run_dir / "plan.json"
        self._write_json(path, payload)
        return path

    def append_log(self, run_dir: Path, message: str, kind: str = "info") -> None:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "message": message,
        }
        log_path = run_dir / "logs" / "events.jsonl"
        log_path.write_text(
            (log_path.read_text(encoding="utf-8") if log_path.exists() else "")
            + json.dumps(log_entry)
            + "\n",
            encoding="utf-8",
        )

    def save_state(self, run_dir: Path, state: Dict[str, Any]) -> None:
        self._write_json(run_dir / "state.json", state)

    def read_state(self, run_dir: Path) -> Dict[str, Any]:
        state_path = run_dir / "state.json"
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(state_path)

    def add_decision(self, run_dir: Path, title: str, context: str, decision: str, slug: str = "architecture") -> Path:
        adr_index = len(list((run_dir / "adr").glob("ADR-*.md"))) + 1
        path = run_dir / "adr" / f"ADR-{adr_index:04d}-{slug}.md"
        content = "\n".join(
            [
                f"# {title}",
                "",
                f"**Date:** {datetime.now(timezone.utc).date().isoformat()}",
                f"**Context:** {context}",
                f"**Decision:** {decision}",
                "**Consequences:**",
                "- Captured in follow-up tasks.",
            ]
        )
        path.write_text(content + "\n", encoding="utf-8")
        return path

    def save_report(self, run_dir: Path, name: str, content: str) -> Path:
        path = run_dir / "reports" / name
        path.write_text(content, encoding="utf-8")
        return path

    def append_fixer_log(self, run_dir: Path, payload: Dict[str, Any]) -> None:
        fixer_log = run_dir / "logs" / "fixer.jsonl"
        fixer_log.write_text(
            (fixer_log.read_text(encoding="utf-8") if fixer_log.exists() else "")
            + json.dumps(payload)
            + "\n",
            encoding="utf-8",
        )

    def create_incident(self, run_dir: Path, title: str, body: str) -> Path:
        incidents = list((run_dir / "incidents").glob("INC-*.md"))
        next_id = len(incidents) + 1
        path = run_dir / "incidents" / f"INC-{next_id:04d}.md"
        content = "\n".join(
            [
                f"# {title}",
                "",
                body,
            ]
        )
        path.write_text(content + "\n", encoding="utf-8")
        return path

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_env_snapshot(self, run_dir: Path, stack: str, config: Dict[str, Any]) -> None:
        snapshot = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "stack": stack,
            "config": config,
        }
        self._write_json(run_dir / "env_snapshot.json", snapshot)

    def append_jsonl(self, run_dir: Path, rel_path: str, payload: Dict[str, Any]) -> None:
        target = run_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(existing + json.dumps(payload) + "\n", encoding="utf-8")

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

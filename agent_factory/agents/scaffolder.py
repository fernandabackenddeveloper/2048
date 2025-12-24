from __future__ import annotations

import json
from pathlib import Path

from agent_factory.orchestrator.state_store import StateStore
from agent_factory.tools.fs_tool import ensure_dir
from agent_factory.tools.shell_tool import AllowedCommandRunner


class Scaffolder:
    def __init__(self, run_dir: Path, stack: str, state_store: StateStore) -> None:
        self.run_dir = run_dir
        self.stack = stack
        self.state_store = state_store
        self.runner = AllowedCommandRunner()

    def scaffold(self) -> None:
        stack_rules = self._load_stack_rules()
        scaffold_dir = self.run_dir / "scaffold"
        ensure_dir(scaffold_dir)
        summary = {
            "stack": self.stack,
            "templates": stack_rules.get("templates", []),
            "commands": stack_rules.get("commands", []),
        }
        (scaffold_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        self.state_store.append_log(self.run_dir, f"Scaffold created for stack {self.stack}")
        state = self.state_store.read_state(self.run_dir)
        state["current_gate"] = "qa"
        self.state_store.save_state(self.run_dir, state)

    def _load_stack_rules(self) -> dict:
        rules_path = Path("agent_factory") / "stacks" / self.stack / "rules.yaml"
        if not rules_path.exists():
            return {"templates": [], "commands": []}
        import yaml  # type: ignore

        return yaml.safe_load(rules_path.read_text(encoding="utf-8"))

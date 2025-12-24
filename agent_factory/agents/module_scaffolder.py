from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from agent_factory.orchestrator.state_store import StateStore


@dataclass
class ModuleScaffolder:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(__file__).resolve().parents[2]

    def run(self, module: Dict[str, Any], out_dir: Path) -> Path:
        repo_name = module["repo"]
        root = out_dir / repo_name
        root.mkdir(parents=True, exist_ok=True)

        (root / "src").mkdir(exist_ok=True)
        (root / "tests").mkdir(exist_ok=True)
        (root / "README.md").write_text(
            f"# {repo_name}\n\nDomains: {', '.join(module['domains'])}\n",
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            "[project]\nname = \"" + repo_name + "\"\nversion = \"0.1.0\"\n",
            encoding="utf-8",
        )
        (root / "tests" / "test_smoke.py").write_text(
            "def test_smoke():\n    assert True\n",
            encoding="utf-8",
        )

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/multirepo.jsonl",
            {"ts": self.state_store.utc_now(), "event": "module_scaffolded", "repo": repo_name},
        )
        return root

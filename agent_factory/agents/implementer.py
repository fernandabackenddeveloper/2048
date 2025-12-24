from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from agent_factory.orchestrator.sandbox import create_sandbox
from agent_factory.orchestrator.patching import PatchError, apply_patch, rollback, snapshot
from agent_factory.orchestrator.state_store import StateStore
from agent_factory.orchestrator.task_graph import iter_plan_tasks
from agent_factory.orchestrator.llm.adapter import OpenAICompatibleAdapter
from agent_factory.orchestrator.changes import diff_hashes, snapshot_hashes
from orchestrator.vault.vault import Vault
from orchestrator.vault.retrieval import retrieve


def run_pytest(path: Path) -> bool:
    result = subprocess.run(["pytest", "-q"], cwd=str(path))
    return result.returncode == 0


@dataclass
class ImplementerAgent:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(".").resolve()

    def run(self, task: Optional[Dict[str, Any]] = None) -> None:
        plan_path = self.run_dir / "plan.json"
        if not plan_path.exists():
            raise FileNotFoundError(plan_path)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        api_key = os.getenv("OPENAI_API_KEY")
        adapter: Optional[OpenAICompatibleAdapter] = None
        if api_key:
            adapter = OpenAICompatibleAdapter(
                api_key=api_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )

        tasks_iter = [task] if task else [t for _, _, t in iter_plan_tasks(plan)]
        last_result: Optional[Dict[str, Any]] = None

        for t in tasks_iter:
            task_id = t.get("id")
            sandbox = create_sandbox(self.repo_root, self.state_store.read_state(self.run_dir)["project"], task_id)
            before = snapshot_hashes(sandbox)
            vault = Vault(self.repo_root / "knowledge")
            hits = retrieve(vault, query=t.get("description", ""), tags=None, top_k=6)
            context_pack = [{"id": h.id, "title": h.title, "path": h.path, "snippet": h.snippet} for h in hits]

            if adapter is None:
                t["status"] = "skipped"
                self._log(task_id, sandbox, "skipped", "No LLM configured")
                last_result = {"task": task_id, "status": "skipped", "sandbox": str(sandbox), "reason": "No LLM configured"}
                continue

            ctx = json.dumps({"task": t, "vault_context": context_pack}, indent=2)

            # 1) Generate tests
            tests_prompt = (
                self.repo_root / "orchestrator" / "llm" / "prompts" / "implementer.tests.system.txt"
            ).read_text(encoding="utf-8")
            diff_tests = adapter.generate_text(tests_prompt, ctx)

            snap_tests = snapshot(sandbox)
            try:
                apply_patch(sandbox, diff_tests)
                run_pytest(sandbox)
            except Exception:
                rollback(snap_tests, sandbox)
                t["status"] = "failed"
                self._log(task_id, sandbox, "failed", "tests")
                last_result = {"task": task_id, "status": "failed", "sandbox": str(sandbox), "stage": "tests"}
                continue

            # 2) Generate code
            code_prompt = (
                self.repo_root / "orchestrator" / "llm" / "prompts" / "implementer.code.system.txt"
            ).read_text(encoding="utf-8")
            diff_code = adapter.generate_text(code_prompt, ctx)

            art_dir = sandbox / "runs" / self.state_store.read_state(self.run_dir)["project"] / "artifacts"
            art_dir.mkdir(parents=True, exist_ok=True)
            (art_dir / f"{task_id}_tests.diff").write_text(diff_tests, encoding="utf-8")
            (art_dir / f"{task_id}_code.diff").write_text(diff_code, encoding="utf-8")

            snap_code = snapshot(sandbox)
            try:
                apply_patch(sandbox, diff_code)
                if not run_pytest(sandbox):
                    raise RuntimeError("Tests still failing after code patch")
            except Exception:
                rollback(snap_code, sandbox)
                t["status"] = "failed"
                self._log(task_id, sandbox, "failed", "code")
                last_result = {"task": task_id, "status": "failed", "sandbox": str(sandbox), "stage": "code"}
                continue

            after = snapshot_hashes(sandbox)
            changes = diff_hashes(before, after)

            manifest_path = sandbox / "runs" / self.state_store.read_state(self.run_dir)["project"] / "artifacts"
            manifest_path.mkdir(parents=True, exist_ok=True)
            (manifest_path / f"changes_{task_id}.json").write_text(
                json.dumps(changes, indent=2),
                encoding="utf-8",
            )

            t["status"] = "ready_to_merge"
            self._log(task_id, sandbox, "ready_to_merge", "ready_to_merge")
            last_result = {
                "task": task_id,
                "status": "ready_to_merge",
                "sandbox": str(sandbox),
                "changes": changes,
                "patches": {
                    "tests": str(art_dir / f"{task_id}_tests.diff"),
                    "code": str(art_dir / f"{task_id}_code.diff"),
                },
            }

        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        state = self.state_store.read_state(self.run_dir)
        state["tasks"] = plan.get("milestones", [])
        self.state_store.save_state(self.run_dir, state)
        return last_result or {"task": task.get("id") if task else None, "status": "skipped"}

    def _log(self, task_id: str, sandbox: Path, status: str, detail: str) -> None:
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/implementer.jsonl",
            {
                "ts": self.state_store.utc_now(),
                "event": "implementer_invoked",
                "task": task_id,
                "sandbox": str(sandbox),
                "status": status,
                "detail": detail,
            },
        )

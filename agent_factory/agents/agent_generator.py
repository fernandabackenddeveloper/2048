from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.generator.naming import slug, stable_id
from orchestrator.generator.registry import load_registry, save_registry
from orchestrator.generator.bundle import merge_generated_capabilities


@dataclass
class AgentGenerator:
    run_dir: Path
    stack: str
    state_store: StateStore
    config: Dict[str, Any]
    repo_root: Path = Path(__file__).resolve().parents[2]

    def _ensure_dirs(self) -> Dict[str, Path]:
        repo = self.repo_root
        out_agents_dir = repo / "agent_factory" / "agents" / "generated"
        prompts_dir = repo / "orchestrator" / "llm" / "prompts" / "generated"
        rubrics_dir = repo / "docs" / "generated_rubrics"
        policies_dir = repo / "stacks" / self.stack / "generated_policies"
        tests_dir = repo / "tests" / "generated"
        for p in [out_agents_dir, prompts_dir, rubrics_dir, policies_dir, tests_dir]:
            p.mkdir(parents=True, exist_ok=True)
        (out_agents_dir / "__init__.py").write_text("# auto-generated\n", encoding="utf-8")
        return {
            "agents": out_agents_dir,
            "prompts": prompts_dir,
            "rubrics": rubrics_dir,
            "policies": policies_dir,
            "tests": tests_dir,
        }

    def run(self, prd: Dict[str, Any], specs: List[Dict[str, Any]], caps: Dict[str, Any] | None = None) -> Dict[str, Any]:
        repo = self.repo_root
        dirs = self._ensure_dirs()
        reg = load_registry(repo)

        docker_image = (self.config.get("tooling", {}).get("docker", {}) or {}).get(
            "image", "agent-factory/runner-web_fullstack:0.1.0"
        )

        created: List[str] = []
        for sp in specs:
            domain = sp.get("domain", "domain")
            module = sp.get("module", "module")
            dom_slug = slug(domain)
            mod_slug = slug(module)
            agent_id = stable_id(domain, module)
            class_name = "".join([w.capitalize() for w in (dom_slug + "_" + mod_slug).split("_")]) + "Agent"
            agent_py_name = f"{dom_slug}_{mod_slug}_agent"

            prompt_dir = dirs["prompts"] / dom_slug / mod_slug
            prompt_dir.mkdir(parents=True, exist_ok=True)
            system_prompt = self._build_system_prompt(sp, agent_id, domain, module)
            (prompt_dir / "system.txt").write_text(system_prompt, encoding="utf-8")

            rubric_dir = dirs["rubrics"] / dom_slug
            rubric_dir.mkdir(parents=True, exist_ok=True)
            (rubric_dir / f"{mod_slug}.md").write_text(self._build_rubric(domain, module), encoding="utf-8")

            (dirs["policies"] / f"{dom_slug}_{mod_slug}.yaml").write_text(
                self._build_policy(agent_id, docker_image), encoding="utf-8"
            )

            agent_code = self._build_agent_code(class_name, agent_id, domain, module, dom_slug, mod_slug, sp)
            (dirs["agents"] / f"{agent_py_name}.py").write_text(agent_code, encoding="utf-8")

            test_code = f"def test_generated_agent_import():\n    from agent_factory.agents.generated.{agent_py_name} import {class_name}\n    assert {class_name} is not None\n"
            (dirs["tests"] / f"test_{dom_slug}_{mod_slug}_agent.py").write_text(test_code, encoding="utf-8")

            reg.setdefault("agents", {})
            reg["agents"][agent_id] = {
                "class": class_name,
                "module_path": f"agent_factory.agents.generated.{agent_py_name}",
                "domain": domain,
                "module": module,
                "tags": [dom_slug, mod_slug],
                "docker_image": docker_image,
                "boundaries": [f"{domain}/", f"{module}/", "docs/", "tests/"],
                "rubric": str((rubric_dir / f"{mod_slug}.md").relative_to(repo)),
                "prompt": str((prompt_dir / "system.txt").relative_to(repo)),
                "policy": str((dirs["policies"] / f"{dom_slug}_{mod_slug}.yaml").relative_to(repo)),
            }
            created.append(agent_id)

        save_registry(repo, reg)
        merge_generated_capabilities(repo, reg)
        self.state_store.append_jsonl(
            self.run_dir,
            "logs/agent_generator.jsonl",
            {"ts": self.state_store.utc_now(), "event": "agents_generated", "count": len(created)},
        )
        return {"generated": created, "registry": "orchestrator/generator/generated_registry.json"}

    def _build_system_prompt(self, sp: Dict[str, Any], agent_name: str, domain: str, module: str) -> str:
        boundaries = "\n".join([f"- {b}" for b in [f"{domain}/", f"{module}/", "docs/", "tests/"]])
        acceptance = "\n".join([f"- {t}" for t in (sp.get("acceptance_tests") or [])])
        overview = sp.get("overview", "")
        return (
            f"You are PROJECT-FORGE Specialist Agent: {domain}.{module} ({agent_name})\n\n"
            "NON-NEGOTIABLE RULES:\n"
            "- Output MUST be a unified diff patch OR a JSON issue report.\n"
            "- Do NOT change files outside boundaries.\n"
            "- Do NOT add unrequested features.\n"
            "- Prefer minimal changes that satisfy Acceptance Tests.\n\n"
            "BOUNDARIES (allowed paths):\n"
            f"{boundaries}\n\n"
            f"SPEC SUMMARY:\n{overview}\n\n"
            "ACCEPTANCE TESTS (must become real tests):\n"
            f"{acceptance}\n\n"
            "OUTPUT FORMAT:\n"
            "Option A) Unified diff starting with lines like:\n--- a/path\n+++ b/path\n\n"
            'Option B) JSON issue report only:\n{{"status":"blocked","reason":"...","missing":["..."],"suggested_tasks":["..."]}}\n\n'
            "CONTEXT:\nYou will be given: task + spec + vault_context snippets.\n"
        )

    def _build_rubric(self, domain: str, module: str) -> str:
        return (
            f"# Rubric — {domain}.{module}\n\n"
            "## Definition of Done\n"
            "- Changes restricted to allowed boundaries.\n"
            "- Acceptance tests implemented as automated tests.\n"
            "- Gates: pytest passes in docker runner.\n"
            "- No TODO/print/debug left in release path.\n\n"
            "## Anti-scope rules\n"
            "- No unrelated modules.\n"
            "- No UI/feature creep beyond spec.\n"
            "- Prefer simplest implementation.\n\n"
            "## Common pitfalls\n"
            "- Breaking API without bumping version (if multi-repo mode).\n"
            "- Adding new dependencies without pinning.\n"
        )

    def _build_policy(self, agent_name: str, docker_image: str) -> str:
        return (
            f"agent: {agent_name}\n"
            f"docker_image: {docker_image}\n"
            "allowlist:\n"
            "  - python\n"
            "  - pytest\n"
            "  - rg\n"
            "  - git\n"
            "notes:\n"
            "  - \"This agent must run in sandbox.\"\n"
            "  - \"No network tools except allowed (gh only in release).\"\n"
        )

    def _build_agent_code(
        self, class_name: str, agent_name: str, domain: str, module: str, dom_slug: str, mod_slug: str, sp: Dict[str, Any]
    ) -> str:
        spec_json = json.dumps(sp, ensure_ascii=False)
        template = (
            "from __future__ import annotations\n\n"
            "import json\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from pathlib import Path\n"
            "from typing import Any, Dict\n\n"
            "from orchestrator.vault.vault import Vault\n"
            "from orchestrator.vault.retrieval import retrieve\n"
            "from orchestrator.llm.adapter import OpenAICompatibleAdapter\n\n"
            "@dataclass\n"
            "class {class_name}:\n"
            "    run_dir: Path\n"
            "    stack: str\n"
            "    state_store: Any\n"
            "    repo_root: Path = Path(__file__).resolve().parents[3]\n\n"
            "    def run(self, task: Dict[str, Any]) -> Dict[str, Any]:\n"
            "        vault = Vault(self.repo_root / \"knowledge\")\n"
            "        hits = retrieve(vault, query=task.get(\"description\", \"\"), top_k=6)\n"
            "        context_pack = [{{\"id\": h.id, \"title\": h.title, \"path\": h.path, \"snippet\": h.snippet}} for h in hits]\n"
            "        sys_path = self.repo_root / \"orchestrator\" / \"llm\" / \"prompts\" / \"generated\" / \"{dom_slug}\" / \"{mod_slug}\" / \"system.txt\"\n"
            "        system = sys_path.read_text(encoding=\"utf-8\")\n"
            "        payload = {{\"task\": task, \"spec\": {spec_json}, \"vault_context\": context_pack}}\n"
            "        if not os.getenv(\"OPENAI_API_KEY\"):\n"
            "            return {{\n"
            "                \"status\": \"needs_llm\",\n"
            "                \"agent\": \"{agent_name}\",\n"
            "                \"note\": \"OPENAI_API_KEY missing; cannot generate code diffs.\",\n"
            "                \"context_used\": context_pack,\n"
            "            }}\n"
            "        adapter = OpenAICompatibleAdapter(\n"
            "            api_key=os.getenv(\"OPENAI_API_KEY\"),\n"
            "            base_url=os.getenv(\"OPENAI_BASE_URL\", \"https://api.openai.com/v1\"),\n"
            "            model=os.getenv(\"OPENAI_MODEL\", \"gpt-4o-mini\"),\n"
            "        )\n"
            "        result = adapter.generate_text(system, json.dumps(payload, ensure_ascii=False))\n"
            "        return {{\"status\": \"proposed\", \"agent\": \"{agent_name}\", \"output\": result, \"context_used\": context_pack}}\n"
        )
        return template.format(
            class_name=class_name,
            dom_slug=dom_slug,
            mod_slug=mod_slug,
            spec_json=spec_json,
            agent_name=agent_name,
        )

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json

from agent_factory.orchestrator.state_store import StateStore
from orchestrator.integrator.lock import write_lock


@dataclass
class IntegratorScaffolder:
    run_dir: Path
    stack: str
    state_store: StateStore
    repo_root: Path = Path(__file__).resolve().parents[2]

    def run(self, multirepo: Dict[str, Any], out_dir: Path) -> Path:
        repo = multirepo["integrator_repo"]
        root = out_dir / repo
        root.mkdir(parents=True, exist_ok=True)

        (root / "modules").mkdir(exist_ok=True)
        (root / "README.md").write_text(
            f"# {repo}\n\nThis repo integrates module repos.\n",
            encoding="utf-8",
        )

        modules = []
        for mod in multirepo.get("modules", []):
            modules.append(
                {
                    "name": mod.get("name"),
                    "repo": mod.get("repo"),
                    "version": "0.1.0",
                    "ref": "refs/tags/v0.1.0",
                }
            )
        lock = {
            "owner": multirepo.get("owner", ""),
            "integrator": repo,
            "modules": modules,
        }
        write_lock(root / "module.lock.json", lock)

        (root / "docker-compose.yml").write_text(
            "services:\n"
            "  app:\n"
            "    image: agent-factory/runner-web_fullstack:0.1.0\n"
            "    volumes:\n"
            "      - ./:/work\n"
            "    working_dir: /work\n"
            "    command: [\"bash\",\"-lc\",\"pytest -q || true\"]\n",
            encoding="utf-8",
        )

        scripts_dir = root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "fetch_modules.py").write_text(
            "import json, subprocess\n"
            "from pathlib import Path\n"
            "root = Path(__file__).resolve().parents[1]\n"
            "lock = json.loads((root / \"module.lock.json\").read_text(encoding=\"utf-8\"))\n"
            "mods_dir = root / \"modules\"\n"
            "mods_dir.mkdir(exist_ok=True)\n"
            "owner = lock.get(\"owner\")\n"
            "for m in lock.get(\"modules\", []):\n"
            "    repo = m[\"repo\"]\n"
            "    ref = m.get(\"ref\", \"main\")\n"
            "    name = repo.replace(\"/\", \"__\")\n"
            "    dest = mods_dir / name\n"
            "    if dest.exists():\n"
            "        subprocess.run([\"git\", \"-C\", str(dest), \"fetch\", \"--tags\"], check=False)\n"
            "    else:\n"
            "        url = f\"https://github.com/{owner}/{repo}.git\"\n"
            "        subprocess.run([\"git\", \"clone\", url, str(dest)], check=False)\n"
            "    subprocess.run([\"git\", \"-C\", str(dest), \"checkout\", ref], check=False)\n"
            "print(\"Modules fetched.\")\n",
            encoding="utf-8",
        )

        ci_dir = root / "ci"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "github_actions_integrator.yml").write_text(
            "name: Integrator CI\n"
            "on:\n"
            "  push:\n"
            "    branches: [ \"main\" ]\n"
            "  workflow_dispatch: {}\n"
            "jobs:\n"
            "  test:\n"
            "    strategy:\n"
            "      matrix:\n"
            "        os: [ubuntu-latest, windows-latest]\n"
            "    runs-on: ${{ matrix.os }}\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: \"3.12\"\n"
            "      - name: Fetch modules\n"
            "        run: python scripts/fetch_modules.py\n"
            "      - name: Install deps\n"
            "        run: pip install -U pytest\n"
            "      - name: Run tests\n"
            "        run: pytest -q\n",
            encoding="utf-8",
        )

        self.state_store.append_jsonl(
            self.run_dir,
            "logs/multirepo.jsonl",
            {"ts": self.state_store.utc_now(), "event": "integrator_scaffolded", "repo": repo},
        )
        return root

# Agent Factory Quickstart

The Agent Factory orchestrator is a Python CLI that ingests a project prompt and generates a runnable run directory with a plan, ADR, scaffold summary, QA report, quickstart, and final report.

## Prerequisites
- Python 3.11+
- Optional: `pyyaml` (installed via the provided `pyproject.toml`)

Install dev dependencies (for running tests):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Running the pipeline
```bash
python -m orchestrator.main \
  --prompt "Build a modular orchestrator for automated projects" \
  --project demo-project \
  --stack web_fullstack \
  --dry-run
```

### Real run (executes stack checks)
```bash
python -m orchestrator.main \
  --prompt "Build a modular orchestrator for automated projects" \
  --project demo-project \
  --stack web_fullstack
```

Artifacts appear under `runs/<project>`:
- `inputs/input_prompt.md` – captured prompt
- `plan.json` – milestones/tasks
- `state.json` – pipeline gate state
- `env_snapshot.json` – environment and config snapshot
- `adr/ADR-0001-architecture.md` – stack/architecture decision
- `scaffold/summary.json` – stack commands/templates summary
- `reports/qa_report.json` – placeholder QA output
- `reports/QUICKSTART.md` – how to rerun
- `reports/final_report.md` – delivery summary
- `reports/final_report.json` – delivery summary (JSON)

## Running tests
```bash
pytest
```

## Extending
- Add stack plugins under `stacks/<stack_name>/` with `rules.yaml` and `checks.yaml`.
- Extend agents in `agent_factory/agents/` to add linting, templating, or CI hooks.

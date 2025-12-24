# Agent Factory Playbook

This document captures the operational blueprint for a fully automated, multi-agent system that ingests a project prompt/plan and delivers a complete repository (or zip) with code, build assets, tests, documentation, and a final report. The orchestrator is written in Python and drives OpenAI-compatible models through a controlled tool layer.

## Objectives (non-negotiable)
- **Input:** User prompt or plan.
- **Output:** GitHub-ready repository (or zip) with modular code, executable build or build instructions, automated tests executed, final report (done/missing/risks/next steps), documentation (README, architecture docs).
- **Constraints:** End-to-end automation (plan → implement → QA → fix loop), multi-stack via plugins, sandboxed execution with minimal permissions.

## Core Architecture
- **Orchestrator (Python):** Central decision-maker, assigns work, enforces gates, and manages state.
- **Agent Runtime:** Executes agent tasks with controlled tools (filesystem, git, build, tests).
- **Tool Layer:** Whitelisted, sandboxed commands (git, docker, rg, linters, build tools).
- **Stack Plugins:** Templates and rules per stack (e.g., Godot/C++, web, mobile).
- **Evaluation & QA Loop:** Detects failures, diagnoses, applies fixes, and retries.
- **Artifact Publisher:** Pushes to GitHub, publishes releases/changelogs.

### Recommended Repository Layout
```
agent-factory/
  orchestrator/
    main.py
    config.yaml
    router.py
    state_store.py
    task_graph.py
  agents/
    chief_planner.py
    architect.py
    scaffolder.py
    implementer.py
    reviewer.py
    qa.py
    fixer.py
    docs.py
    release.py
  tools/
    fs_tool.py
    git_tool.py
    shell_tool.py        # whitelist + sandbox
    docker_tool.py
    test_runner.py
    code_search.py
  stacks/
    godot_desktop/
      template/
      rules.yaml
      checks.yaml
    web_fullstack/
      template/
      rules.yaml
      checks.yaml
  runs/
    <project_name>/
      input_prompt.md
      plan.json
      logs/
      reports/
  ci/
    github_actions.yml
  README.md
```

## Agent Roles (minimal effective set)
1. **Chief Planner:** Converts prompt into roadmap, milestones, atomic backlog tasks, and Definition of Done (DoD).
2. **Architect:** Defines layered architecture, modules, interfaces, naming, and foldering; records ADRs.
3. **Scaffolder:** Creates repo, folder structure, CI, tooling, templates, and config.
4. **Implementers (N):** Build specific modules or features on separate branches.
5. **Reviewer:** Automated code review for style, security, complexity, and module coherence.
6. **QA/Test:** Writes and runs tests; produces reports and bug tasks.
7. **Fixer:** Applies targeted patches from failure logs (hotfix loop).
8. **Docs:** Writes README, docs, diagrams, and “How to extend.”
9. **Release:** Tags/releases, packages artifacts, and delivers final checklist.

> Scale via pools of Implementers activated on demand (fan-out/fan-in), not always-on agents.

## Tooling (allowed commands)
- **Core:** git, python, docker, rg, linters (ruff/black/eslint/clang-format), build tools (cmake/ninja/node/godot headless).
- **Rules:** Agents cannot run arbitrary commands; all commands flow through the whitelisted tool layer with sandboxing (docker by default).

## Shared State (single source of truth)
- **State store:** `runs/<project>/plan.json` + `runs/<project>/state.json` capturing backlog, milestones, gates, test results, decisions, branches/PRs.
- **Logs:** `runs/<project>/logs/*.jsonl`
- **Decisions:** `runs/<project>/adr/ADR-XXXX-*.md`
- **Incidents:** `runs/<project>/incidents/INC-XXXX.md` when auto-fix loop exhausts retries.

## Standard Workflow (gated pipeline)
1. **Ingest:** Save prompt to `input_prompt.md`; detect stack; load stack rules.
2. **Plan:** Chief Planner produces backlog/milestones/DoD; Architect emits ADRs.
3. **Scaffold:** Repo + CI + templates; baseline build + commit.
4. **Implement (fan-out):** Branch per task; Implementers code; Reviewer gates PRs.
5. **QA/Test:** Run build/lint/test in docker; produce reports.
6. **Fix Loop:** On failure, Fixer patches and re-runs QA (max 6 attempts) else raise Incident + GitHub Issue.
7. **Docs:** Update README/docs/diagrams.
8. **Release:** Tag, changelog, packaged artifacts, final checklist.

### Gate Criteria
- Build + lint + tests pass.
- Smoke test passes (app launches/responds).
- DoD satisfied for milestone.
- Security/secret scan clean (where applicable).

## Auto-Fix Loop (mandatory)
1. QA captures failing command, stdout/stderr, exit code, and implicated files.
2. Debugger classifies error (deps/syntax/runtime/test assertion/etc.).
3. Fixer applies minimal patch and augments/updates tests if needed.
4. QA reruns the failing command.
5. Repeat up to 6 attempts; on persistent failure, file an Incident and GitHub Issue with logs and next steps.

## UI/UX Decisions (when style provided)
- Produce `docs/ui/style_guide.md` + `design-tokens.json` + `apps/ui-kit/` components + `apps/demo/` (login, dashboard, details).
- Gate: UI build intact; basic accessibility (contrast + keyboard nav) validated; visual diff/screenshot captured.

## Stack Plugin Pattern
- Each stack directory contains:
  - `template/` scaffold
  - `rules.yaml` (lint/build/test commands, naming conventions)
  - `checks.yaml` (gates, perf budgets, security checks)
- Stack loader merges rules into orchestrator runtime.

## Decision & Governance Rules
- Every significant technical choice → ADR.
- Every modification → atomic commit.
- No feature creep: Scope Guard agent enforces prompt boundaries.
- Security defaults: sandboxed execution, secrets scanning, allowlist commands only.

## Operational Prompt (boot instruction)
Use this as the orchestrator’s initial control prompt when a user submits a plan:
> You are PROJECT-FORGE Orchestrator. Take the input plan and generate: (1) backlog JSON (milestone→feature→task), (2) repo skeleton with CI, Docker/Makefile, and runnable app scaffold, (3) minimal test suite executed. Proceed milestone by milestone with gates (build+test+lint+smoke). On failure, enter auto-fix loop (max 6 attempts), else open Incident and GitHub Issue. Record ADRs for key decisions. Keep changes modular and avoid unrequested features.

## Data Structures (minimum)
- **Task:** id, description, expected output, DoD, owner, status.
- **Artifact:** files generated, test logs, build reports, screenshots.
- **GateResult:** pass/fail, rationale, fix suggestions.
- **Decision:** ADR reference, context, decision, consequences.

## Publishing & Release
- Push branches/PRs per milestone; Reviewer enforces gates.
- Release agent tags versions, publishes changelog, and exports runnable artifacts (docker image/zip).
- Final delivery includes README, architecture docs, tests executed, reports, and build/run instructions.

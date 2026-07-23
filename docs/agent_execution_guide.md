# Agent Execution Guide

This document defines how Codex or another implementation agent should work on this repository using short prompts without losing scope, security requirements, or validation detail.

## 1. Documentation authority order

Before implementation, read documents in this order:

1. [`current_state.md`](current_state.md) — what is actually implemented and deployed;
2. [`development_plan.md`](development_plan.md) — phase ordering and status;
3. the selected phase contract:
   - the [archived Phase 16 contract](archive/v1_phase_16/phase_16_identity_ownership_contract.md) when maintaining its implementation, or
   - [`future_phase_contracts.md`](future_phase_contracts.md);
4. [`architecture.md`](architecture.md) — trust boundaries and system design;
5. [`deployment.md`](deployment.md) — environment and production behavior;
6. [`testing.md`](testing.md) — required validation;
7. domain documents such as RAG, risk, data-source, or agent design files.

When code and documentation disagree:

- inspect the code and tests;
- state the mismatch;
- do not silently assume the documentation is implemented;
- update the documentation to reflect reality or fix the code when the phase contract requires it.

## 2. Required start-of-task procedure

```bash
git status
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

Create or switch to the requested phase branch. Never begin a future phase from an outdated base.

Inspect:

- branch diff against `main`;
- relevant migrations;
- configuration and environment files;
- authentication and authorization dependencies;
- frontend API/BFF paths;
- existing tests;
- current phase status in documentation.

## 3. Scope rules

- Implement only the selected phase or correction scope.
- Preserve all completed behavior and safety boundaries.
- Do not begin later-phase infrastructure unless it is a necessary interface foundation explicitly allowed by the selected contract.
- Do not introduce wallets, private-key handling, signing, custody, transaction execution, automated capital allocation, guaranteed returns, or personalized financial advice.
- Do not mark scaffolding, placeholder pages, mocked external behavior, or unverified provider setup as complete.

## 4. Implementation evidence

Every claimed deliverable needs evidence from at least one of:

- production code path;
- migration;
- automated test;
- browser/integration test;
- deployment configuration;
- manual external verification recorded in the final report.

A documentation statement alone is not evidence.

## 5. Security review checklist

For every change, inspect:

- authentication source of truth;
- authorization on list, detail, create, update, delete, and export paths;
- tenant and owner filters;
- secret/token/cookie exposure;
- SSRF and proxy destination control;
- request size and schema bounds;
- concurrency and idempotency;
- deletion and retention;
- logging and audit redaction;
- public-demo regression;
- failure behavior and safe status codes.

## 6. Testing expectations

Run the commands required by [`testing.md`](testing.md) and the selected phase contract.

At minimum:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py

cd ../frontend
npm ci
npm run lint
npm run build

cd ..
docker compose config
docker compose -f docker-compose.production.yml config
```

Run upgrade/downgrade/upgrade, browser tests, PostgreSQL concurrency tests, cleanup, worker tests, retrieval evaluation, security scans, or deployment checks when required by the phase contract.

Do not report a check as passed unless it was executed successfully.

## 7. Status labels

Use only:

```text
Planned
In Progress
Implemented Foundation
Complete
Blocked
```

Definitions:

- **Planned** — no implementation branch or only design discussion.
- **In Progress** — implementation exists but completion gates are not satisfied.
- **Implemented Foundation** — core interfaces/models exist, but important workflows or external validation remain; use sparingly and list gaps.
- **Complete** — every contract gate, automated check, required deployment check, and documentation update passed.
- **Blocked** — progress cannot continue without an external decision, credential, provider, legal review, or unresolved dependency.

Never change a phase to `Complete` because tests compile or a page renders.

## 8. Documentation update protocol

Every implementation or correction pass updates:

- `docs/current_state.md`;
- `docs/development_plan.md` status when justified;
- the selected phase contract when a new invariant, failure mode, or acceptance criterion is discovered;
- `docs/architecture.md` when trust boundaries or components change;
- `docs/deployment.md` when environment, secrets, startup, domains, or provider setup changes;
- `docs/testing.md` when commands or required coverage change;
- `README.md` only for high-level user/developer-facing changes;
- `CHANGELOG.md` for meaningful shipped or branch-level milestones.

Documentation must separate:

- implemented and tested;
- implemented but externally unverified;
- planned;
- deferred to a later phase;
- known blockers.

## 9. Commit and PR rules

- inspect `git diff` before staging;
- do not commit secrets, `.env`, generated credentials, private data, or runtime artifacts;
- use logical commits;
- keep unrelated changes out of the phase branch;
- push only the requested branch;
- open a draft PR unless explicitly asked for ready-for-review;
- do not merge without explicit instruction;
- recommend squash merge for large iterative branches unless preserving commit history has a clear value.

## 10. Required final report

Every phase or correction run ends with:

1. verdict: complete, partially complete, blocked, or not ready;
2. branch and base;
3. architecture changes;
4. security and authorization changes;
5. migrations;
6. frontend workflows;
7. tests and commands executed;
8. exact results;
9. files changed;
10. commits created;
11. external/manual verification still required;
12. known limitations;
13. merge recommendation.

## 11. Standard short prompts

### Implement a new phase

```text
Implement V1 Phase <N> on a new branch from current main.
Read docs/current_state.md, docs/development_plan.md,
the relevant phase contract, docs/architecture.md, docs/deployment.md,
docs/testing.md, and docs/agent_execution_guide.md.
Follow the contract exactly, preserve completed behavior, run all required
checks, update the docs, commit logically, push the branch, open a draft PR,
and do not merge.
```

### Correct an existing phase branch

```text
Audit the current Phase <N> branch against the relevant contract and current
main. Fix every blocker, preserve prior phases, run all required tests,
update current-state and contract documentation, commit the corrections,
push the same branch, and do not merge.
```

### Documentation-only review

```text
Review the current branch implementation and make the repository documentation
fully match reality and the phase contracts. Record implemented behavior,
remaining blockers, validation evidence, and later-phase handoffs. Commit only
documentation changes to the current branch and do not merge.
```

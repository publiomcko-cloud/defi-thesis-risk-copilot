# Agent Execution Guide

This document defines how Codex or another implementation agent should work on this repository using short prompts without losing scope, security requirements, or validation detail.

## 1. Documentation authority order

After a new chat/session/context reset, read documents in this order:

1. [`agent_memory/PROJECT_MEMORY.md`](agent_memory/PROJECT_MEMORY.md) — stable project architecture, trust boundaries, phase history, and resume protocol;
2. [`agent_memory/CURRENT_HANDOFF.md`](agent_memory/CURRENT_HANDOFF.md) — latest recorded branch/phase/migration/CI snapshot; verify it before trusting time-sensitive state;
3. [`portfolio_profile.md`](portfolio_profile.md) — active implementation profile and current portfolio-versus-product boundary;
4. the selected active phase plan/evidence:
   - the [archived Phase 16 contract](archive/v1_phase_16/phase_16_identity_ownership_contract.md) when maintaining its implementation,
   - the [archived Phase 17 record](archive/v1_phase_17/) when maintaining durable jobs,
   - the [archived Phase 18 record](archive/v1_phase_18/) when maintaining durable knowledge/retrieval,
   - [`phase_19_execution_plan.md`](phase_19_execution_plan.md) when maintaining the merged Phase 19 foundation,
   - [`phase_20_execution_plan.md`](phase_20_execution_plan.md) and [`phase_20_evidence_matrix.md`](phase_20_evidence_matrix.md) for active Phase 20 work, or
   - [`future_phase_contracts.md`](future_phase_contracts.md) for later/product-capable scope;
5. [`current_state.md`](current_state.md) — detailed implemented/deployed history;
6. [`development_plan.md`](development_plan.md) — broader roadmap/history;
7. [`architecture.md`](architecture.md) — trust boundaries and system design;
8. [`deployment.md`](deployment.md) — environment and production behavior;
9. [`testing.md`](testing.md) — required validation;
10. domain documents such as RAG, risk, data-source, or agent design files.

[`productization_backlog.md`](productization_backlog.md) is authoritative for commercial/provider work intentionally deferred from the active portfolio profile.

`current_state.md`, `development_plan.md`, archived plans, and `future_phase_contracts.md` may contain historical commercial framing that predates the portfolio pivot. When that wording conflicts with the active portfolio profile or current Phase 20 execution/evidence, do not resurrect deferred commercial scope automatically.

When code and documentation disagree:

- inspect the code, migrations, configuration, tests, current branch/PR state, and hosted checks;
- state the mismatch;
- do not silently assume the documentation is implemented;
- current portfolio profile + active execution/evidence take precedence over stale roadmap wording;
- update the documentation to reflect reality or fix the code when the active contract requires it.

`CURRENT_HANDOFF.md` is a snapshot, not a replacement for verification. If Git has advanced, trust verified repository state and refresh the handoff.

## 2. Required start-of-task procedure

```bash
git status
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

When the task explicitly continues an unmerged branch or PR, do not discard that branch state by blindly starting from `main`. Verify the requested branch/PR head first, then create/switch branches from the correct reviewed base.

Inspect:

- branch diff against its intended base;
- relevant migrations and actual Alembic head;
- configuration and environment files;
- authentication and authorization dependencies;
- frontend API/BFF paths;
- existing tests;
- current phase status in code and documentation;
- latest hosted CI/security status when available.

## 3. Scope rules

- Implement only the selected phase or correction scope.
- Preserve all completed behavior and safety boundaries.
- Do not begin later-phase infrastructure unless it is a necessary interface foundation explicitly allowed by the selected contract.
- Do not introduce wallets, private-key handling, signing, custody, transaction execution, automated capital allocation, guaranteed returns, or personalized financial advice.
- Do not mark scaffolding, placeholder pages, mocked external behavior, synthetic adapters, or unverified provider setup as production-complete.
- A capability may be implementation-complete while intentionally disabled in the public portfolio deployment.
- Do not turn productization-backlog requirements back into current portfolio blockers without an explicit profile/owner decision.

## 4. Implementation evidence

Every claimed deliverable needs evidence from at least one of:

- production code path;
- migration;
- automated test;
- PostgreSQL concurrency/integration test where applicable;
- browser/integration test;
- deployment configuration;
- manual external verification recorded in the final report.

A documentation statement alone is not evidence.

Before claiming that a future slice is absent or complete, confront proposed documentation/table names with the actual repository tree, migration head, runtime modules, and tests.

## 5. Security review checklist

For every change, inspect:

- authentication source of truth;
- authorization on list, detail, create, update, delete, and export paths;
- tenant and owner filters;
- secret/token/cookie exposure;
- SSRF and proxy destination control;
- request size and schema bounds;
- exact browser origins, BFF upstream allowlists, redirect handling, and CORS;
- upload media/signature validation and scanner failure behavior before storage;
- telemetry, analytics, alert, synthetic, and dashboard paths for aggregate-only output, ownership, redaction, delivery failure, purpose separation, and feature-gated rollout;
- backup/restore tooling for isolated targets, metadata-only evidence, RPO/RTO, provider/object parity, retention gating, and secret-free rotation records;
- concurrency and idempotency;
- deletion and retention;
- logging and audit redaction;
- public-demo regression;
- failure behavior and safe status codes;
- independence among rate limits, product quotas, entitlements, usage, analytics, audit, and any future billing evidence.

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

Run upgrade/downgrade/upgrade, browser tests, PostgreSQL concurrency tests, cleanup, worker tests, retrieval evaluation, dependency/security scans, supply-chain checks, recovery exercises, or deployment checks when required by the active phase contract.

Do not report a check as passed unless it was executed successfully or verified from the exact current hosted commit.

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
- **Complete** — every active-profile contract gate, automated check, required deployment check, and documentation update passed.
- **Blocked** — progress cannot continue without an external decision, credential, provider, review, or unresolved dependency required by the active profile.

For portfolio work, a product-only activation gate recorded in `productization_backlog.md` is not automatically a `Blocked` status for the portfolio implementation.

Never change a phase to `Complete` because tests compile or a page renders.

## 8. Documentation and memory update protocol

Every implementation or correction pass updates, when materially affected:

- `docs/agent_memory/CURRENT_HANDOFF.md` at phase boundaries, major corrections, profile changes, migration-head changes, or other context that a new agent must know immediately;
- `docs/agent_memory/PROJECT_MEMORY.md` only when stable architecture, permanent invariants, authority rules, or durable phase-history facts change;
- `docs/current_state.md` for detailed implementation/deployment truth;
- `docs/development_plan.md` status when justified;
- the selected active phase contract/evidence when a new invariant, failure mode, or acceptance criterion is discovered;
- `docs/architecture.md` when trust boundaries or components change;
- `docs/deployment.md` when environment, secrets, startup, domains, or provider setup changes;
- `docs/testing.md` when commands or required coverage change;
- `README.md` only for high-level user/developer-facing changes;
- `CHANGELOG.md` for meaningful shipped or branch-level milestones.

Do not make `PROJECT_MEMORY.md` a changelog. Keep it compact and stable. Put volatile branch SHA, PR, migration head, current CI, and next-slice state in `CURRENT_HANDOFF.md`.

Documentation must separate:

- implemented and tested;
- implemented but intentionally disabled;
- synthetic/demo-only;
- implemented but externally unverified;
- planned;
- deferred to productization/later phase;
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
13. merge recommendation;
14. whether `CURRENT_HANDOFF.md` remains accurate.

## 11. Standard short prompts

### Implement a new phase/slice

```text
Implement V1 Phase <N> on a new branch from the correct current reviewed base.
Read docs/agent_memory/PROJECT_MEMORY.md,
docs/agent_memory/CURRENT_HANDOFF.md, docs/portfolio_profile.md,
the active phase execution/evidence, docs/current_state.md,
docs/architecture.md, docs/deployment.md, docs/testing.md,
and docs/agent_execution_guide.md.
Verify branch/PR/migration/CI state before editing. Follow the active portfolio
contract exactly, preserve completed behavior, run all required checks, update
the handoff and living docs, commit logically, push the branch, open a draft PR
when requested, and do not merge.
```

### Correct an existing phase branch

```text
Audit the current Phase <N> branch against PROJECT_MEMORY, CURRENT_HANDOFF,
the active profile/contract, and its intended base. Verify current Git and
migration state, fix every active-profile blocker, preserve prior phases, run
all required tests, update evidence and CURRENT_HANDOFF, commit the corrections,
push the same branch, and do not merge.
```

### Documentation-only review

```text
Review the current branch implementation against the repository tree,
migrations, tests, configuration, active profile, and phase evidence. Make the
repository documentation and agent-memory handoff match reality. Record
implemented behavior, intentional disabled/synthetic scope, remaining blockers,
validation evidence, and next-slice handoff. Commit only documentation changes
to the requested branch and do not merge.
```

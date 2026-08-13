# Phase 20 Evidence Matrix

Status: **In Progress — portfolio profile active**

Current scope is defined by [`portfolio_profile.md`](portfolio_profile.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md). Requirements intentionally deferred from the portfolio are preserved in [`productization_backlog.md`](productization_backlog.md).

| Slice | Portfolio status | Evidence state |
| --- | --- | --- |
| 20A | Complete | Governance, threat model, taxonomy, provider-decision and data-model foundations exist |
| 20B | Complete | Migration `0023`, consent-aware first-party analytics, lifecycle integration, PostgreSQL concurrency tests, browser coverage and hosted implementation checks passed before the portfolio-doc refactor |
| 20C | Review corrections in progress / required | The original Phase 20C implementation passed hosted CI. Migration `0024`, durable private schedules, DST, PostgreSQL one-winner claims, Phase 17 jobs, lifecycle/export/retention, browser and operations aggregates are implemented; authoritative completion and daily scheduled-run quota corrections now require fresh hosted checks. Production dispatch remains disabled. |
| 20D | Planned / required | In-app preferences, intents, duplicate suppression, tenant and browser evidence needed |
| 20E | Optional | Synthetic/provider-neutral delivery demonstration only |
| 20F | Planned / required | Versioned entitlements and non-billable usage/reconciliation evidence needed |
| 20G | Deferred | Not required for portfolio completion; preserved for future productization |
| 20H | Planned / required | Invitations, seats, ownership and PostgreSQL concurrency evidence needed |
| 20I | Planned / required, reduced | First-party bounded support/privacy/status evidence needed |
| 20J | Planned / required | Portfolio architecture closeout |

## Phase 20B checkpoint

Phase 20B is implementation-complete for the portfolio profile. Commit `a7bcd42` contains the deployment-disabled consent correction and passed the required implementation validation at that checkpoint.

Production analytics remains disabled. Its later activation is a productization task rather than a Phase 20 portfolio blocker.

## Current branch maintenance

The documentation-only portfolio refactor triggered fresh hosted checks on 2026-08-13. CI, CodeQL, Phase 19 failure exercises, dependency review, secret scan, workflow policy and SBOM checks passed before a fresh dependency audit identified newly known issues in existing dependencies.

The focused dependency maintenance updates `pypdf` from `6.14.2` to `6.15.0` and `cryptography` from `48.0.1` to `50.0.0`, and pins the production `nanoid` transitive dependency to `3.3.18`. Local `pip-audit` and production npm audit return no known high or critical findings. The supply-chain workflow now skips its npm-audit summary only when the npm-audit step was not reached, so a Python-audit failure remains precise. A fresh hosted CI run remains the PR merge gate.

## Phase 20C checkpoint

Phase 20C is limited to authenticated user-owned enabled private watchlist
targets. It deliberately does not schedule arbitrary analysis prompts,
organization work, discovery/review/RAG ingestion, notification delivery or
provider jobs. The API rejects all schedule access when deployment
authentication is disabled; it never reuses the public/demo identity.
`SCHEDULE_DISPATCH_ENABLED=false` remains the default and the production
configuration validator rejects activation. The original Phase 20C hosted
implementation checks passed. On 2026-08-13 the clean backend
suite, all 26 PostgreSQL integration tests on a newly created pgvector-enabled
local validation database, SQLite and PostgreSQL migration
upgrade/downgrade/upgrade checks, smoke/cleanup/recovery dry runs, frontend
lint/build/BFF/MFA/accessibility/security/browser tests, dependency and
supply-chain checks, and default/profile/production Compose rendering passed
locally. The remaining review findings require that successful evaluation leave
the occurrence `running` until Phase 17 control-plane completion atomically
marks both job and occurrence complete, and require the fixed server-owned
120-per-user UTC-day scheduled-run quota. Fresh hosted CI for those corrections
remains the merge gate; Phase 20C is not complete or merge-ready yet.
The current local correction validation passes the complete 28-test PostgreSQL
integration suite; this is not a substitute for fresh hosted CI or production
operational evidence.
Before any production activation, approved policy, scoped worker/scheduler
deployment and external operational evidence remain required.

## Portfolio closeout

Phase 20 becomes **Complete — Portfolio Profile** after required 20C, 20D, 20F, 20H, reduced 20I and 20J evidence passes, optional work is accurately labeled, deferred work remains documented rather than falsely completed, no high/critical security regression remains, dependency/security checks are green, migrations and rollback are tested, public feature flags are safe, and CI is green.

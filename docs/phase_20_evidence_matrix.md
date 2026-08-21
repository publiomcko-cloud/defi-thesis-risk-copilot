# Phase 20 Evidence Matrix

Status: **In Progress — portfolio profile active**

Current scope is defined by [`portfolio_profile.md`](portfolio_profile.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md). Requirements intentionally deferred from the portfolio are preserved in [`productization_backlog.md`](productization_backlog.md).

| Slice | Portfolio status | Evidence state |
| --- | --- | --- |
| 20A | Complete | Governance, threat model, taxonomy, provider-decision and data-model foundations exist |
| 20B | Complete | Migration `0023`, consent-aware first-party analytics, lifecycle integration, PostgreSQL concurrency tests, browser coverage and hosted implementation checks passed before the portfolio-doc refactor |
| 20C | Merged / production-disabled | The original Phase 20C implementation and the authoritative-completion/daily-scheduled-run-quota correction both passed hosted CI. Migration `0024`, durable private schedules, DST, PostgreSQL one-winner claims, Phase 17 jobs, lifecycle/export/retention, browser and operations aggregates merged as `8aeb84cec0427765322cf44b3827eee319e8064e`. Production dispatch remains disabled. |
| 20D | Merged / production-disabled | Migration `0025`, in-app preference and notification records, code-owned registry, authenticated API, notification center UI, source projections, lifecycle/export/deletion, retention cleanup, policy/access/pagination corrections, recovery coverage, PostgreSQL/browser/Compose/CodeQL/Supply Chain/Phase 19 exercise evidence merged as `32dfb91ece2344be5dbbcd2c8d12723bc2378126`. External delivery and production activation remain out of scope. |
| 20E | Optional | Synthetic/provider-neutral delivery demonstration only |
| 20F | In progress / shadow-only | Migration `0026` seeds `free-v1`; read-only resolver compares seven documented limits against legacy authorities with bounded fallback; immutable ledger and four authoritative meter points implemented; corrected hosted validation pending |
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
120-per-user UTC-day scheduled-run quota. Fresh hosted CI passed for correction
commit `cc8278c`; the current local correction validation also passes the
complete 28-test PostgreSQL integration suite. Phase 20C is locally complete,
but production activation remains separately gated and this evidence is
not a substitute for production operational validation.
Before any production activation, approved policy, scoped worker/scheduler
deployment and external operational evidence remain required.

## Phase 20D checkpoint

Phase 20D is in-app only. It adds server-owned notification preferences and
notification records with the exact initial categories
`monitoring.risk_alert`, `schedule.status`, `job.status`, and
`account.lifecycle`, and severities `informational`, `warning`, and
`critical`. Product/status categories default off where suppression is allowed;
account lifecycle notifications are mandatory. Notification rows store bounded
code-owned title/body/template IDs, source type/ID, deterministic idempotency
keys, allowed same-origin navigation metadata, read state, availability state,
policy outcome, and 30-day retention expiry.

Notifications are projections from existing authorities: watchlist alert
creation, schedule occurrence lifecycle, Phase 17 terminal job transitions,
account export, and MFA lifecycle audit events. The browser can list, inspect,
mark read/unread, mark all read, and update bounded preferences, but cannot
create a notification or choose category, severity, owner, source, template, or
idempotency identity. Quiet hours and digest behavior affect availability, not
source-event durability.

Final Phase 20D head `6a943e1bc6293ba88bcd7a8ab6ca68baca822e37`
passed hosted CI with PostgreSQL integration and real pytest failure
propagation, frontend/browser and Compose checks, CodeQL, Supply Chain Security
including Gitleaks and Trivy, and Phase 19 Failure Exercises on 2026-08-20.
The slice merged to `main` as `32dfb91ece2344be5dbbcd2c8d12723bc2378126`
on 2026-08-21. No production activation or external notification delivery is
claimed.

## Portfolio closeout

Phase 20 becomes **Complete — Portfolio Profile** after required 20C, 20D, 20F, 20H, reduced 20I and 20J evidence passes, optional work is accurately labeled, deferred work remains documented rather than falsely completed, no high/critical security regression remains, dependency/security checks are green, migrations and rollback are tested, public feature flags are safe, and CI is green.

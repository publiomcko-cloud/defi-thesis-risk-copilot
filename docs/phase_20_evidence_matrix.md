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
| 20F | Merged / shadow-only | Migration `0026` seeds `free-v1`; read-only resolver compares seven documented limits against legacy authorities with bounded fallback; immutable ledger and real schedule lease-loss/retry completion evidence merged as `1e5ea045390b11c7b8dc933a48b40a562e3270da` |
| 20G | Deferred | Not required for portfolio completion; preserved for future productization |
| 20H | Complete / merged | Migration `0028`, organization invitations/seats/ownership/export, real PostgreSQL lifecycle races and browser token-fragment/manual-entry coverage merged as `54329c6911fa1fada2160cc98ac0a57a3aaa5acc`. No production activation is claimed. |
| 20I | Active — checkpoint 20I-1 | Reduced first-party support/privacy request tracking on `agent/v1-phase-20i-support-privacy-status`, authorized by `docs/decisions/phase_20i_support_privacy_status_approval.md`. |
| 20J | Planned / required | Portfolio architecture closeout |

Phase 20F additionally runs an isolated PostgreSQL migration-cycle test using a
temporary database: `0025 -> 0026 -> 0025 -> 0026`. It verifies the seeded
catalog, overlap exclusion constraint, downgrade preservation of Phase 20C/20D
objects, and intentional retention of shared `btree_gist` extension support.

## Phase 20H checkpoint

Phase 20H adds the non-billable, server-owned `portfolio-org-v1` plan with the
`limit.organization.seats.count` entitlement. Existing user `free-v1` semantics
remain unchanged. Seat consumption is active memberships plus unexpired pending
invitations plus legacy pending memberships; a PostgreSQL organization-row lock
serializes seat-consuming invitation creation. Acceptance converts a reservation
to a membership without double counting. Existing over-limit organizations are
preserved and new invitations fail closed when the entitlement is missing or
corrupt.

The local evidence commands and results are recorded exactly as follows:

```bash
cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true .venv/bin/python -m pytest app/tests/test_phase20h_postgres.py app/tests/test_phase20h_postgres_migration.py app/tests/test_phase20h_sqlite_migration.py -q
# 9 passed: final-seat, resend/revoke, resend/accept, revoke/accept, duplicate-accept,
# explicit-entitlement, PostgreSQL 0026 -> 0028 -> 0026 -> 0028, and SQLite migration cycles

cd frontend && npm run test:phase20h
# passed: fragment link handling, manual token entry, token-free URL/storage, and POST { token }

cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true APP_ENV=test PUBLIC_DEMO_MODE=false AUTH_ENABLED=false VAST_ENABLED=false VAST_DRY_RUN=true .venv/bin/python -m pytest -q --tb=short
# passed: complete backend suite with PostgreSQL integration

cd frontend && npm run lint && npm run build && npm run test:e2e && npm run test:phase20h && npm run test:bff && npm run test:mfa && npm run test:mfa:routes && npm run test:accessibility && npm run test:security
# passed: typecheck, production build, Phase 16 and 20H E2E, route/BFF/MFA/a11y/security contracts

cd backend && PATH="$PWD/.venv/bin:$PATH" DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/defi_copilot_exercises RUN_POSTGRES_INTEGRATION=true APP_ENV=exercise PUBLIC_DEMO_MODE=false AUTH_ENABLED=false VAST_ENABLED=false VAST_DRY_RUN=true OPERATIONS_EXERCISES_ENABLED=true OPERATIONS_EXERCISES_ISOLATED=true python -m scripts.run_phase19_exercises --run
# passed: all 11 isolated exercises, including the HTTP harness and worker-loss recovery
```

`20260824_0028` directly follows `20260821_0026`; no `0027` file exists.
`0027` remains reserved/deferred for billing and was not fabricated. The
migration cycle verifies the seven `free-v1` limits are unchanged, the
organization default plan seeds once, organization assignments are removed for
downgrade before the user-only constraint returns, and legitimate user
assignments and Phase 20F PostgreSQL constraints survive.

No external invitation email is sent. Plaintext invitation tokens appear only
in the immediate create/resend demo response, durable token hashes are never
exposed, and browser links use URL fragments so plaintext is not transmitted in
HTTP navigation URLs. The organization seat plan is non-billable: no pricing,
payment, subscription, checkout, invoice, or production commercial-SaaS claim
exists. Phase 20G is **DEFERRED**. Phase 20H is COMPLETE for the portfolio
profile and merged as `54329c6911fa1fada2160cc98ac0a57a3aaa5acc`; Phase 20I
is active.

Phase 20H exact-head hosted validation completed before its merge. This does
not claim production activation or external delivery. Each Phase 20I head,
including documentation-only updates, requires its own green hosted run.

## Phase 20I checkpoint

Phase 20I is **ACTIVE** for the reduced portfolio profile under
[`phase_20i_support_privacy_status_approval.md`](decisions/phase_20i_support_privacy_status_approval.md).
Checkpoint 20I-1 is limited to bounded customer/privacy request authority and
lifecycle integration. Migration `20260828_0029_add_customer_requests.py`
directly follows `20260824_0028`; `0027` remains reserved/deferred for billing
and was not fabricated. It creates owner-scoped `customer_requests` with the
five code-owned types, API/schema and database text bounds, constrained
workflow/verification states, `RESTRICT` user ownership, and optional `SET
NULL` organization context.

The authenticated first-party API exposes create, owner list/read, and
requester close only. Request ownership is always server-derived; active
membership validates optional organization context without allowing an
organization or platform-admin content bypass. Privacy request context remains
individual-only. Close uses a PostgreSQL row lock and is a deterministic no-op
after the first close, which emits one bounded audit event.

Subject and description are private application content. The implementation
does not put them in logs, structured audit metadata, analytics, notifications,
LLM prompts, embedding/retrieval paths, or provider payloads. There is no
Phase 20I analytics event or automatic request processing. Existing Phase 16
account export includes only the owner's request projection, account deletion
removes owned rows, and organization deletion clears context while preserving
owner isolation. No legal retention policy, production/legal approval, external
helpdesk/status provider, or external delivery is claimed.

Local evidence for this checkpoint:

```bash
cd backend && .venv/bin/python -m compileall -q app
# passed

cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true .venv/bin/python -m pytest app/tests/test_phase20i_customer_requests.py app/tests/test_phase20i_sqlite_migration.py app/tests/test_phase20i_postgres.py app/tests/test_phase20i_postgres_migration.py -q
# passed: 13 tests; SQLite and PostgreSQL 0028 -> 0029 -> 0028 -> 0029 cycles

cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true .venv/bin/python -m pytest app/tests/test_phase16_identity.py app/tests/test_phase16_knowledge_scope.py app/tests/test_phase16_migration_hardening.py app/tests/test_phase20b_product_analytics.py app/tests/test_phase20h_seats.py app/tests/test_phase20h_ownership.py app/tests/test_phase20h_lifecycle_export.py app/tests/test_phase20h_postgres.py app/tests/test_phase20h_postgres_ownership.py app/tests/test_phase20h_sqlite_migration.py app/tests/test_phase20h_postgres_migration.py -q
# passed: 83 tests across affected Phase 16, 20B, and 20H authority/lifecycle paths

cd frontend && npm run lint && npm run build
# passed: TypeScript typecheck and production build
```

The migration cycles preserve Phase 20H invitations and organization plan
state, preserve all seven `free-v1` limits, remove only Phase 20I schema on
downgrade, and recreate the table cleanly on re-upgrade. Phase 20G remains
**DEFERRED**. Public status and request-management UI remain for 20I-2.

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

# Phase 20 Evidence Matrix

Status: **Complete — Portfolio Profile.** Phase 20J technical completion
evidence passed on `4b09071623bc686c1e623cbf383eb198b3c89412`; PR #31 remains
DRAFT and unmerged.

Current scope is defined by [`portfolio_profile.md`](portfolio_profile.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md). Requirements intentionally deferred from the portfolio are preserved in [`productization_backlog.md`](productization_backlog.md).

| Slice | Portfolio status | Evidence state |
| --- | --- | --- |
| 20A | Complete | Governance, threat model, taxonomy, provider-decision and data-model foundations exist |
| 20B | Complete | Migration `0023`, consent-aware first-party analytics, lifecycle integration, PostgreSQL concurrency tests, browser coverage and hosted implementation checks passed before the portfolio-doc refactor |
| 20C | Merged / production-disabled | The original Phase 20C implementation and the authoritative-completion/daily-scheduled-run-quota correction both passed hosted CI. Migration `0024`, durable private schedules, DST, PostgreSQL one-winner claims, Phase 17 jobs, lifecycle/export/retention, browser and operations aggregates merged as `8aeb84cec0427765322cf44b3827eee319e8064e`. Production dispatch remains disabled. |
| 20D | Merged / production-disabled | Migration `0025`, in-app preference and notification records, code-owned registry, authenticated API, notification center UI, source projections, lifecycle/export/deletion, retention cleanup, policy/access/pagination corrections, recovery coverage, PostgreSQL/browser/Compose/CodeQL/Supply Chain/Phase 19 exercise evidence merged as `32dfb91ece2344be5dbbcd2c8d12723bc2378126`. External delivery and production activation remain out of scope. |
| 20E | Omitted / optional | No synthetic delivery adapter or external provider is implemented; the documented provider-neutral boundary remains optional future work. |
| 20F | Merged / shadow-only | Migration `0026` seeds `free-v1`; read-only resolver compares seven documented limits against legacy authorities with bounded fallback; immutable ledger and real schedule lease-loss/retry completion evidence merged as `1e5ea045390b11c7b8dc933a48b40a562e3270da` |
| 20G | Deferred | Not required for portfolio completion; preserved for future productization |
| 20H | Complete / merged | Migration `0028`, organization invitations/seats/ownership/export, real PostgreSQL lifecycle races and browser token-fragment/manual-entry coverage merged as `54329c6911fa1fada2160cc98ac0a57a3aaa5acc`. No production activation is claimed. |
| 20I | Complete / merged | Bounded first-party support/privacy/status merged as `f55ee37db98abfcf8a3d7651f81436bc63e6a9b8`. PR #29 was superseded only by the PR #30 merge vehicle; both used implementation head `3c8680e69cf0eb9e33bb940fd82fda80406da227`. |
| 20J | Complete | Final architecture audit, full-chain PostgreSQL migration regression, evidence reconciliation, and exact-head hosted technical completion on `4b09071623bc686c1e623cbf383eb198b3c89412`. PR #31 remains DRAFT and unmerged. |

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
is complete and merged as `f55ee37db98abfcf8a3d7651f81436bc63e6a9b8`.

Phase 20H exact-head hosted validation completed before its merge. This does
not claim production activation or external delivery. Phase 20J technical
completion evidence is recorded separately at `4b09071623bc686c1e623cbf383eb198b3c89412`.

## Phase 20I checkpoint

Phase 20I is **COMPLETE** for the reduced portfolio profile under
[`phase_20i_support_privacy_status_approval.md`](decisions/phase_20i_support_privacy_status_approval.md).
Checkpoint 20I-1 is complete and merged as
`8fb2fd6e998e740cba9bd29078597b5a9c1cbfa3`. It is limited to bounded
customer/privacy request authority and lifecycle integration. Migration
`20260828_0029_add_customer_requests.py`
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
downgrade, and recreate the table cleanly on re-upgrade.

Checkpoint 20I-2 is accepted at
`1465601712c29988360d7017cd9a6e7f1a5d007f` on its historical implementation
branch, `agent/v1-phase-20i-2-request-status-ui`.
It adds authenticated `/support`, owner-only history/detail and close UI,
privacy-type links to the existing account export/deletion workflow, a curated
same-origin BFF `/customer-requests` family, and public `/status`. Private
unsaved request text is volatile and is not placed in URLs, local/session
storage, cookies, titles, metadata, analytics, notifications, logs, LLM/RAG, or
external services. `/status` maps only public-safe health success/failure to
coarse availability and exposes no customer, tenant, database, provider,
incident, infrastructure, SLA, uptime-history, or subscriber information.
There is no external helpdesk/status provider or production/commercial support
claim.

Checkpoint 20I-3 adds a bounded BFF query-string rule: the customer-request
collection, detail, and close paths reject any non-empty query string with
`400` before creating an upstream request. It does not alter unrelated BFF
query handling, logs no query content, and browser evidence proves a rejected
query-bearing request never reaches the backend mock.

Local 20I-3 evidence:

```bash
cd frontend && npm run lint && npm run build && npm run test:phase20i && npm run test:e2e && npm run test:phase20h && npm run test:bff && npm run test:mfa && npm run test:mfa:routes && npm run test:accessibility && npm run test:security
# passed: typecheck, production build, Phase 20I workspace/status/BFF privacy E2E,
# Phase 16 and 20H E2E, BFF/MFA/accessibility/security contracts

cd frontend && npm run start -- --hostname 127.0.0.1 --port 3000
cd frontend && npm run test:route-smoke
# passed: production-server route smoke for 12 Phase 16 pages

cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true APP_ENV=test PUBLIC_DEMO_MODE=false AUTH_ENABLED=false VAST_ENABLED=false VAST_DRY_RUN=true .venv/bin/python -m pytest -q --tb=short
# passed: full PostgreSQL-enabled backend suite; 437 tests collected, zero failures

cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5435/defi_copilot RUN_POSTGRES_INTEGRATION=true APP_ENV=test PUBLIC_DEMO_MODE=false AUTH_ENABLED=false .venv/bin/python -m pytest app/tests/test_phase20i_customer_requests.py app/tests/test_phase20i_postgres.py app/tests/test_phase20i_sqlite_migration.py app/tests/test_phase20i_postgres_migration.py app/tests/test_phase20h_postgres.py app/tests/test_phase20h_postgres_migration.py -q --tb=short
# passed: 23 explicit Phase 20I/20H PostgreSQL owner-isolation, close, lifecycle,
# invitation/plan interaction, and SQLite/PostgreSQL 0028 -> 0029 -> 0028 -> 0029 tests

cd backend && PATH="$PWD/.venv/bin:$PATH" DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5435/defi_copilot_exercises_20i APP_ENV=exercise OPERATIONS_EXERCISES_ENABLED=true OPERATIONS_EXERCISES_ISOLATED=true OPERATIONS_EXERCISE_TIMEOUT_SECONDS=180 VAST_ENABLED=false VAST_DRY_RUN=true VAST_REAL_RENTALS_ENABLED=false RUN_POSTGRES_INTEGRATION=true .venv/bin/python -m scripts.run_phase19_exercises --run --evidence-file /tmp/phase20i-phase19-exercise-evidence.json
# passed: all 11 fixed isolated Phase 19 exercises

docker compose config --quiet
docker compose -f docker-compose.production.yml config --quiet
docker compose up -d --build
docker compose down
docker compose -f docker-compose.production.yml up -d --build
# passed: both Compose configurations, normal and production image/startup paths,
# backend /health and /ready, and frontend /status and /support probes

python3 scripts/supply_chain.py check-workflows
python3 scripts/supply_chain.py check-lockfiles
python3 scripts/supply_chain.py check-security-exceptions
python3 scripts/supply_chain.py generate-sbom --output /tmp/phase20i-sbom.cdx.json
cd backend && .venv/bin/pip-audit -r requirements.txt --format json
cd frontend && npm audit --omit=dev --audit-level=high --json
# passed: workflow/lockfile/exception policy, 74-component SBOM, and zero known
# high/critical pip/npm audit findings
```

`0029` directly follows `0028`; no `0027` migration file exists. The explicit
migration evidence preserves Phase 20H invitations, organization plan state,
the exact seven-key `free-v1` contract, and all Phase 20H constraints while
downgrade removes only Phase 20I schema and re-upgrade recreates it without FK
or orphan corruption. Phase 20G remains **DEFERRED**. Phase 20I becomes
complete only after all required hosted checks are green for the exact current
DRAFT PR head; this does not claim production activation, legal approval,
external delivery, an external provider, subscriber collection, billing, or an
SLA/uptime history.

The pull-request Frontend job runs the Phase 16, Phase 20H, and Phase 20I
browser harnesses, so final hosted evidence includes the support/status and BFF
privacy boundary rather than only the earlier browser slices.

## Phase 20B checkpoint

Phase 20B is implementation-complete for the portfolio profile. Commit `a7bcd42` contains the deployment-disabled consent correction and passed the required implementation validation at that checkpoint.

Production analytics remains disabled. Its later activation is a productization task rather than a Phase 20 portfolio blocker.

## Phase 20J closeout checkpoint

The Phase 20J branch adds no schema migration. It adds
`test_phase20j_postgres_migration_chain.py`, an isolated PostgreSQL regression
for `0022 -> 0029 -> 0022 -> 0029`. It verifies the exact final revision,
Phase 16 user/organization/membership and rate-limit authorities, all Phase 20
table boundaries, `free-v1`'s seven immutable limits, `portfolio-org-v1`'s
five-seat entitlement, and the key Phase 20 uniqueness/exclusion constraints.
The downgrade removes only the intended post-`0022` schema; the re-upgrade
reseeds both catalogs and recreates the constraints.

The closeout audit confirms 20E is omitted, 20G remains **DEFERRED**, 20F is
shadow-only/non-billable, 20D remains in-app only, and the public-safe flags
remain disabled. Local 2026-09-02 validation passed the full PostgreSQL backend
suite, all focused Phase 20 migration cycles, frontend/browser/BFF/MFA/a11y/
security/route-smoke checks, both Compose runtime paths, all eleven fixed
Phase 19 exercises, source-policy/SBOM checks, and zero-known-finding Python
and production npm audits. `pypdf` is pinned at `6.16.1` to remediate the
three advisories found in `6.15.0`. On the implementation/evidence head
`4b09071623bc686c1e623cbf383eb198b3c89412`, CI, Backend and PostgreSQL,
Frontend, Docker Compose Config, CodeQL, Supply Chain Security, Phase 19
Failure Exercises, and Vercel all passed.

## Current branch maintenance

The documentation-only portfolio refactor triggered fresh hosted checks on 2026-08-13. CI, CodeQL, Phase 19 failure exercises, dependency review, secret scan, workflow policy and SBOM checks passed before a fresh dependency audit identified newly known issues in existing dependencies.

The focused dependency maintenance updates `pypdf` from `6.14.2` through
`6.16.1`, `cryptography` from `48.0.1` to `50.0.0`, and pins the production
`nanoid` transitive dependency to `3.3.18`. Local `pip-audit` and production
npm audit return no known high or critical findings. The supply-chain workflow
now skips its npm-audit summary only when the npm-audit step was not reached,
so a Python-audit failure remains precise. The Phase 20J technical completion
gate subsequently passed on `4b09071623bc686c1e623cbf383eb198b3c89412`; PR #31
remains DRAFT and unmerged.

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

Phase 20 is **Complete — Portfolio Profile**: required 20C, 20D, 20F, 20H,
reduced 20I, and 20J evidence passed on the validated implementation/evidence
head; optional work is accurately labeled, deferred work remains documented
rather than falsely completed, no high/critical security regression remains,
dependency/security checks are green, migrations and rollback are tested, and
public feature flags are safe. PR #31 remains the DRAFT, unmerged closeout
vehicle pending explicit merge authorization.

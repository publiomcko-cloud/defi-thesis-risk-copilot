# Testing — DeFi Thesis & Risk Copilot

This file is the validation index. Detailed acceptance tests are defined in:

- [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md)
- [`future_phase_contracts.md`](future_phase_contracts.md)
- [`agent_execution_guide.md`](agent_execution_guide.md)

No check may require production customer data, real paid infrastructure, or live capital execution.

## 1. Baseline commands

Backend:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run test:bff
```

Compose:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

Report a command as passed only when it was executed successfully.

## 2. Migration validation

For schema-changing phases:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Also validate PostgreSQL with existing prior-phase data, ownership backfills, constraints, indexes, and intentional deletion behavior.

## 3. Permanent Phase 15 regression suite

Every later phase preserves:

- public visitors never receive administrator access;
- public privileged mutations remain denied;
- bounded analysis, simulation, options, and market-data flows work;
- request limits and rate limits work;
- seeded reports and Markdown export work;
- deterministic risk fields and sources remain authoritative;
- cache expiration and unavailable states work;
- startup seed/RAG preparation remains idempotent;
- `/health`, `/ready`, and safe deployment status work;
- public review/watchlist UX remains read-only;
- no credentials or session material appear in responses or logs.

## 4. Phase 16 required suites

### Authentication and identity

Test valid and invalid JWTs, issuer/audience/expiration/signature, verified email, inactive/deleted accounts, identity collisions, pending invitations, refresh rotation, logout, and administrator MFA assurance.

### BFF and cookies

Test explicit route allowlisting, rejection of arbitrary targets, safe header forwarding, access-token attachment, refresh-cookie isolation, anonymous-cookie propagation, refresh success/failure, and browser storage absence.

### Anonymous isolation

```text
browser A creates and reads report
browser B receives 404
expired session receives 404
cleanup removes expired data
seeded public report remains
```

### Ownership

Test User A versus User B, strict private visibility, organization roles, removed members, disabled/deleted organizations, final-owner protection, and safe `404` behavior.

### Route authorization

Test monitoring, discovery, evaluation, review, document/RAG ingestion, credentials, audit, and Vast routes for anonymous, ordinary user, organization role, and platform administrator actors.

### Quotas

Test exact limit, exceeded limit, period reset, plan differences, saved-resource limits, deletion releasing capacity, and concurrent first-use behavior on PostgreSQL.

### Account lifecycle

Test bounded export, exclusion of foreign/sensitive data, deletion confirmation, final-owner blocking, immediate access revocation, dry-run cleanup, retention, consent versioning, and password recovery callback.

### Frontend E2E

Test anonymous demo, login/BFF/refresh/logout, account, thesis CRUD, organizations/memberships, recovery, consent, MFA, mobile layout, keyboard focus, and no private-content flash.

A route-status smoke script is useful but is not full browser E2E coverage.

## 5. Current Phase 16 branch coverage

Present:

- private report isolation;
- final owner protection;
- quota boundary;
- valid/invalid JWT cases;
- anonymous report isolation and expiration;
- strict private visibility with stale organization IDs;
- public-demo durable mutations blocked for anonymous visitors and allowed for authenticated hybrid users;
- watchlist resource limit;
- server-owned consent versions;
- retention anonymization/deletion;
- BFF allowlist/cookie-filter contract check;
- frontend route smoke foundation.

Still required before completion:

- browser refresh/logout tests;
- PostgreSQL quota concurrency;
- deployed recovery callback verification;
- full MFA flow;
- tenant knowledge isolation;
- deployed Supabase verification.

Phase 16 remains `In Progress` until the full contract passes.

## 6. Phase 17 validation

Test atomic job claims, leases, heartbeat, abandoned recovery, retry/dead-letter, idempotency, cancellation, worker authentication, tenant isolation, graceful shutdown, and cost/concurrency limits.

## 7. Phase 18 validation

Test durable objects, document versions, worker ingestion, tenant-filtered retrieval, citation lineage, deletion/tombstones, re-embedding migration, rollback, and retrieval evaluation.

## 8. Phase 19 validation

Test distributed limits, security headers, proxy/SSRF/CSRF protections, centralized redaction, trace correlation, backup restore, migration rollback, scans, load, accessibility, browser, PostgreSQL, and failure recovery.

## 9. Phase 20 validation

Test analytics consent, notification preferences, signed webhooks, delivery retry, schedules/timezones, entitlements, billing event idempotency, organization seats, and data export/deletion integration.

## 10. Phase 21 validation

Test provider routing, model/prompt versioning, evaluation promotion/rollback, deterministic-field preservation, citation support, source-instruction defenses, tenant privacy, cost budgets, feedback controls, and compute cleanup.

## 11. CI expectations

CI should progressively include:

- PostgreSQL 16;
- migrations;
- compile and pytest;
- runtime preparation;
- frontend type/build;
- auth/BFF tests;
- browser tests;
- Compose validation;
- failure artifacts;
- later worker, retrieval, security, accessibility, and load checks.

Real production credentials and paid provider actions are never required in CI.

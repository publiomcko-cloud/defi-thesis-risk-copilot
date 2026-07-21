# Phase 16 Execution Plan

This document breaks V1 Phase 16 into execution sub-phases. It does not replace the authoritative contract in [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md); it turns the remaining blockers into ordered, testable work packages.

Status: **In Progress**

Branch:

```text
agent/v1-phase-16-identity-ownership
```

Permanent constraints:

- preserve the Phase 15 public-safe demo baseline;
- do not merge to `main` until all Phase 16 gates pass;
- do not add wallets, signing, custody, trade execution, capital allocation, or personalized financial advice;
- keep deterministic risk scoring, source provenance, missing-data visibility, and public safety behavior authoritative;
- keep browser access through same-origin Next.js auth/BFF routes.

---

## Execution Order

```text
16A -> 16B -> 16C -> 16D -> 16E -> 16F -> 16G -> 16H
```

Each sub-phase must end with:

- implementation or explicit external blocker;
- focused tests for the changed behavior;
- documentation updates;
- validation commands from [`testing.md`](testing.md) scaled to the change;
- a commit on the same Phase 16 branch when requested.

---

## 16A — Admin MFA Usable Workflow

Status: **Complete locally — deployed Supabase verification remains in 16G**

Goal: make administrator MFA more than an `aal2` backend check.

Scope:

- add frontend account-security controls for MFA enrollment/challenge status;
- add same-origin Next.js auth route handlers that call supported Supabase MFA APIs server-side;
- support enrollment, challenge/verify, factor list, unenrollment, and clear error states;
- keep MFA secrets, QR material, access tokens, and refresh tokens out of browser storage and logs;
- keep backend admin-route enforcement based on verified Supabase assurance claims, not frontend state.

Acceptance:

- platform admin without required `aal2` receives controlled `403`;
- admin with verified `aal2` can use admin routes;
- ordinary users are not blocked from ordinary routes when admin MFA is required;
- UI supports enrollment/challenge/unenrollment without placeholder-only copy;
- tests cover backend enforcement and frontend route-handler failure/success boundaries where provider calls can be mocked.

Remaining external gate:

- deployed Supabase MFA configuration and TOTP flow must be manually verified.

Local evidence:

- `/account/security` supports TOTP enrollment, factor selection, challenge/verification, and unenrollment;
- same-origin route handlers call Supabase Auth with the server-held access token and rotate HttpOnly session cookies after verification;
- factor-list responses are sanitized and MFA setup material is held only in transient page state;
- backend tests prove administrator `aal1` denial, administrator `aal2` access, and ordinary-user `aal1` access;
- provider and HTTP route-handler tests cover success, provider failure, cookie isolation, and cross-origin rejection.

---

## 16B — Organization Knowledge Metadata and Retrieval Boundary

Goal: define Phase 16 organization knowledge ownership without pretending Phase 18 tenant vector storage exists.

Scope:

- add or harden organization-owned knowledge metadata where appropriate;
- ensure global discovery/review/ingestion remains platform-admin controlled;
- ensure organization knowledge actions require owner/admin membership;
- make retrieval use server-derived scope only;
- prevent request input from selecting another tenant's knowledge;
- keep current curated local JSON RAG documented as global/public until Phase 18.

Acceptance:

- public curated demo knowledge remains public;
- organization knowledge metadata is hidden from non-members and removed members;
- disabled/deleted organizations lose knowledge access;
- retrieval cannot be tenant-switched by user input;
- docs clearly state that durable tenant-specific vector storage remains Phase 18.

---

## 16C — Migration, Foreign-Key, and Index Review

Goal: make the Phase 16 schema deliberately safe for ownership, organization, anonymous, and quota queries.

Scope:

- review `20260720_0008_add_identity_ownership_quotas.py` against current models;
- add practical foreign keys for user, organization, membership, anonymous-session, and consent references where compatible with existing Phase 15 data;
- add compound indexes for owner/deleted, organization/visibility/deleted, anonymous/expires, and quota period access;
- keep downgrade/upgrade behavior valid;
- document any intentionally omitted constraint and why.

Acceptance:

- Alembic upgrade from a Phase 15 database preserves seeded public reports and watchlists;
- downgrade/upgrade passes locally;
- PostgreSQL migration path passes;
- common list/detail authorization queries are supported by indexes;
- no destructive reset is required.

---

## 16D — Audit Coverage and Security Event Logging

Goal: record meaningful security and lifecycle events without leaking secrets.

Scope:

- audit organization creation/update/deletion;
- audit membership add/update/remove and final-owner protection failures where useful;
- audit administrator credential changes and platform-sensitive operations;
- audit account deletion/export and security-sensitive consent/MFA events;
- redact emails, tokens, cookie values, provider secrets, and raw request bodies where sensitive.

Acceptance:

- privileged and lifecycle events create bounded audit records;
- exported account data excludes sensitive internal audit metadata;
- public/anonymous users cannot read audit data;
- tests prove redaction and authorization behavior.

---

## 16E — PostgreSQL Concurrency and Phase 15 Data Validation

Goal: prove quota and resource-limit behavior under realistic PostgreSQL concurrency.

Scope:

- add PostgreSQL integration tests or scripts for quota first-use races;
- test saved-thesis and watchlist count limits under concurrent create attempts;
- test exact-limit success and next-request `429`;
- test deletion releases resource capacity;
- test Phase 15 seeded data remains public and readable after Phase 16 migrations.

Acceptance:

- no unhandled unique-constraint errors;
- concurrent first-use either succeeds within limits or returns controlled quota responses;
- Phase 15 seeded reports and public read-only demo behavior remain intact.

---

## 16F — Full Browser E2E for Phase 16 Workflows

Goal: replace route-smoke confidence with real browser workflow coverage.

Scope:

- add Playwright or equivalent browser tests;
- cover anonymous analysis/report retrieval and second-browser isolation;
- cover login through the BFF, session check, refresh behavior, and logout;
- cover thesis CRUD and analyze-from-thesis;
- cover organization creation, membership management, and removed-member access loss;
- cover recovery callback path with mocked/provider-test configuration where possible;
- cover no private-content flash before session resolution.

Acceptance:

- browser tests run locally and in CI-compatible mode;
- screenshots/traces are available on failure;
- tests do not require real paid services or live capital execution;
- deployed Supabase/browser behavior still remains a manual external gate until verified.

---

## 16G — Deployed Supabase Verification

Goal: verify the managed-identity system on real deployed domains.

Scope:

- configure Supabase Site URL and redirect allowlist;
- verify signup email and verified-email enforcement;
- verify login, cookie creation, BFF forwarding, refresh rotation, and logout;
- verify recovery email, callback/code exchange, password update, and expired-link behavior;
- verify admin MFA denial and allow states;
- verify Vercel-to-Render cookie and CORS behavior;
- record exact deployed URLs, dates, and result notes in docs.

Acceptance:

- all deployed identity/recovery/MFA flows are manually verified;
- no tokens appear in browser storage, URLs after callback completion, logs, deployment status, or frontend payloads;
- known external limitations are documented.

---

## 16H — Final Legal, Documentation, and Release Gate

Goal: make the repository truthful and ready for Phase 16 completion or an explicit external block.

Scope:

- ensure terms/privacy pages are marked reviewed or still blocked for qualified legal review;
- update `current_state.md`, `development_plan.md`, `architecture.md`, `deployment.md`, `testing.md`, `README.md`, `CHANGELOG.md`, and the Phase 16 contract;
- run the complete validation suite;
- verify no secrets or runtime artifacts are staged;
- produce final completion report.

Acceptance:

- Phase 16 is marked **Complete** only if every contract gate passes;
- otherwise Phase 16 remains **Blocked** or **In Progress** with exact remaining external blockers;
- branch is ready for PR review but not merged without explicit instruction.

---

## Standard Validation Set

Run the full set at final gate and after any high-risk sub-phase:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py

cd ../frontend
npm ci
npm run lint
npm run test:bff
npm run build
npm run test:e2e

cd ..
docker compose config
docker compose -f docker-compose.production.yml config
```

Add PostgreSQL concurrency, browser, and deployed Supabase checks in the sub-phases that require them.

# Changelog

All notable changes to DeFi Thesis & Risk Copilot are documented here.

## Unreleased — V1 Product Hardening

### Phase 17 Durable Jobs and Hybrid Workers

- Correction pass completed locally: added supervised long-running heartbeats/cancellation, immutable
  attempt lease horizons, exact job schemas, recovery maintenance, database report-reference
  artifacts, completed-only report links, and durable Vast request reconciliation boundaries.

- Added durable tenant-scoped jobs, attempts, events, artifacts, capacity reservations, scoped worker credentials, PostgreSQL-safe leases, retries, cancellation, and retention.
- Added asynchronous authenticated analysis with idempotent report persistence and a trusted outbound-only worker profile.
- Added an administrator-only, server-profiled Vast session job with dry-run defaults, cost reservation, session reconciliation, and idempotent cleanup.
- Added a private jobs workspace with status, progress, event detail, cancellation, safe error guidance, and authorized report links.
- Added safe job/event/artifact account export and account-deletion handling for job results and incomplete outputs.
- Added migration, provider fake, lifecycle, browser BFF, Compose, and retention validation. Hosted workers and real provider rentals remain externally unverified.
- Added cooperative executor cancellation, fixed per-job attempt horizons, side-effect-free recovery dry runs, durable provider-cost reservations, immediate job revocation on organization access loss, and server-owned retry decisions. Real Vast.ai rental remains fail-closed until a verified adapter profile exists.

### Phase 17A Durable Job Foundation

- Added durable PostgreSQL-backed job, attempt, event, worker, worker-credential, and artifact schemas with Phase 16 ownership, tenant, idempotency, cost, and retention constraints.
- Added the closed job-transition service and ordered, redacted append-only job events.
- Added audited platform-admin worker registry and one-time worker credential issuance, rotation, revocation, scoped verification, and production fail-closed configuration.
- Added job/artifact disposal for account and organization deletion plus retention cleanup for terminal jobs, old events, incomplete artifacts, and expired worker credentials.
- Added SQLite migration evidence, PostgreSQL migration-cycle validation, lifecycle, credential, tenancy, retention, and configuration tests. Queue submission, worker claiming/execution, and async analysis remain later Phase 17 slices.

### Phase 16 Identity, Ownership, and Quotas

- Added Supabase Auth JWT validation through JWKS with issuer, audience, expiration, subject, email, and signature checks.
- Added local user synchronization, explicit platform roles, account status, verified-email enforcement, and production fail-closed authentication configuration.
- Added Next.js same-origin BFF and HttpOnly access/refresh/expiration cookie foundations.
- Added organization and membership models with owner/admin/member/viewer roles, pending invitations, and final-owner protection.
- Added centralized authorization policies for private, organization, public-demo, anonymous, deleted, and expired resources.
- Added ownership fields for analysis requests, reports, and watchlists plus saved theses.
- Added account export/deletion, consent records, anonymous sessions, daily quotas, saved-resource limits, and retention cleanup.
- Added administrator MFA assurance checking foundation.
- Added account, thesis, and organization frontend foundations.
- Expanded JWT, anonymous isolation, quota, organization, and cleanup tests.
- Hardened the Phase 16 BFF allowlist and cookie forwarding so browser calls use same-origin route handlers without forwarding Supabase refresh/session cookies to FastAPI.
- Replaced deployment-only public mutation blocking with actor-aware dependencies for durable user mutations and platform-admin routes.
- Tightened private versus organization resource policy semantics, added server-owned consent versions, and added a recovery callback/code-exchange foundation.
- Completed the local Phase 16A TOTP workflow with same-origin Supabase enrollment, challenge/verification, factor management, HttpOnly session rotation, and mocked provider/route tests.
- Added Phase 16B organization knowledge-source metadata, human-approval provenance, active-membership authorization, and a server-derived public-only RAG retrieval boundary pending Phase 18 tenant storage.
- Completed Phase 16C local schema hardening with ownership/organization/anonymous-session/saved-thesis/consent foreign keys, compound authorization and quota indexes, Phase 15 data-preservation tests, and a clean PostgreSQL migration-cycle check.
- Completed Phase 16D local lifecycle/security audit hardening with bounded redaction, organization/account/consent/MFA events, administrator-only audit access, and a server-only BFF MFA audit channel.
- Completed Phase 16E PostgreSQL quota/resource concurrency validation and Phase 15 migrated public API regression coverage; CI now enables the guarded PostgreSQL integration suite, and development demo ownership now respects the production foreign-key contract.

Phase 16 is **Complete and merge-ready**. Its implementation record is archived in `docs/archive/v1_phase_16/`; deferred deployed-provider and qualified legal release validation is tracked as final V1 Phase 22 work.

### Security

- Public hosted visitors receive a common/anonymous restricted identity instead of implicit administrator access.
- Public discovery, monitoring, evaluation, review, RAG, document, watchlist, credential, audit, and Vast.ai mutations remain restricted.
- Public compute endpoints use bounded request schemas and per-client limiting.
- Provider and session secrets remain server-side.
- Phase 16 documentation now explicitly requires effective BFF route allowlisting, cookie filtering, actor-based hybrid authorization, strict visibility semantics, concurrency-safe quotas, complete recovery, server-owned consent versions, usable MFA, and tenant knowledge boundaries.

### Backend

- Added API root, process liveness, and database/RAG readiness endpoints.
- Added request IDs, request-duration logging, and safe exception logging.
- Added deterministic demo seeding and RAG-index generation during hosted startup.
- Updated Render to use `/ready` for health checks.
- Enforced market-cache expiration and update-in-place behavior.
- Added PostgreSQL migration/test foundations in CI.

### Frontend

- Made the live demo the primary product entry point.
- Added public-aware navigation, footer, states, badges, responsive behavior, and reduced-motion support.
- Added cold-start retry/readiness flows and shared-demo privacy guidance.
- Converted review and watchlist workflows to read-only hosted demonstrations.
- Protected direct credential, audit, and Vast.ai pages in public mode.
- Clarified financial units and advanced controls.
- Added clickable sources and Markdown copy/download.
- Added Phase 16 authentication/account/thesis/organization foundations.

### Documentation

- Archived the Phase 16 contract, execution plan, and deployment evidence under `docs/archive/v1_phase_16/` after implementation completion.
- Updated `docs/future_phase_contracts.md` with detailed contracts for Phases 17–22, including final V1 release validation.
- Added `docs/agent_execution_guide.md` so future work can use short prompts safely.
- Rebuilt the authoritative development plan around phase contracts and dependency gates.
- Updated current state to separate deployed `main` from branch-only Phase 16 work.
- Revised architecture, deployment, testing, and README to match the contracts and current implementation audit.
- Moved remaining live-provider and qualified legal launch gates to final V1 Phase 22 instead of presenting them as completed production behavior.

## 0.1.0 — Technical MVP and Portfolio Expansion

### Added

- FastAPI and Next.js full-stack MVP.
- SQLAlchemy/Alembic persistence and Docker Compose.
- Curated RAG, market-data adapters, deterministic scoring, structured reports, and Markdown export.
- Optional LLM synthesis with deterministic fallback.
- Discovery, evaluation, review, human-approved RAG ingestion, simulation, watchlists, alerts, options, ML groundwork, and HPC templates.
- Admin/common access-control foundation, encrypted provider credentials, audit logs, and Vast.ai dry-run/manual warm-up.
- Deterministic demo data, example reports, and Vercel/Render/Supabase deployment preparation.

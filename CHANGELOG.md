# Changelog

## Phase 19 — In Progress

- Opened the production operations and security planning phase after Phase 18
  merged into `main`.
- Phase 19 begins with observability, readiness checks, and controlled
  shadow-mode validation; it does not activate all durable knowledge flags.

## Phase 18 — Merged

- Added generation-specific embedding rows, exact active-generation retrieval,
  same-profile rollback, and a reversible migration.
- Connected guarded durable retrieval to authenticated analysis with server-derived
  public/private/organization scope; anonymous analysis remains public-only and
  JSON remains the fallback.
- Made curated corpus import convergent and compensating, added retrieval quality
  metrics, pgvector preflight, and safe private knowledge metadata in account export.
- Hardened curated-object verification for checksum-free Supabase HEAD responses,
  made compensation corpus-transaction-wide, rejected unsafe deterministic-ID
  collisions, and added declared-lineage expected-empty retrieval evaluation.
- Documented that migration `0021` downgrades fail closed after multi-generation
  data exists; production rollback after activation uses feature flags, not a
  destructive schema downgrade.
- Made curated-object ownership tracking race-safe, added committed operator
  import compensation, and extended convergent repair to validate chunk content,
  metadata, deterministic vectors, and indexed PostgreSQL vector population.
- Phase 18 merged into `main` through PR #4. Its archival record preserves
  validation, correction, migration, and cutover evidence. Production
  storage-policy and final cutover evidence remain Phase 22 work.

All notable changes to DeFi Thesis & Risk Copilot are documented here.

## Unreleased — V1 Product Hardening

### Phase 18A Production RAG Foundation

- Added reversible durable source, document, immutable version, and chunk
  tables while preserving the existing public JSON RAG metadata and runtime
  path.
- Added a disabled-by-default private Supabase Storage abstraction with
  server-derived lineage keys, create-only writes, bounded reads, idempotent
  deletion, sanitized failures, and an in-memory test backend.
- Added server-derived public/private/organization knowledge authorization
  without a platform-admin organization bypass.
- Registered the exact `document.ingest.v1` job contract while keeping normal
  submission and execution disabled until the worker-ingestion slice.
- Added SQLite rollback/data-preservation and PostgreSQL tenant-isolation
  coverage, plus Supabase Storage metadata and signed-path contract coverage.
  Phase 18A is complete; Phase 18 remains an implemented foundation, not
  complete.

### Phase 18B Source/Document API and Private Upload

- Added authenticated, server-scoped knowledge source/document/version APIs and
  bounded multipart uploads for allowlisted text, Markdown, HTML, and PDF files.
- Added checksum, media-type, filename, and size validation; create-only private
  object writes; metadata-only responses; and database-failure object compensation.
- Added source approval/upload audit events plus account and organization
  tombstones for durable knowledge records. Storage, ingestion, and retrieval
  remain disabled by default; Phase 18 is not complete.

### Phase 18C Durable Ingestion Executor

- Added server-owned, feature-gated `document.ingest.v1` submission and Phase 17
  worker execution for approved immutable document versions.
- Added bounded text/Markdown, HTML, and PDF extraction, deterministic
  normalization/chunking, checksum verification, retry-safe partial cleanup,
  and transactional version activation.
- Generic durable-job submission cannot queue ingestion. Storage, ingestion,
  embeddings, and retrieval remain disabled by default until deployment and
  later Phase 18 gates are completed.

### Phase 18D Versioned pgvector Embeddings

- Added a reversible pgvector migration with a local deterministic 384-dimension
  profile, immutable generation records, portable vector metadata, and a
  PostgreSQL HNSW cosine index.
- Added server-owned `document.embed.v1` worker jobs for approved ready document
  versions, including idempotency, dimension/model validation, retry/cancel
  cleanup, and atomic generation activation.
- No external embedding provider is supported, so private content remains in the
  controlled worker process. Embeddings and retrieval stay disabled by default.

### Phase 18E Tenant-safe Shadow Retrieval and Citations

- Added a reversible privacy-safe retrieval-event table and an authenticated,
  disabled-by-default pgvector shadow retrieval endpoint.
- Added server-derived public/private/active-organization predicates before
  ranking; deleted, unapproved, non-current, and corrupt-lineage chunks are
  excluded.
- Added exact source/document/version/chunk checksum citations and event
  metadata without raw query or chunk-content logging. Analysis reports still
  use the curated JSON RAG path; no durable retrieval cutover has occurred.

### Phase 18F Knowledge Lifecycle Operations

- Added atomic document-version rollback, completed embedding-generation
  promotion/rollback, and version-level active embedding-profile metadata.
- Added immediate tombstone revocation with idempotent, retryable physical
  cleanup tasks for private originals and derived chunks/vectors, plus a bounded
  cleanup CLI with dry-run support.

### Phase 18G Public Corpus Migration and Guarded Cutover

- Added an operator-only, idempotent importer for checked-in curated Markdown
  that creates approved public immutable source, version, chunk, object, and
  local deterministic embedding lineage without accepting discovered or tenant
  content.
- Added durable-public retrieval comparison metrics in CI and a weekly scheduled
  workflow, plus an opt-in pgvector public report path with automatic local JSON
  fallback. Both the importer and the primary path remain disabled by default.

### Phase 18H Knowledge Workspace and Operational Readiness

- Added an authenticated source/document/version workspace, safe lifecycle
  actions, exact durable citation lineage in report sources, and an
  administrator-only aggregate readiness endpoint.
- Added an explicit private-storage probe and a deployment runbook. It remains
  disabled/non-mutating by default; live Supabase policy and cutover validation
  are not represented as complete until Phase 22 evidence is recorded.

### Phase 17 Durable Jobs and Hybrid Workers

- Correction pass completed on `main`: added supervised long-running heartbeats/cancellation, immutable
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

Phase 16 is **Complete on main**. Its implementation record is archived in `docs/archive/v1_phase_16/`; deferred deployed-provider and qualified legal release validation is tracked as final V1 Phase 22 work.

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

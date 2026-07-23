# Architecture — DeFi Thesis & Risk Copilot

This document defines the system architecture and permanent trust boundaries. Phase-specific requirements live in:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`future_phase_contracts.md`](future_phase_contracts.md)
- [`current_state.md`](current_state.md)

---

## 1. Architecture goals

The system is designed for:

- deterministic, explainable risk analysis;
- source-grounded research and citation provenance;
- visible missing data and uncertainty;
- optional model assistance after retrieval and scoring;
- human approval before new knowledge becomes trusted;
- secure identity, ownership, and tenant isolation;
- server-side credentials and cookies;
- safe anonymous public-demo access;
- durable asynchronous work and storage in later phases;
- incremental deployment from portfolio demo to commercial product.

---

## 2. Permanent boundaries

The application must not implicitly:

- connect wallets;
- request private keys or seed phrases;
- sign transactions;
- custody assets;
- execute trades;
- allocate capital;
- promise returns;
- provide personalized financial advice;
- hide missing data;
- auto-trust discovered sources;
- expose credentials or session secrets;
- let model output replace deterministic risk fields.

---

## 3. Deployed Phase 15 architecture

```text
Browser
  -> Vercel Next.js frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL

Render startup
  -> Alembic migrations
  -> deterministic public demo seed
  -> local curated RAG index build
  -> Uvicorn
```

The deployed `main` branch currently represents the Phase 15 public-safe baseline unless a later phase is explicitly merged and deployed.

Live endpoints:

- frontend: `https://defi-thesis-risk-copilot.vercel.app`;
- backend: `https://defi-thesis-risk-copilot.onrender.com`;
- liveness: `/health`;
- readiness: `/ready`;
- safe deployment status: `/api/deployment/status`;
- OpenAPI: `/docs`.

---

## 4. Phase 16 target architecture

```text
Browser
  -> Vercel Next.js application
     -> /api/auth/* server route handlers
     -> /api/backend/* BFF
     -> HttpOnly access/refresh/expiry cookies
     -> HttpOnly anonymous-session cookie
  -> Render FastAPI API
     -> Supabase JWKS token verification
     -> application user synchronization
     -> actor and authorization policies
     -> owned/organization/anonymous resources
     -> durable quota records
  -> Supabase PostgreSQL
```

### Trust boundary

- Browser JavaScript never receives access or refresh tokens.
- Next.js owns browser session cookies and server-side token refresh.
- FastAPI verifies access tokens independently.
- Supabase claims establish identity only.
- Application database fields establish platform role, account status, plan, ownership, and organization membership.
- Resource policies derive tenant scope server-side.
- Organization knowledge metadata is database-owned and membership-scoped, but tenant documents and vectors are not stored in Phase 16.

### Ownership persistence integrity

Phase 16C adds database foreign keys for resource owner, organization, and anonymous-session links, plus saved-thesis owner and consent-user records. Nullable resource links use `SET NULL`; required saved-thesis/consent links use `RESTRICT`. Compound indexes support owner/deleted, organization/visibility/deleted, anonymous/expires, membership, and quota-period access paths. Polymorphic quota subjects and immutable audit actors intentionally remain application-managed references; the Phase 16 contract records why.

When authentication is disabled outside the public demo, the local `demo_admin` context is materialized as a database user before it can create owned resources. This prevents development-only convenience identities from bypassing the same foreign-key integrity expected in PostgreSQL production-like validation.

### Lifecycle audit boundary

The application records bounded audit events for privileged and lifecycle operations. Metadata is recursively redacted and size-limited before persistence; emails, tokens, cookies, credentials, verification codes, and raw request bodies are never retained. Only administrators can query the full operational log. Account export exposes a user-visible projection without internal metadata. Successful Next.js MFA route handlers may report fixed event types to FastAPI only through a server-only BFF shared secret and authenticated user token; the secret is not browser-visible.

### BFF boundary

The BFF must:

- use explicit route-family allowlisting;
- reject arbitrary hosts, schemes, ports, paths, and path traversal;
- forward only safe headers;
- attach the access token through `Authorization`;
- forward only backend-required cookies, such as the anonymous session;
- never forward refresh-token cookies to Render;
- propagate anonymous-session cookies safely;
- clear auth cookies after refresh failure.

The current Phase 16 branch contains the BFF foundation with explicit backend route-family allowlisting and anonymous-cookie-only backend forwarding. Full deployed browser refresh/logout verification remains a completion gate documented in the Phase 16 contract.

---

## 5. Product domains

```text
Next.js frontend/BFF
  -> landing and guided demo
  -> authentication and session management
  -> account/security
  -> strategy analysis
  -> reports/export
  -> simulator/options
  -> theses
  -> organizations/memberships
  -> watchlists/alerts
  -> discovery/review/admin tools

FastAPI control plane
  -> request validation
  -> identity synchronization
  -> actor/authorization policies
  -> analysis orchestration
  -> deterministic risk scoring
  -> market data/cache
  -> report persistence
  -> simulation/options
  -> organizations/theses/watchlists/alerts
  -> quotas/account/consent/retention
  -> discovery/evaluation/review
  -> knowledge ingestion
  -> credentials/audit/Vast controls

Persistence
  -> Supabase PostgreSQL hosted
  -> PostgreSQL/SQLite local
  -> curated Markdown sources
  -> local JSON RAG index in current phases
```

---

## 6. Analysis architecture

```text
bounded strategy input
  -> strategy parsing
  -> protocol/entity detection
  -> approved retrieval
  -> market-data adapters/cache
  -> explicit unavailable/missing state
  -> deterministic risk scoring
  -> stress scenarios
  -> structured report
  -> optional LLM wording synthesis
  -> owned persistence
  -> authorized rendering/export
```

Authoritative fields include:

- risk rating and score;
- risk drivers;
- market values;
- assumptions;
- missing data;
- source metadata;
- disclaimer.

Model output may not silently override them.

---

## 7. Knowledge trust architecture

```text
discovery
  -> filtering/normalization
  -> stable-key deduplication
  -> deterministic evaluation
  -> human review
  -> approved_for_rag
  -> explicit authorized ingestion
  -> durable source/version in Phase 18
  -> retrieval index
```

Current global ingestion may generate curated Markdown and refresh the public-curated local index. Phase 16 organization sources persist provenance and approval metadata only. The analysis service derives retrieval scope from authenticated membership, but organization-tagged chunks remain blocked because tenant storage is disabled. Phase 18 replaces runtime/local authority with object storage, versioned documents/chunks, and tenant-filtered vector retrieval.

No automatically discovered content becomes trusted without explicit approval.

---

## 8. Actor architecture

### Anonymous visitor

- reads public seeded content;
- runs bounded compute;
- owns temporary resources through a server-generated anonymous session;
- cannot run privileged mutations.

### Authenticated user

- owns private resources;
- uses quotas and account lifecycle;
- participates in organizations.

### Organization roles

```text
owner
admin
member
viewer
```

Organization access requires:

- active, non-deleted organization;
- active membership;
- allowed role;
- resource visibility equal to `organization`.

### Platform administrator

Uses explicit platform-admin routes. Organization role does not grant platform-admin access. Supabase metadata does not grant platform-admin access.

When configured, platform administrators require MFA assurance.

---

## 9. Resource visibility architecture

```text
private
organization
public_demo
```

### Private

Owner-only. A stale `organization_id` does not grant organization access.

### Organization

Requires active organization and membership. Client input cannot assign arbitrary organization scope.

### Public demo

Globally readable seeded/safe content. Public mutation remains blocked.

### Anonymous private

Requires matching active anonymous session and unexpired resource.

Every list and detail query must enforce the same policy. Export and mutation routes are not exceptions.

---

## 10. Public and authenticated coexistence

The desired product can support both anonymous and authenticated actors in one deployment.

Authorization is therefore actor-based:

```text
operation + actor + role + ownership + organization + visibility + state
```

It must not be reduced to:

```text
PUBLIC_DEMO_MODE=true -> block every mutation
```

A deployment-mode flag may enable anonymous demo behavior, but authenticated user and administrator capabilities still require explicit actor policies.

---

## 11. Identity and session architecture

### Managed identity

- Supabase Auth for credential and recovery flows;
- FastAPI JWKS verification;
- normalized local application user;
- database-owned roles and plans;
- collision-safe identity linking;
- verified email;
- optional/required MFA.

### Local development

`legacy_local` may support controlled development only. Production rejects it.

### Credentials

Provider credentials:

- remain server-side;
- use encrypted storage or environment configuration;
- never return raw values;
- are redacted from logs/audit metadata;
- require explicit platform-admin authorization.

---

## 12. Quota architecture

Two distinct concepts:

### Product quotas

Persistent per-period limits for analysis, simulation, options, market data, and saved-resource counts.

### Network rate limits

Request-frequency protection. Current Phase 15 limiter is in-process; Phase 19 supplies distributed enforcement.

Quota check/increment must be atomic. A row lock cannot protect a missing first-use row; PostgreSQL upsert or retry logic is required.

Phase 16E validates the controlled retry plus quota-row-lock design against PostgreSQL: concurrent first use yields a permitted request and a controlled `429` at the configured limit, while the same durable lock serializes saved-thesis and watchlist count checks. The test suite also verifies that soft deletion releases user resource capacity.

---

## 13. Account and retention architecture

Account lifecycle:

```text
active
  -> inactive/deletion requested
  -> deleted/disabled immediately
  -> retention cleanup
  -> identifiers deleted or anonymized
```

Required controls:

- exact confirmation;
- recent authentication where supported;
- final organization-owner protection;
- immediate access revocation;
- session clearing;
- bounded export;
- no secret export;
- deterministic cleanup/dry-run;
- explicit private-resource disposition;
- redacted audit retention.

---

## 14. Runtime reliability

Startup:

```text
alembic upgrade head
  -> scripts.prepare_runtime
  -> uvicorn
```

Health:

- `/health` — process liveness;
- `/ready` — database and required runtime resources;
- `/api/deployment/status` — safe UI metadata.

Request middleware provides request ID, method, path, status, duration, and `X-Request-ID` response header without logging secrets.

---

## 15. Market-data architecture

The cache:

- keys by adapter/query identity;
- updates current rows rather than appending indefinitely;
- removes duplicates;
- enforces expiration;
- uses only unexpired fallback data;
- returns explicit unavailable state when no valid data exists.

Market data may be delayed, partial, cached, simulated, or manually supplied and must be labeled accordingly.

---

## 16. Phase 17 target — jobs and workers

```text
API/control plane
  -> PostgreSQL job state
  -> local/cloud worker outbound claim
  -> lease/heartbeat/progress
  -> durable artifact/result
```

Key invariants:

- scoped worker auth;
- atomic claim;
- idempotency;
- retry/dead-letter;
- cancellation;
- cost/concurrency controls;
- no inbound local-worker ports.

See [`future_phase_contracts.md`](future_phase_contracts.md).

### Phase 17A–17C implemented foundation

PostgreSQL now persists job, attempt, event, worker, worker-credential, and artifact metadata.
Job transitions are restricted to a closed service, events are append-only and sequenced, and
worker tokens use a separate hashed credential domain rather than a browser or user token. The
control plane now exposes authenticated, tenant-filtered job submission, list/detail, events,
cancellation, and admin linked replay. A unique scoped idempotency boundary and lockable capacity
reservation rows keep quota, user/organization/global/provider capacity, preallocated report IDs,
and the initial event transactional. The internal worker protocol now leases jobs with PostgreSQL
`SKIP LOCKED`, a monotonic lease generation, a hashed per-attempt token, durable attempt rows, and
bounded heartbeat/retry/cancellation recovery. It is excluded from the browser BFF. The optional
local worker is outbound-only and runs a fake deterministic executor; asynchronous analysis and
provider execution arrive in later Phase 17 slices. Account/organization deletion disposes of
affected jobs and artifacts, while retention expires credentials and terminal job material
according to configured policy.

---

## 17. Phase 18 target — durable RAG/storage

```text
approved source/upload
  -> object storage
  -> versioned document
  -> ingestion job
  -> durable chunks/embeddings
  -> tenant-filtered vector retrieval
  -> citation lineage
```

Runtime filesystem and global JSON indexes stop being authoritative.

---

## 18. Phase 19 target — operations/security

Adds:

- distributed rate limiting;
- WAF/security headers/CSRF/SSRF protections;
- centralized logs/errors/traces/metrics;
- request-job correlation;
- backups/restores;
- secret rotation;
- scanning;
- incident response;
- load/failure/browser/PostgreSQL testing.

---

## 19. Phase 20 target — commercial product

Adds privacy-conscious analytics, durable scheduling, notifications, entitlements, billing webhook processing, organization invitations/seats, support/status, and qualified legal review.

---

## 20. Phase 21 target — model/research expansion

Adds task-level provider routing, model/prompt registry, evaluation-before-promotion, regression datasets, prompt-injection defenses, controlled feedback, thesis/catalyst tracking, and worker-controlled ephemeral GPU tasks.

Deterministic risk and non-execution boundaries remain permanent.

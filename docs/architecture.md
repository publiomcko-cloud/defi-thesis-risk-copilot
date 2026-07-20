# Architecture — DeFi Thesis & Risk Copilot

## 1. Architecture Goals

DeFi Thesis & Risk Copilot is designed around:

- clear domain separation
- source-grounded research
- deterministic risk fields
- optional model synthesis after retrieval and scoring
- human approval before knowledge trust
- server-side credentials
- safe public defaults
- optional heavy compute
- an incremental path from portfolio deployment to a multi-user product

## 2. Current Hosted Architecture

```text
Browser
  -> Vercel Next.js frontend
  -> same-origin Next.js BFF route handlers
  -> Render FastAPI backend
  -> Supabase PostgreSQL

Render container
  -> Alembic migrations
  -> deterministic demo seed
  -> curated RAG index build
  -> Uvicorn API
```

Live endpoints:

- Frontend: `https://defi-thesis-risk-copilot.vercel.app`
- Backend: `https://defi-thesis-risk-copilot.onrender.com`
- Liveness: `/health`
- Readiness: `/ready`
- Deployment metadata: `/api/deployment/status`
- OpenAPI: `/docs`

## 3. Product Domains

```text
Next.js Frontend
  -> landing and guided demo
  -> strategy analysis
  -> persisted reports and export
  -> simulator
  -> options analysis
  -> watchlist and alerts
  -> discovery/review workflow
  -> private admin tools

FastAPI Backend
  -> request validation and public safety dependencies
  -> analysis orchestration
  -> RAG retrieval
  -> market-data adapters and cache
  -> deterministic risk scoring
  -> report generation and persistence
  -> discovery and evaluation
  -> review queue and approved RAG ingestion
  -> simulation
  -> watchlist and alert rules
  -> options analysis
  -> identity and authorization
  -> provider credentials and audit logs
  -> Vast.ai lifecycle controls
  -> deterministic demo and deployment metadata

Storage
  -> Supabase PostgreSQL for hosted persistence
  -> SQLite or PostgreSQL locally
  -> curated Markdown knowledge base
  -> local JSON RAG index for the current deployment
  -> committed example reports
```

## 4. Analysis Flow

```text
strategy input
  -> bounded request validation
  -> protocol detection
  -> curated/hybrid retrieval
  -> public/manual market-data adapters
  -> cache or explicit unavailable state
  -> deterministic risk scoring
  -> stress scenarios
  -> structured report writer
  -> optional LLM wording synthesis
  -> persisted report
  -> browser rendering and Markdown export
```

Deterministic risk scoring, source metadata, missing data, market fields, and disclaimers remain authoritative.

## 5. Discovery and Knowledge Trust

```text
private/admin discovery trigger
  -> DefiLlama/manual collectors
  -> filtering and normalization
  -> stable-key deduplication
  -> discovered item
  -> deterministic evaluation
  -> human review
  -> approved_for_rag
  -> explicit private/admin ingestion
  -> curated Markdown
  -> RAG index refresh
```

Discovery, approval, and ingestion are separate states. No automatically discovered content becomes trusted without review.

RAG ingestion uses:

```text
refresh_pending
  -> ingested
```

or:

```text
refresh_pending
  -> refresh_failed
  -> retry
```

## 6. Public Safety Architecture

`PUBLIC_DEMO_MODE=true` creates three endpoint classes.

### Public read-only

- demo status and scenarios
- protocols
- reports
- discovery candidates
- review records
- knowledge-base ingestion metadata
- watchlists and alerts
- deployment status

### Public bounded compute

- strategy analysis
- market-data fetch
- simulation
- options analysis

These requests use:

- maximum payload sizes
- numeric bounds
- maximum list sizes
- per-client in-process rate limiting
- safe error responses

The in-process limiter is suitable for the current single-instance demo. A distributed limiter is planned for multi-instance production.

### Private/admin mutations

Blocked in the hosted public environment:

- demo reseeding/reset
- monitoring runs
- discovery runs
- evaluation creation
- review decisions
- RAG ingestion
- document ingestion
- watchlist/alert mutations
- provider credentials
- audit logs
- Vast.ai lifecycle operations

When authentication is disabled locally, the application can use a local demo administrator. When authentication is disabled in the public deployment, visitors receive a `common` read-only identity instead.

## 7. Identity and Credential Architecture

Current roles:

```text
admin
common
```

Current private/local authentication is bearer-token based. Production managed identity is planned.

Provider credential model:

```text
api_credentials
  id
  provider
  name
  secret_encrypted
  secret_last4
  enabled
  created_by
  created_at
  updated_at
  last_used_at
```

Rules:

- secrets never return to the browser
- secrets are never logged
- database storage requires encryption configuration
- audit metadata is redacted
- public credential reads and writes are denied by the public common identity
- a production secret manager/KMS remains a future improvement

## 8. Runtime Reliability

Startup:

```text
alembic upgrade head
  -> scripts/prepare_runtime.py
     -> idempotent synthetic seed
     -> RAG index generation
  -> uvicorn
```

Health model:

- `/health`: process liveness only
- `/ready`: database plus public RAG readiness
- `/api/deployment/status`: safe operational metadata for the UI

Request middleware adds:

- request ID
- status code
- request duration
- response `X-Request-ID`

Unhandled exceptions are logged server-side and return a generic error with request ID.

## 9. Market-Data Cache

The current cache:

- keys by adapter and query identity
- updates an existing current record instead of appending indefinitely
- removes duplicate rows for the same key
- enforces `expires_at`
- uses only unexpired fallback data
- reports unavailable data explicitly when no valid cache exists

## 10. Vast.ai Provider

```text
admin request
  -> role and public-mode checks
  -> cost/runtime/GPU constraints
  -> offer search
  -> rental
  -> startup polling
  -> OpenAI-compatible health check
  -> test task
  -> cleanup/destroy
  -> audit events
```

The provider is disabled and dry-run by default. Automatic rental for normal reports is not enabled.

## 11. Frontend Architecture

Public mode:

- hides administrator navigation
- provides guided scenario paths
- renders review/watchlist as read-only
- shows shared-database privacy guidance
- handles Render cold starts with retry/readiness actions
- presents percentages and financial units explicitly
- supports keyboard focus and reduced motion

Private/local mode retains mutation and administrator controls.

## 12. Planned Production Architecture

```text
Vercel frontend
  -> API/control plane
  -> managed auth and tenant authorization
  -> PostgreSQL control database
  -> durable job queue
  -> local/cloud workers pull jobs outbound
  -> object storage
  -> pgvector or dedicated vector store
```

This permits a local worker without open inbound router ports. Workers authenticate with scoped credentials, lease jobs, publish progress, and store outputs durably.

## 12.1 Phase 16 Identity Architecture

```text
Browser
  -> Vercel Next.js auth and BFF route handlers
  -> HttpOnly Supabase access/refresh cookies
  -> approved same-origin /api/backend/* forwarding
  -> FastAPI with Authorization bearer token forwarding when authenticated
  -> Supabase JWKS token validation
  -> local users, organizations, policies, quotas
```

Supabase JWT claims only establish identity. Application roles, platform administrator status, account status, organization roles, and quota plan come from the application database.

Browser code does not call authenticated backend endpoints directly. It calls the Next.js BFF on the same origin; the BFF forwards only fixed backend path prefixes, rotates refresh cookies through Supabase when needed, clears cookies on failed refresh, and never accepts arbitrary proxy destinations.

Central authorization policies evaluate owner user, organization membership, resource visibility, anonymous session, deleted state, and expiration state. Report IDs alone do not grant access.

The current RAG index remains local JSON/runtime storage. Phase 16 adds organization ownership metadata and policy boundaries; durable tenant-specific vector storage is deferred to Phase 18.

## 13. Non-Negotiable Boundaries

The application must not:

- connect wallets implicitly
- request private keys or seed phrases
- sign transactions
- execute trades
- custody funds
- promise returns
- provide personalized financial advice
- hide missing data
- auto-trust discovered content
- expose provider secrets
- let model output override deterministic risk fields

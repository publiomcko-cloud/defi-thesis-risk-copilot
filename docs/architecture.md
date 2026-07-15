# Architecture — DeFi Thesis & Risk Copilot

## 1. Overview

DeFi Thesis & Risk Copilot is a full-stack AI research application for DeFi strategy analysis.

The architecture is designed around:

- clear separation between frontend, backend, data adapters, RAG, agents, risk logic, and model providers
- source-grounded analysis using protocol documentation
- deterministic calculations where possible
- LLM generation only after retrieval, normalization, and risk scoring
- human review before trusted knowledge-base ingestion
- role-based access for sensitive actions
- portfolio-grade maintainability and documentation

## 2. Current Product Domains

```text
Next.js Frontend
  -> strategy analysis UI
  -> report pages
  -> review queue
  -> simulator
  -> watchlist
  -> options analysis
  -> demo dashboard
  -> admin console for auth status, provider credentials, and audit logs

FastAPI Backend
  -> controlled analysis workflow
  -> RAG retrieval
  -> market data adapters
  -> deterministic risk scoring
  -> report generation
  -> source monitoring
  -> public-source discovery
  -> evaluation and review queue
  -> human-approved RAG ingestion
  -> simulation
  -> watchlist and alerts
  -> options analysis
  -> ML dataset export and advisory classifier
  -> MVP access control
  -> provider credential metadata
  -> access audit logs
  -> Vast.ai dry-run/manual lifecycle manager
  -> deterministic demo seeding and scenario metadata

Storage
  -> SQLite or PostgreSQL
  -> local knowledge_base markdown files
  -> discovered knowledge markdown under knowledge_base/discovered/
  -> JSON RAG index for MVP
  -> encrypted provider credential metadata
  -> access audit logs
  -> Vast.ai lifecycle sessions
  -> synthetic demo records in normal persistence tables
  -> example Markdown reports under examples/reports/
```

## 3. Analysis Flow

```text
User strategy input
    -> protocol detection
    -> local/hybrid RAG retrieval
    -> market-data adapter lookup
    -> manual fallback fields
    -> deterministic risk scoring
    -> stress scenarios
    -> report writer
    -> optional LLM synthesis
    -> persisted report
    -> markdown export
```

Deterministic risk scoring remains authoritative. LLM and ML outputs are advisory or explanatory only.

## 4. Discovery-to-RAG Flow — Phase 10

```text
Admin triggers discovery
    -> DefiLlama/manual/source collector
    -> candidate filtering
    -> candidate normalization
    -> discovered_items table
    -> automated evaluation
    -> review_items table
    -> human approval or rejection
    -> explicit ingest-to-RAG action
    -> markdown file under knowledge_base/discovered/
    -> RAG index refresh
    -> future reports can cite approved source
```

No discovered source becomes trusted automatically. Human approval plus an explicit ingest action is required.

## 5. Access Control — Phase 11

Two user roles are implemented for MVP/local use:

```text
admin
common
```

Common users can run normal analysis workflows, simulations, options analysis, and personal watchlist flows.

Admin users can manage discovery sources, review decisions, RAG ingestion, provider credentials, Vast.ai sessions, and audit logs.

`AUTH_ENABLED=false` preserves local/demo behavior and treats protected workflows as a demo admin session. `AUTH_ENABLED=true` requires a bearer token and enforces admin/common role checks for sensitive endpoints.

Sensitive operations must be server-side only:

- credential creation
- credential rotation
- discovery source configuration
- approved source ingestion
- Vast.ai rent/start/destroy lifecycle
- audit-log review

## 6. Credential and Provider Storage

Provider credentials use this model:

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

- raw secrets are never sent to the frontend
- raw secrets are never logged
- database-stored secrets must be encrypted
- `CREDENTIAL_ENCRYPTION_KEY` is required for database-stored secrets
- a production deployment should replace the MVP encryption helper with a managed secret store or KMS-backed encryption
- every sensitive action should create an audit event

## 7. Vast.ai Ephemeral Provider — Phase 12

The Vast.ai provider is a lifecycle manager, not a simple HTTP client.

```text
admin request
    -> validate budget and role
    -> search offer
    -> rent instance
    -> boot container
    -> health-check model endpoint
    -> run model task through OpenAI-compatible interface
    -> collect result
    -> destroy instance
    -> write lifecycle/audit logs
```

Planned lifecycle states:

```text
idle
searching_offer
renting_instance
booting
starting_model_server
health_checking
ready
serving_request
cleanup
destroyed
failed
```

Vast.ai is disabled by default. The implemented Phase 12 path supports admin manual warm-up, dry-run lifecycle simulation, test prompts, idempotent destroy, and cleanup before any automatic ephemeral usage is enabled.

## 8. Demo Data — Final Phase 13

The demo module seeds deterministic portfolio examples into existing tables rather than adding separate demo-only schema.

```text
GET /api/demo/status
GET /api/demo/scenarios
POST /api/demo/seed
```

Seeded records include:

- synthetic strategy reports
- a discovery-to-review-to-RAG-ingestion example
- a watchlist item with an open in-app alert
- an options and volatility report
- a Vast.ai dry-run session record

The demo path is local, synthetic, and educational. It does not call paid APIs, connect wallets, sign transactions, execute trades, or rent real Vast.ai infrastructure.

## 8. Backend Module Map

```text
backend/app/
  api/
  agents/
  auth/
  core/
  data_sources/
  db/
  evaluation/
  llm/
  market_data/
  ml/
  models/
  monitoring/
  options/
  rag/
  reports/
  risk/
  simulation/
  watchlist/
  discovery/
  knowledge_base_ingestion/
  providers/
  llm/vast/
```

## 9. Frontend Route Map

```text
frontend/src/app/
  page.tsx
  analyze/page.tsx
  reports/[reportId]/page.tsx
  protocols/page.tsx
  review/page.tsx
  simulate/page.tsx
  watchlist/page.tsx
  options/page.tsx
  admin/page.tsx
  admin/provider-credentials/page.tsx
  admin/audit/page.tsx
  admin/vast/page.tsx
  about/page.tsx
```

## 10. Non-Negotiable Boundaries

The app must not:

- connect wallets
- request private keys or seed phrases
- sign transactions
- execute trades
- custody funds
- provide personalized financial advice
- auto-ingest unreviewed sources
- expose provider API keys to the frontend
- let remote LLM output override deterministic risk scoring

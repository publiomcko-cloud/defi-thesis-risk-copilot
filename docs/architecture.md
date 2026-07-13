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
  -> future admin console

FastAPI Backend
  -> controlled analysis workflow
  -> RAG retrieval
  -> market data adapters
  -> deterministic risk scoring
  -> report generation
  -> source monitoring
  -> evaluation and review queue
  -> simulation
  -> watchlist and alerts
  -> options analysis
  -> ML dataset export and advisory classifier
  -> future access control
  -> future Vast.ai lifecycle manager

Storage
  -> SQLite or PostgreSQL
  -> local knowledge_base markdown files
  -> JSON RAG index for MVP
  -> future encrypted credential metadata
  -> future audit logs
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

Two user roles are planned:

```text
admin
common
```

Common users can run normal analysis workflows, simulations, options analysis, and personal watchlist flows.

Admin users can manage discovery sources, review decisions, RAG ingestion, provider credentials, Vast.ai sessions, and audit logs.

Sensitive operations must be server-side only:

- credential creation
- credential rotation
- discovery source configuration
- approved source ingestion
- Vast.ai rent/start/destroy lifecycle
- audit-log review

## 6. Credential and Provider Storage

Provider credentials should use this model:

```text
api_credentials
  id
  provider
  display_name
  encrypted_secret or env_reference
  secret_last_four
  status
  created_by_user_id
  created_at
  rotated_at
  revoked_at
```

Rules:

- raw secrets are never sent to the frontend
- raw secrets are never logged
- database-stored secrets must be encrypted
- environment variables are acceptable for the first implementation
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

Vast.ai must be disabled by default. The first implementation should support admin manual warm-up and cleanup before automatic ephemeral usage.

## 8. Backend Module Map

```text
backend/app/
  api/
  agents/
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

Future Phase 10:
  discovery/
  knowledge_base_ingestion/

Future Phase 11:
  auth/
  credentials/
  audit/

Future Phase 12:
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
  about/page.tsx

Future:
  admin/discovery/page.tsx
  admin/credentials/page.tsx
  admin/vast/page.tsx
  admin/audit/page.tsx
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

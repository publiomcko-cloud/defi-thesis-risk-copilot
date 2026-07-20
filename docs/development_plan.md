# DeFi Thesis & Risk Copilot — Consolidated Development Plan

This is the single authoritative product and engineering roadmap for DeFi Thesis & Risk Copilot.

It replaces the fragmented planning documents previously stored in:

- `docs/post_mvp_development_plan.md`
- `docs/phase_10_12_expansion_plan.md`

Git history preserves the original Codex-ready task specifications. This document preserves every completed phase, the important architectural decisions from those plans, and the new path from portfolio demo to a real product.

## 1. Product Mission

DeFi Thesis & Risk Copilot standardizes research and risk review for complex DeFi strategies.

The product should help a user:

1. describe a strategy or market thesis;
2. retrieve protocol and internal risk context;
3. collect public or manually supplied market data;
4. expose assumptions and missing information;
5. apply deterministic risk scoring;
6. test transparent stress scenarios;
7. generate a structured, source-grounded report;
8. monitor relevant thresholds and research changes;
9. maintain a controlled, human-approved knowledge base.

The product does **not** connect wallets, sign transactions, hold assets, execute trades, or provide personalized financial advice.

## 2. Permanent Engineering Principles

- Deterministic calculations and risk fields remain the source of truth.
- LLM output may improve language but may not invent or overwrite deterministic values.
- Missing data and uncertainty must remain visible.
- Source provenance must remain visible.
- Discovery and trust are separate: discovered content requires evaluation and human approval before RAG ingestion.
- Provider credentials remain server-side and are never returned to the browser.
- Public deployments are safe by default and read-only for privileged workflows.
- Heavy infrastructure is optional, cost-limited, auditable, and explicitly controlled.
- Wallet, custody, signing, execution, and automated capital allocation remain out of scope unless separately designed and reviewed.

---

# Completed Product History

## Phase 0 — Core Technical MVP — Complete

Established:

- FastAPI backend
- Next.js frontend
- SQLAlchemy and Alembic persistence
- Docker Compose local stack
- curated Markdown knowledge base
- local retrieval pipeline
- market-data adapter interfaces
- deterministic risk scoring
- structured report generation
- Markdown report export
- backend tests and frontend build checks

Core workflow:

```text
strategy input
  -> strategy parsing
  -> protocol-context retrieval
  -> market-data adapters
  -> deterministic risk scoring
  -> stress scenarios
  -> structured report
  -> persistence
  -> Markdown export
```

## Post-MVP Phase 1 — Optional Backend LLM Synthesis — Complete

- disabled deterministic fallback
- local Ollama provider
- OpenAI-compatible provider
- timeout and safe fallback
- reports continue working without an LLM
- model wording cannot override risk, market data, sources, missing data, or disclaimers

## Post-MVP Phase 2 — Source Monitoring and Discovery — Complete

- source watches
- manual/public discovery inputs
- normalized discovered-item records
- duplicate detection
- failure tracking
- discovered-item listing

## Post-MVP Phase 3 — Automated Evaluation and Review Queue — Complete

- deterministic candidate evaluation
- persisted evaluation results
- review-item creation
- reviewer notes
- linked reports
- visible confidence and missing data

Review states:

```text
needs_review
approved_for_rag
needs_more_data
rejected
archived
```

## Post-MVP Phase 4 — Strategy Simulator — Complete

- net-spread analysis
- borrow-rate shock
- liquidity and slippage shock
- collateral drawdown
- early-exit discount
- incentive removal
- combined adverse case
- formulas, assumptions, missing data, and interpretations

## Post-MVP Phase 5 — Watchlists and Alerts — Complete

- watchlist persistence
- configurable threshold rules
- manually evaluated snapshots
- in-app alert events
- severity and status
- no trade execution or external notification dependency

## Post-MVP Phase 6 — Options and Volatility Analysis — Complete

- long calls and puts
- premium and contract count
- breakeven
- maximum loss and profit framing
- bid/ask spread
- expiration timing
- payoff scenarios and moneyness
- return on premium
- volatility thesis and risk framing

## Post-MVP Phase 7 — Advanced RAG and Retrieval Evaluation — Complete

- header-aware chunking
- local hash embeddings
- keyword/vector/metadata hybrid weighting
- reranking foundations
- citation validation foundations
- retrieval-evaluation dataset and scripts
- deterministic local fallback

## Post-MVP Phase 8 — Fine-Tuning and ML Risk Groundwork — Complete

- report-to-dataset export
- deterministic labels distinguished from human ground truth
- baseline classifier workspace
- advisory model outputs cannot override deterministic scoring
- model-training workspace

## Post-MVP Phase 9 — HPC and SLURM Readiness — Complete

- SLURM embedding-generation template
- retrieval-evaluation template
- classifier-training template
- Apptainer definition
- no HPC dependency for normal operation

## Post-MVP Phase 10 — Auto-Discovery and Human-Approved RAG Ingestion — Complete

Discovery sources and candidate types:

- DefiLlama public/free endpoints
- manual candidate lists
- protocols
- yield pools
- options/open-interest sources where practical
- fees/revenue sources where practical

Discovery controls:

- minimum protocol and pool TVL
- chain, category, and protocol allow/block lists
- recency controls
- include flags
- stable discovery keys
- normalization and deduplication

Required trust workflow:

```text
discovery
  -> normalization and deduplication
  -> automated evaluation
  -> human review
  -> approved_for_rag
  -> explicit admin ingestion
  -> curated Markdown
  -> RAG refresh
```

Automatic discovery and evaluation are allowed. Automatic ingestion is not.

Ingestion safeguards:

- only `approved_for_rag` items are eligible
- duplicate ingestion is prevented
- Markdown records provenance, risk summary, missing data, reviewer notes, and disclaimer
- generated sources state that they were automatically discovered and human-approved
- refresh failures are recorded as `refresh_failed`
- ingestion is marked `ingested` only after a successful refresh
- failed refresh can be retried

## Post-MVP Phase 11 — Access Control and Secure Provider Configuration — Complete for MVP

Roles:

```text
admin
common
```

Common-user capabilities:

- normal analysis
- allowed reports
- simulation
- options analysis
- personal-resource foundations

Admin capabilities:

- provider credentials
- discovery controls
- review actions
- RAG ingestion
- audit events
- Vast.ai controls

Credential rules:

- server-side only
- encrypted database storage or environment-backed credentials
- database storage fails closed without an encryption key
- frontend receives safe metadata and last four characters only
- secrets are redacted from audit metadata

Known limitation: the bearer-token implementation is an MVP foundation, not final production identity. Managed authentication, ownership, MFA, recovery, and quotas are planned below.

## Post-MVP Phase 12 — Vast.ai Ephemeral Model Provider — Complete for Dry-Run and Manual Warm-Up

Lifecycle:

```text
idle
  -> searching_offer
  -> renting_instance
  -> booting
  -> starting_model_server
  -> health_checking
  -> ready
  -> serving_request
  -> cleanup
  -> destroyed
```

Failure states:

- offer not found
- rent failure
- boot timeout
- container failure
- model-health failure
- request failure
- cleanup failure

Guardrails:

- disabled and dry-run by default
- admin-only
- hourly-cost and runtime limits
- GPU allow list
- RAM/disk/verified-host filters
- maximum active instances
- startup polling and timeout
- idempotent destroy
- cleanup after failure
- no live rental in automated tests

Automatic Vast.ai rental for ordinary public reports remains disabled.

## Final Phase 13 — Demo Data and Example Reports — Complete

- Pendle PT/lending-loop report
- discovery-to-RAG report
- watchlist-alert report
- options/volatility report
- Vast.ai dry-run report
- idempotent seed
- `/demo` dashboard
- committed Markdown examples
- no external keys or live rental required

## Final Phase 14 — Public Portfolio Deployment — Complete

Architecture:

```text
Vercel frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL
```

Live services:

- Frontend: `https://defi-thesis-risk-copilot.vercel.app`
- Backend: `https://defi-thesis-risk-copilot.onrender.com`
- API docs: `https://defi-thesis-risk-copilot.onrender.com/docs`

Public defaults:

- synthetic demo mode
- LLM synthesis disabled
- Vast.ai disabled/dry-run
- semantic RAG optional and disabled by default
- safe deployment-status endpoint
- no durable dependence on Render runtime report files

---

# Real Product Roadmap

## V1 Phase 15 — Product Hardening and Public-Safe UX — Complete

This phase turns the portfolio deployment into a credible v1 product boundary.

Security and API scope:

- public visitors receive a `common` read-only identity instead of an implicit administrator identity
- privileged and state-changing public-demo routes return `403`
- public discovery, monitoring, evaluation, review mutation, RAG ingestion, watchlist mutation, credential, audit, document-ingestion, and Vast lifecycle actions are blocked
- bounded compute endpoints remain available with rate limiting
- request schemas enforce size and range limits
- request IDs and safe request/error logging are added
- database/RAG-aware `/ready` endpoint is added
- API root links health, readiness, deployment status, docs, and frontend
- Render uses readiness rather than liveness
- startup seeds deterministic data and rebuilds the RAG index
- market cache uses expiration and update-in-place behavior

UX scope:

- live demo becomes the primary entry point
- public admin navigation is hidden
- direct admin pages explain the protected boundary
- review and watchlist screens are read-only publicly
- shared-demo privacy warning is visible
- cold-start and retry states are visible
- APY, LTV, LLTV, volatility, USD, and basis-point units are explicit
- advanced fields use progressive disclosure
- raw JSON and snake-case values are replaced with readable labels
- report sources are clickable
- Markdown can be copied or downloaded
- duplicate report panels are removed
- responsive navigation, footer, focus-visible states, hover states, reduced-motion support, badges, and loading indicators are added

Completion gate:

- backend tests pass
- frontend TypeScript/build pass
- Compose files validate
- public mutation tests pass
- Vercel deployment succeeds
- Render readiness succeeds
- deployed read-only behavior is manually verified

## V1 Phase 16 — Production Identity, Ownership, and Quotas — In Progress

Goal: move from a shared portfolio environment to a real multi-user product.

Deliverables:

- Supabase Auth JWT validation through JWKS
- verified-email enforcement for managed auth
- secure HttpOnly session-cookie BFF foundation instead of browser-stored bearer tokens
- optional administrator MFA configuration and UI foundation
- account recovery and password-reset pages
- user and organization ownership tables
- central authorization policies
- private reports, watchlists, alerts, and saved theses foundations
- organization-scoped knowledge-base metadata foundation; durable tenant vector storage remains Phase 18
- explicit administrator assignment through application database fields
- durable daily API quotas by role/plan
- account deletion and bounded account data export
- isolated anonymous-demo sessions
- retention and TTL cleanup command
- terms, privacy, and versioned consent records

Remaining validation before commercial launch:

- configure Supabase Auth/MFA in the deployed project and verify the complete external email/MFA flow
- perform browser E2E coverage for authenticated organization workflows
- complete legal review of terms and privacy copy

## V1 Phase 17 — Durable Job Queue and Hybrid Workers — Planned

Goal: execute heavy work outside the public web process.

```text
Vercel frontend
  -> Render API/control plane
  -> Supabase job queue and persistence
  -> local or cloud workers pull jobs outbound
```

Deliverables:

- job state machine
- scoped worker authentication
- lease and heartbeat
- retry and dead-letter handling
- idempotent execution
- cancellation and progress events
- local Docker worker requiring no inbound ports
- optional private Cloudflare/Tailscale administration
- Vast.ai worker adapter
- object-storage artifacts
- capacity and cost controls

## V1 Phase 18 — Production RAG and Knowledge Storage — Planned

Goal: eliminate runtime-filesystem dependence and support tenant-specific corpora.

Deliverables:

- object storage for documents
- PostgreSQL/pgvector or dedicated vector store
- durable chunks and embeddings
- tenant/protocol metadata filters
- worker-based ingestion
- document versioning
- re-embedding migrations
- source deletion and tombstones
- retrieval observability
- citation-integrity checks
- evaluation dashboards
- approved-source lineage
- knowledge-version rollback

## V1 Phase 19 — Production Operations and Security — Planned

Deliverables:

- distributed rate limiting
- WAF policy
- dependency and container scanning
- automated dependency updates
- centralized logs, errors, traces, and latency metrics
- request/job correlation IDs
- uptime checks and dashboards
- backup/restore drills
- migration rollback process
- secret rotation
- CSP and security headers
- abuse detection
- incident-response runbook
- threat model and penetration-test checklist
- PostgreSQL integration tests
- browser end-to-end tests
- accessibility automation
- load and failure testing

## V1 Phase 20 — Product Analytics, Notifications, and Commercial Readiness — Planned

Deliverables:

- privacy-conscious analytics
- onboarding and workflow metrics
- email/webhook/Telegram notifications
- notification preferences
- scheduled monitoring jobs
- usage metering and plan limits
- subscription/billing foundation
- organization workspaces and invitations
- audit export
- customer-facing status page
- support and feedback workflow

## V1 Phase 21 — Model and Research Intelligence Expansion — Planned

Deliverables:

- explicit task-level provider selection
- safe ephemeral GPU execution through workers
- model evaluation before provider promotion
- output-quality scoring
- prompt/model versioning
- regression datasets
- human feedback capture
- source-quality scoring
- broader protocol/market coverage
- catalysts and thesis tracking
- scenario comparison across saved reports

---

# Release Gates

## V1.0 Product Gate

The application may be labeled a production v1.0 when:

- public users cannot access privileged mutations;
- real authentication and ownership protect private data;
- anonymous inputs are isolated or automatically deleted;
- rate limiting is durable across instances;
- RAG and artifacts use durable storage;
- heavy work runs through jobs/workers;
- logs, metrics, alerts, backups, and security headers are active;
- browser and PostgreSQL integration tests run in CI;
- legal and privacy copy is published;
- wallet, signing, custody, and execution have not been introduced implicitly.

## Definition of Done for Every Future Phase

A phase is complete only when:

1. code and migrations are committed;
2. tests cover normal, failure, and authorization paths;
3. frontend type/build checks pass;
4. Docker configuration validates;
5. documentation and current state are updated;
6. secrets are not exposed;
7. public safety boundaries remain intact;
8. deployment behavior is verified;
9. known limitations are explicit.

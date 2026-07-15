# Post-MVP Development Plan — DeFi Thesis & Risk Copilot

## 1. Purpose

This document defines the product-development plan after the original Phase 10 MVP checkpoint.

The post-MVP expansion block and local demo phase are complete through Final Phase 13:

```text
Post-MVP Phase 1: Optional backend LLM synthesis
Post-MVP Phase 2: Source monitoring and discovery
Post-MVP Phase 3: Automated evaluation pipeline and review queue
Post-MVP Phase 4: Strategy simulator
Post-MVP Phase 5: Watchlist and alerts
Post-MVP Phase 6: Options and volatility analysis agent
Post-MVP Phase 7: Advanced RAG and retrieval evaluation
Post-MVP Phase 8: Fine-tuning and ML risk classifier groundwork
Post-MVP Phase 9: HPC and SLURM readiness
Post-MVP Phase 10: Auto-discovery and human-approved RAG ingestion
Post-MVP Phase 11: Access control and secure provider configuration
Post-MVP Phase 12: Vast.ai ephemeral model provider
Final Phase 13: Demo data and example reports
```

Before public deployment and final polish, the remaining work is:

```text
Final Phase 14: Public portfolio deployment
Final Phase 15: Portfolio polish
```

The detailed Phase 10-12 implementation plan is maintained in [`docs/phase_10_12_expansion_plan.md`](phase_10_12_expansion_plan.md).

## 2. Current Baseline

Current baseline capabilities:

- FastAPI backend and Next.js frontend.
- SQLite/PostgreSQL persistence through SQLAlchemy and Alembic.
- Local curated RAG knowledge base.
- Lightweight local hash embeddings and optional hybrid/semantic retrieval signals.
- Manual, Pendle, Morpho, Aave, DefiLlama, CoinGecko, and manual data adapters.
- Controlled analysis workflow.
- Deterministic rule-based risk scoring.
- Structured report generation and Markdown export.
- Optional LLM report synthesis with deterministic fallback.
- Manual source monitoring and discovered-item storage.
- Automated evaluation and human review queue.
- Deterministic strategy simulator.
- Watchlists and in-app alerts.
- Options and volatility analysis workflow.
- ML risk classifier groundwork and dataset export.
- Optional HPC/SLURM templates.

Current known limitations:

- RAG is local and curated, with explicit human-approved ingestion for discovered items.
- Review approval does not ingest automatically; explicit ingest-to-RAG action is required.
- Source discovery is manually triggered and still basic.
- Production authentication, MFA, ownership scoping, and rate limits are not implemented yet.
- API/provider secrets can be managed through admin-only metadata endpoints, but hosted production should use managed secret storage or KMS-backed encryption.
- Vast.ai dry-run/manual warm-up is implemented; automatic ephemeral use for normal reports is not enabled.
- Fine-tuning has not been performed.
- Public demo/deployment/polish remain final phases.
- Local deterministic demo data and example reports are implemented; public deployment and video polish remain final phases.

## 3. Product Boundary

The product remains a research and risk analysis copilot.

The application must not:

- connect wallets
- request private keys
- request seed phrases
- sign transactions
- execute trades
- custody funds
- provide personalized financial advice
- provide direct buy or sell instructions
- hide missing data or assumptions
- automatically trust newly discovered sources
- expose provider API keys to the frontend
- let remote model output override deterministic risk scoring

The application may:

- analyze public protocol data
- summarize strategy mechanics
- classify strategy risk
- simulate risk scenarios
- monitor public sources
- queue discoveries for human review
- ingest approved sources into the knowledge base after explicit admin action
- generate educational, non-advisory reports
- use optional LLM providers for explanatory synthesis
- use optional ephemeral GPU infrastructure for approved model tasks

## 4. Post-MVP Phase 10 — Auto-Discovery and Human-Approved RAG Ingestion

### Objective

Add a controlled discovery-to-knowledge-base workflow.

The app should discover candidate protocols, pools, markets, options venues, and source items from public sources such as DefiLlama or a manual list. It should normalize, deduplicate, evaluate, and route those candidates through human review before any knowledge-base ingestion occurs.

### Required workflow

```text
public source or manual list
    -> discovery collector
    -> normalized discovered item
    -> duplicate detection
    -> automated evaluation
    -> human review queue
    -> approved_for_rag
    -> explicit admin ingest-to-RAG action
    -> generated curated markdown
    -> RAG index refresh
```

### Initial discovery sources

```text
DefiLlama protocols
DefiLlama yield pools
DefiLlama options overview
DefiLlama open-interest overview
DefiLlama fees/revenue overview
Manual URL or pasted list
```

### Acceptance criteria

- Discovery can run from DefiLlama and/or a manual list.
- Candidates are normalized and deduplicated.
- Candidates enter the existing evaluation and review queue.
- Rejected, archived, or unreviewed items cannot be ingested.
- Approved items require explicit admin ingest action.
- Duplicate ingestion is prevented.
- Generated markdown includes source metadata, reviewer metadata, evaluation summary, missing data, and disclaimers.
- RAG index refresh is triggered after ingestion.
- Future analysis can retrieve the ingested knowledge.

## 5. Post-MVP Phase 11 — Access Control and Secure Provider Configuration

### Objective

Add role-based access control before any Vast.ai automation or provider-secret storage.

The system should define two user types:

```text
admin
common
```

### Common user

Common users may:

- run normal strategy analysis
- view allowed reports
- run simulations
- run options analysis
- create personal watchlist items
- view their own in-app alerts

Common users may not:

- configure provider API keys
- run or destroy Vast.ai instances
- approve or ingest discovered sources into RAG
- change global discovery settings
- view system audit logs
- manage other users

### Admin user

Admins may:

- manage users and roles
- configure discovery sources
- run global discovery
- approve/reject/archive review items
- ingest approved items into the knowledge base
- configure model providers
- store and rotate Vast.ai credentials
- start, test, and destroy Vast.ai model sessions
- view lifecycle/cost/audit logs

### Credential storage rules

Secrets must be server-side only.

MVP implementation should support:

```text
Mode A: environment variables only
Mode B: encrypted database storage for admin-managed provider credentials
```

If stored in the database, raw secrets must not be stored in plaintext or returned to the frontend. Store encrypted values and safe metadata only.

### Acceptance criteria

- Admin and common roles exist.
- Admin-only endpoints reject common users.
- Raw API secrets are never returned to the frontend.
- Sensitive actions produce audit events.
- RAG ingestion from review items is admin-only.
- Vast.ai lifecycle actions are admin-only.

## 6. Post-MVP Phase 12 — Vast.ai Ephemeral Model Provider

### Objective

Add an optional model provider that can rent a Vast.ai GPU instance, start a model server container, use it for a controlled task, and then destroy the instance.

Vast.ai must be disabled by default and must not be required for the normal app to run.

### Recommended provider flow

```text
admin enables Vast.ai provider
    -> app searches acceptable GPU offer
    -> app rents instance within cost/runtime constraints
    -> container starts OpenAI-compatible model server
    -> app health-checks model endpoint
    -> task runs
    -> app destroys instance by default
    -> lifecycle and cost metadata are logged
```

### Required safety controls

- Admin-only access.
- Server-side API key storage only.
- Max hourly cost.
- Max session runtime.
- Max active instances.
- GPU allowlist and minimum VRAM.
- Verified-machine requirement where supported.
- Automatic destroy by default.
- Emergency cleanup endpoint.
- No real Vast.ai calls in unit tests.

### Acceptance criteria

- Vast.ai provider is disabled by default.
- Unit tests mock Vast.ai API calls.
- Existing local/API LLM providers still work.
- Deterministic report fallback still works with no LLM.
- Cost/runtime limits are enforced.
- Failed startup attempts trigger cleanup.
- Destroy/cleanup endpoints work even after partial failures.

## 7. Final Phase 13 — Demo Data and Example Reports

Purpose:

- create polished example reports
- create repeatable demo inputs
- include at least one discovery-to-RAG flow example
- update screenshots
- prepare demo script
- create showcase-ready sample data

Status: implemented for local portfolio review.

Implemented scope:

- `/api/demo/status`, `/api/demo/scenarios`, and admin-gated `/api/demo/seed`
- `backend/scripts/seed_demo_data.py`
- frontend `/demo` dashboard
- deterministic seeded reports, discovery/review/RAG-ingestion example, watchlist alert, options example, and Vast.ai dry-run session
- example Markdown reports in `examples/reports/`
- walkthrough in `docs/demo_walkthrough.md`

Not included in Phase 13:

- hosted public deployment
- recorded demo video
- new wallet, custody, trade, or buy/sell functionality

## 8. Final Phase 14 — Public Portfolio Deployment

Purpose:

- deploy frontend
- deploy backend
- configure database
- configure environment variables
- keep admin-only features protected
- keep Vast.ai disabled unless safely configured
- test public demo links
- update README with live links

## 9. Final Phase 15 — Portfolio Polish

Purpose:

- polish UI screenshots
- record demo video
- finalize README presentation
- improve case study language
- update portfolio readiness checklist
- prepare LinkedIn/GitHub presentation material

## 10. Codex Execution Prompt

Use this template for each phase:

```text
Implement Post-MVP Phase X from docs/post_mvp_development_plan.md and docs/phase_10_12_expansion_plan.md.

Do not implement wallet connection, transaction signing, trade execution, custody, or personalized financial advice.

Preserve deterministic risk scoring as the source of truth.

Preserve existing app behavior and tests.

After implementation, run:
- cd backend && source .venv/bin/activate && python -m pytest -q
- cd frontend && npm run lint
- cd frontend && npm run build
- docker compose config
- python backend/scripts/run_smoke_checks.py

Summarize:
1. files changed
2. commands run
3. tests passed or failed
4. remaining issues
5. whether the project is ready for the next phase
```

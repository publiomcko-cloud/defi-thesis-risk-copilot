# Current State — DeFi Thesis & Risk Copilot

This document describes the current public portfolio state of DeFi Thesis & Risk Copilot.

Historical planning notes should be kept in `docs/archive/`.

## Public Demo

- Frontend: pending
- Backend health: pending
- API docs: pending
- Demo video: pending
- Local demo dashboard: implemented at `/demo`
- Example Markdown reports: implemented in `examples/reports/`

## Current Stack

Current local stack:

- Frontend: Next.js App Router, TypeScript, global CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Local database: SQLite by default; PostgreSQL supported through `DATABASE_URL` and Docker Compose
- Local RAG: curated markdown knowledge base, header-aware chunking, local hash embeddings, JSON vector store
- Frontend/backend integration: controlled analysis workflow with persisted reports
- Testing and validation: pytest, smoke scripts, frontend lint/build
- Automation: GitHub Actions CI

## Current Status

Current status: Final Phase 13 complete.

The app currently supports optional backend LLM synthesis, controlled public-source discovery, automated evaluation, human review queue foundations, explicit human-approved RAG ingestion, MVP token access control, admin/common role checks, server-side provider credential storage metadata, audit logs, admin-only Vast.ai dry-run/manual warm-up sessions, deterministic strategy simulation, in-app watchlist alerts, options/volatility analysis, advanced RAG evaluation foundations, ML risk classifier groundwork, optional HPC/SLURM templates, and deterministic local demo data with example reports.

Before public deployment and final polish, the next planned product phases are:

```text
Final Phase 14: Public portfolio deployment
Final Phase 15: Portfolio polish
```

Detailed planning for Phases 10-12 is in `docs/phase_10_12_expansion_plan.md`.

## What the App Can Do Now

The current app can:

- run a controlled DeFi strategy analysis workflow through `/api/analyze`
- persist structured reports and retrieve them later
- export generated reports to Markdown
- list supported protocols for the core MVP scope
- refresh the local curated RAG index from `knowledge_base/`
- retrieve local RAG context from Pendle, Morpho, Aave, Chainlink, and internal risk notes
- optionally use hybrid retrieval, local semantic signals, reranking, citation validation, and retrieval evaluation
- fetch or normalize market data through manual, Pendle, Morpho, Aave, DefiLlama, and CoinGecko adapters
- use deterministic rule-based risk scoring with visible components, confidence, and drivers
- generate stress scenarios and monitoring checklists
- optionally synthesize report wording with an LLM while preserving deterministic fields
- create discovered source candidates through manual monitoring
- run public-source discovery through `/api/discovery/run`
- list discovery candidates through `/api/discovery/candidates`
- evaluate discovered candidates and create review queue items
- update review status as `needs_review`, `approved_for_rag`, `rejected`, `needs_more_data`, or `archived`
- explicitly ingest only `approved_for_rag` review items into `knowledge_base/discovered/`
- refresh the local RAG index after approved ingestion
- run in local/demo mode with `AUTH_ENABLED=false`
- enforce admin/common authorization for sensitive endpoints when `AUTH_ENABLED=true`
- store provider credentials server-side with encrypted metadata and last-four display only
- view audit events for credential management, discovery runs, review status changes, and approved RAG ingestion
- inspect Vast.ai runtime configuration through `/api/admin/vast/config`
- start dry-run/manual Vast.ai model sessions through `/api/admin/vast/sessions/start`
- list, test, destroy, and clean up Vast.ai sessions through admin-only endpoints
- seed deterministic local demo data through `/api/demo/seed` or `backend/scripts/seed_demo_data.py`
- inspect demo status and scenarios through `/api/demo/status` and `/api/demo/scenarios`
- view the frontend demo dashboard at `/demo`
- review example Markdown reports in `examples/reports/`
- run deterministic strategy simulation through `/api/simulation/run`
- create watchlist items and rule-based in-app alerts
- run deterministic options analysis through `/api/options/analyze`
- export candidate ML training examples from persisted reports
- run an advisory baseline risk classifier for future model comparison only
- use optional HPC/SLURM templates for batch RAG and ML-preparation workflows

## Implemented Feature Areas

Implemented feature areas include:

- FastAPI backend skeleton and health endpoint
- Next.js frontend with main navigation and analysis/report flows
- SQLAlchemy/Alembic database foundation
- Docker Compose local stack
- CI workflow for backend tests, frontend lint/build, and Compose validation
- local curated RAG knowledge base and JSON vector store
- optional hybrid RAG retrieval and retrieval evaluation dataset
- market data adapter interface and MVP adapters
- controlled internal analysis orchestration
- deterministic risk scoring and report writer
- optional backend LLM synthesis with Ollama and OpenAI-compatible provider abstractions
- monitoring/discovery foundation
- public-source discovery and manual discovery inputs
- evaluation and human review queue foundation
- human-approved discovery-to-RAG ingestion
- MVP access control and admin/common role dependencies
- server-side provider credential management
- audit logging for sensitive actions
- Vast.ai dry-run/manual warm-up lifecycle
- local portfolio demo dashboard
- deterministic demo seed data
- example Markdown reports
- strategy simulator
- watchlist and in-app alert system
- options and volatility analysis
- ML dataset export and advisory baseline classifier
- model-training workspace
- HPC workspace with SLURM templates and Apptainer definition

## Active Product Development To Implement

The next active product work is:

1. Final Phase 14 — Public portfolio deployment.

Phase 12 is complete for dry-run/manual warm-up. Automatic Vast.ai use for ordinary report generation remains disabled and should only be added behind explicit task approval.

## Planned User Roles

### Common User

Common users can:

- run normal strategy analysis
- view allowed reports
- run simulations
- run options analysis
- create personal watchlists
- view their own in-app alerts

Common users cannot:

- configure API keys
- manage Vast.ai
- approve or ingest discovered sources when `AUTH_ENABLED=true`
- change global discovery settings
- view sensitive audit logs
- manage users

### Admin User

Admins can:

- use the bootstrap/admin bearer-token flow
- run global discovery jobs
- approve/reject/archive review items
- ingest approved items into the knowledge base
- manage provider credentials
- view access audit logs

Admins can configure, start, test, destroy, and clean up dry-run/manual Vast.ai sessions.

## Current Validation Commands

Backend validation:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend validation:

```bash
cd frontend
npm run lint
npm run build
```

RAG validation:

```bash
cd backend
python scripts/evaluate_retrieval.py
```

ML groundwork validation:

```bash
cd backend
python scripts/export_training_dataset.py
```

Docker validation:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

HPC template validation:

```bash
bash -n hpc/slurm_generate_embeddings.sbatch
bash -n hpc/slurm_evaluate_retrieval.sbatch
bash -n hpc/slurm_train_risk_classifier.sbatch
```

## Current Limitations

- The application is still an MVP and uses deterministic local analysis logic.
- Demo scenarios are synthetic and designed for portfolio review; they are not live market assessments.
- Data adapters are basic MVP implementations; several protocol adapters still rely on manual fallback.
- RAG is local and curated only; it does not crawl protocol docs or refresh automatically.
- Semantic retrieval is optional and currently uses a deterministic local semantic provider rather than an external embedding model.
- Source monitoring is manually triggered and creates review candidates only.
- Review approval does not ingest sources automatically; explicit admin ingestion is required.
- Access control is an MVP bearer-token implementation; production-grade hosted auth, MFA, password reset, per-user resource ownership, and rate limits are not implemented.
- Provider credentials can be stored through the admin API, but the MVP encryption helper is not a substitute for a production secret manager.
- Vast.ai dry-run/manual warm-up is implemented, but automatic ephemeral rental for normal report generation is not enabled.
- Simulation is deterministic and educational; it does not forecast outcomes or recommend entering/exiting positions.
- Watchlist alerts are manually evaluated and in-app only; no push, email, streaming, or automated execution exists.
- Options analysis is deterministic and educational; it does not recommend buying or selling options.
- Risk scoring is deterministic and rule-based, but not a quantitative liquidation engine.
- Reports are persisted and rendered through a deterministic template; optional LLM synthesis can enrich explanatory wording when enabled, but cannot override deterministic risk scoring, missing data, sources, market values, protocols, or disclaimers.
- Fine-tuning has not been performed; the baseline classifier is advisory only and cannot override deterministic risk scoring.
- HPC readiness is template-based only; no SLURM job has been submitted from this local environment.
- No deployed public demo exists yet; local demo data and example reports are implemented.
- No wallet connection or transaction execution will be implemented.

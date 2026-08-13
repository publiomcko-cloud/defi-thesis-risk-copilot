# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

A full-stack DeFi research and risk-analysis portfolio project that turns a strategy thesis into a structured, source-grounded report with deterministic risk scoring, visible assumptions, missing data, stress scenarios, and monitoring requirements.

The repository is intentionally engineered like a production-capable SaaS platform while the public deployment remains a constrained portfolio demo. It demonstrates applied AI, data, backend, security, multi-tenant, durable-workflow, RAG, and operational engineering without operating a paid financial product.

It does not connect wallets, sign transactions, hold funds, execute trades, allocate capital, or provide personalized financial advice.

## Live Portfolio Demo

- Frontend: https://defi-thesis-risk-copilot.vercel.app
- Guided demo: https://defi-thesis-risk-copilot.vercel.app/demo
- Example report: https://defi-thesis-risk-copilot.vercel.app/reports/demo_report_pendle_pt_loop
- Backend: https://defi-thesis-risk-copilot.onrender.com
- Readiness: https://defi-thesis-risk-copilot.onrender.com/ready
- Deployment status: https://defi-thesis-risk-copilot.onrender.com/api/deployment/status
- API docs: https://defi-thesis-risk-copilot.onrender.com/docs

The Render free-tier backend may cold-start after inactivity.

## Current Development Profile

The active implementation profile is **portfolio-first, product-capable**.

The current goal is to demonstrate production-grade architecture and engineering decisions without taking on the ongoing legal, provider, payment, support, and production-operations burden of running a commercial SaaS service.

The original productization requirements are preserved rather than deleted:

- [Portfolio implementation profile](docs/portfolio_profile.md) — active scope and completion rules;
- [Productization backlog](docs/productization_backlog.md) — deferred provider, legal, billing, operational, and launch work;
- [Phase 20 execution plan](docs/phase_20_execution_plan.md) — active portfolio implementation sequence.

A future return to product mode should activate reviewed adapters and policies through existing boundaries instead of requiring an architectural rewrite.

## Current Phase Status

```text
Completed: Phase 0, Post-MVP 1–12, Final 13–14, V1 Phases 15–18
Implemented foundation: V1 Phase 19 (merged; deployed operational evidence remains gated)
In progress: V1 Phase 20 portfolio profile
  - 20A governance/design foundation: complete
  - 20B consent-aware first-party analytics: implemented and validated; production collection disabled
  - next required portfolio slices: 20C, 20D, 20F, 20H, reduced 20I, 20J closeout
  - 20E secure sandbox adapter: optional portfolio demonstration
  - real 20G billing/provider work: deferred to productization backlog
Later: V1 Phase 21 model/research intelligence, then portfolio release validation
```

## Engineering Capabilities

The repository currently demonstrates or provides foundations for:

- structured DeFi strategy reports;
- curated protocol retrieval;
- public and manual market-data adapters;
- deterministic risk scoring;
- visible assumptions, missing data, confidence, and provenance;
- lending-loop and fixed-yield stress simulation;
- long call/put payoff analysis;
- discovery, deterministic evaluation, and human review before knowledge trust;
- durable source and knowledge metadata with feature-gated private RAG/pgvector paths;
- Markdown export;
- optional local/OpenAI-compatible synthesis;
- managed identity and BFF boundaries;
- user, organization, thesis, quota, anonymous-session, account, consent, export, deletion, and audit foundations;
- durable jobs, workers, retry/recovery, cancellation, idempotency, and capacity controls;
- Phase 19 security, rate-limit, recovery, incident, and supply-chain foundations;
- optional authenticated first-party product analytics with immutable consent decisions, strict metadata, lifecycle integration, and production-disabled rollout;
- admin-controlled Vast.ai dry-run/manual warm-up with real rentals disabled.

The remaining Phase 20 portfolio work focuses on durable schedules, in-app notifications, versioned entitlements/non-billable metering, organization seat/invitation controls, minimal first-party support/privacy workflows, and architecture closeout before moving to Phase 21 AI/research intelligence.

## Public Deployment Safety

The deployed environment is intentionally constrained.

Visitors may inspect public demo records and run bounded public analysis, simulation, options, and market-data flows.

The public portfolio environment does not imply that every implemented production-capable subsystem is activated.

Depending on the current feature flags, public visitors cannot:

- run private monitoring or privileged global discovery;
- change trust/review state;
- ingest private documents or activate private RAG content;
- access another tenant's resources;
- access credentials, audit evidence, internal worker routes, or administrative controls;
- control real Vast.ai rentals;
- activate analytics collection, payments, paid plans, or external notification providers.

Do not submit sensitive personal, wallet, credential, private-position, or confidential research data to the public demo.

## Architecture

Current public deployment:

```text
Browser
  -> Vercel Next.js
  -> Render FastAPI
  -> Supabase PostgreSQL
```

Authenticated architecture:

```text
Browser
  -> Vercel Next.js auth routes and BFF
  -> HttpOnly managed/anonymous cookies
  -> Render FastAPI token verification and authorization
  -> Supabase PostgreSQL server-owned identity/ownership/quota state
```

Extended architecture includes feature-gated durable jobs/workers, knowledge/object/vector storage interfaces, server-side analytics, operational controls, and future portfolio scheduling/notification/entitlement domains.

See [Architecture](docs/architecture.md).

## Permanent Engineering Decisions

### Deterministic values remain authoritative

Model wording cannot silently replace:

- risk rating or score;
- market values;
- assumptions or missing data;
- protocol identity;
- source references;
- disclaimers.

### Discovery does not imply trust

```text
discovery
  -> evaluation
  -> human review
  -> approved_for_rag
  -> explicit ingestion
```

### Identity does not imply authorization

Managed identity establishes who the user is. The application database establishes:

- platform role;
- account status;
- plan/entitlement state;
- resource owner;
- organization membership;
- visibility;
- quota.

### Product architecture does not imply product activation

An implemented adapter, migration, state machine, or feature flag is not proof that a provider or commercial capability is production-ready.

Production-only activation requirements belong in [Productization backlog](docs/productization_backlog.md).

### Heavy infrastructure remains optional and controlled

Normal deterministic analysis does not require an LLM, GPU rental, wallet, private key, external notification provider, or billing provider.

## Local Quick Start

```bash
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Open:

```text
Frontend: http://127.0.0.1:3000
Demo:     http://127.0.0.1:3000/demo
Backend:  http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
```

## Manual Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Validation

Backend:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Compose:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

Phase-specific migration, PostgreSQL concurrency, browser, worker, retrieval, security, and deployment checks are defined in [Testing](docs/testing.md) and the active phase evidence matrices.

## Important Routes

Service/demo:

- `GET /`
- `GET /health`
- `GET /ready`
- `GET /api/deployment/status`
- `GET /api/demo/status`
- `GET /api/demo/scenarios`

Analysis:

- `POST /api/analyze`
- `GET /api/reports/{report_id}`
- `POST /api/reports/{report_id}/export`
- `POST /api/market-data/fetch`
- `POST /api/simulation/run`
- `POST /api/options/analyze`

Identity/account foundations:

- `/api/auth/*`
- `/api/account*`
- `/api/organizations*`
- `/api/theses*`
- `/api/usage`
- `/api/consents`
- `/api/account/privacy-preferences`

Durable-work foundations:

- `/api/jobs*`
- `/internal/workers/*` — trusted workers only; blocked by the browser BFF.

Controlled research/admin routes remain explicitly protected.

## Authoritative Documentation

- [Portfolio implementation profile](docs/portfolio_profile.md) — current scope and definition of done
- [Productization backlog](docs/productization_backlog.md) — deferred commercial/provider/launch requirements
- [Current state](docs/current_state.md) — deployed versus branch reality
- [Development plan](docs/development_plan.md) — roadmap and phase history
- [Phase 20 execution plan](docs/phase_20_execution_plan.md) — active portfolio sequence
- [Phase 20 threat model](docs/phase_20_threat_model.md) — cross-domain risk boundaries
- [Phase 20 evidence matrix](docs/phase_20_evidence_matrix.md) — current completion/evidence record
- [Future phase contracts](docs/future_phase_contracts.md) — broader product-capable target requirements
- [Phase 19 execution plan](docs/phase_19_execution_plan.md) — merged operational/security foundation and external gates
- [Phase 19 monitoring runbook](docs/operations/monitoring_and_alerting.md)
- [Phase 19 backup/restore runbook](docs/operations/backup_restore_runbook.md)
- [Phase 19 secret inventory](docs/operations/secret_inventory.md)
- [Phase 19 incident runbooks](docs/operations/incidents/)
- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Agent execution guide](docs/agent_execution_guide.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [RAG design](docs/rag_design.md)
- [Agent design](docs/agent_design.md)
- [Risk framework](docs/risk_framework.md)
- [Data sources](docs/data_sources.md)
- [Changelog](CHANGELOG.md)

## Short Agent Prompt

Future portfolio work should read the active profile before the broader product contracts:

```text
Implement the next approved V1 portfolio slice.
Read docs/portfolio_profile.md, docs/current_state.md,
docs/phase_20_execution_plan.md, docs/phase_20_evidence_matrix.md,
docs/architecture.md, docs/deployment.md, docs/testing.md,
and docs/agent_execution_guide.md.
Preserve productization boundaries in docs/productization_backlog.md.
Run all required checks, update evidence, commit logically, and do not merge.
```

## Safety Boundary

- no wallet connection;
- no transaction signing;
- no custody;
- no automated trade execution;
- no secret-key handling;
- no guaranteed-return language;
- no model override of deterministic risk fields;
- no automatic trust of discovered content;
- no live Vast rental in automated tests;
- no claim that synthetic or disabled provider paths are commercially live.

All output is research-oriented and educational. Market data may be delayed, incomplete, cached, simulated, or manually entered.

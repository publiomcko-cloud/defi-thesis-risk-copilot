# Development Plan — DeFi Thesis & Risk Copilot

## 1. Purpose

This document defines the active implementation plan for **DeFi Thesis & Risk Copilot**.

The goal is to transform the current documentation-first repository into a working MVP that demonstrates:

- full-stack product engineering
- generative AI integration
- retrieval-augmented generation
- controlled agentic workflows
- DeFi protocol analysis
- public market data adapters
- rule-based risk scoring
- structured report generation
- Dockerized local execution
- portfolio-ready deployment

This plan is intentionally written as a **Codex-ready execution plan**. Each phase includes objectives, files to create or edit, validation commands, acceptance criteria, dependencies, and out-of-scope boundaries.

---

## 1.1 Documentation Map

This implementation plan should be read together with the rest of the project documentation.

Important project documents:

```text
README.md
  Main portfolio-facing project overview, demo links, quick start, limitations, and roadmap.

docs/current_state.md
  Current implementation status, pending features, current stack, and known limitations.

docs/mvp_scope.md
  MVP boundaries, included features, excluded features, success criteria, and main use case.

docs/demo_architecture.md
  Demo architecture, local/public deployment model, safety boundaries, data flow, and demo screens.

docs/architecture.md
  Full system architecture, backend/frontend structure, RAG architecture, agent architecture, and safety architecture.

docs/data_sources.md
  Public/free data source plan, API adapter strategy, fallback behavior, and future premium data providers.

docs/rag_design.md
  RAG knowledge base, ingestion, chunking, metadata, retrieval, citations, and evaluation strategy.

docs/agent_design.md
  Controlled agent workflow, tool responsibilities, future multi-agent design, and automation boundaries.

docs/risk_framework.md
  Risk categories, rule-based scoring model, rating levels, stress scenarios, and future risk improvements.

docs/demo_script.md
  Step-by-step demo flow for the portfolio video.

docs/deployment.md
  Local and public deployment strategy, environment variables, and deployment safety.

docs/testing.md
  Backend, frontend, RAG, risk scoring, report, and smoke test strategy.

docs/portfolio_readiness.md
  Portfolio checklist, GitHub positioning, screenshots, video, and recruiter/client presentation.
```

Each implementation phase below includes a **Reference Documents** section. Before implementing that phase, Codex or any developer should read the listed documents and keep the implementation aligned with them.


---

## 2. Product Boundary

The MVP is a **research and risk analysis copilot**, not a trading bot.

The application must not:

- connect wallets
- request private keys
- request seed phrases
- sign transactions
- execute trades
- custody funds
- provide personalized financial advice
- promise returns
- hide missing data or assumptions

The application should:

- analyze DeFi strategies
- retrieve protocol documentation
- fetch or accept market data
- classify risk
- generate structured reports
- cite sources
- show assumptions and uncertainty
- remain safe for public portfolio demonstration

---

## 3. MVP Target

The MVP is complete when a user can open the app, submit a DeFi strategy prompt, and receive a structured, source-backed risk report.

Example demo prompt:

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

Expected output:

1. Executive summary.
2. Strategy description.
3. Protocols involved.
4. Strategy mechanics.
5. Yield source.
6. Market data summary.
7. Key assumptions.
8. Risk analysis.
9. Stress scenarios.
10. Exit plan.
11. Monitoring checklist.
12. Risk rating.
13. Missing data and uncertainty.
14. Sources.
15. Disclaimer.

---

## 4. Recommended Implementation Strategy

Build the project in layers:

```text
Repository foundation
    ↓
Backend foundation
    ↓
Frontend foundation
    ↓
Persistence layer
    ↓
RAG ingestion
    ↓
Market data adapters
    ↓
Risk framework
    ↓
Agent orchestration
    ↓
Report generation
    ↓
Docker + CI
    ↓
Demo polish
    ↓
Public deployment
```

Do not start with fine-tuning, wallet integration, trading automation, or paid APIs.

---

# Phase 0 — Documentation Cleanup and Repository Alignment

## Reference Documents

Read before implementation:

```text
README.md
docs/current_state.md
docs/mvp_scope.md
docs/demo_architecture.md
docs/portfolio_readiness.md
```

Use these documents to ensure repository links, active documentation, demo positioning, and portfolio presentation remain consistent.

## Objective

Prepare the repository for implementation by making documentation discoverable, consistent, and aligned with the MVP.

## Tasks

### Files to edit

```text
README.md
docs/development_plan.md
docs/demo_architecture.md
docs/current_state.md
```

### Required changes

1. Move the active development plan from:

```text
docs/archive/development_plan.md
```

to:

```text
docs/development_plan.md
```

2. Keep `docs/archive/development_plan.md` only if it is clearly marked as historical.

3. Add `docs/demo_architecture.md` to the README documentation list.

4. Add `docs/development_plan.md` to the README documentation list.

5. Fix the CI badge path from:

```text
YOUR_USERNAME
```

to:

```text
publiomcko-cloud
```

6. Confirm that all README links point to existing files.

## Validation

```bash
find docs -maxdepth 2 -type f | sort
grep -n "demo_architecture" README.md
grep -n "development_plan" README.md
grep -n "YOUR_USERNAME" README.md || true
```

## Acceptance Criteria

- README links to the active development plan.
- README links to the demo architecture document.
- CI badge no longer contains `YOUR_USERNAME`.
- The active implementation plan is located at `docs/development_plan.md`.
- Archive files are clearly historical.

## Out of Scope

- No backend code.
- No frontend code.
- No API implementation.

---

# Phase 1 — Repository Foundation

## Reference Documents

Read before implementation:

```text
README.md
docs/current_state.md
docs/architecture.md
docs/demo_architecture.md
docs/deployment.md
docs/testing.md
```

Use these documents to keep the initial backend, frontend, Docker, and validation structure aligned with the planned architecture and demo environment.

## Objective

Create the basic project structure for a full-stack application.

## Files to create

```text
.gitignore
.env.example
docker-compose.yml
docker-compose.production.yml

backend/
  requirements.txt
  pyproject.toml
  app/
    __init__.py
    main.py
    core/
      __init__.py
      config.py
      logging.py
      errors.py
    api/
      __init__.py
      routes_health.py
    tests/
      test_health.py
    scripts/
      run_smoke_checks.py

frontend/
  package.json
  tsconfig.json
  next.config.js
  src/
    app/
      page.tsx
      layout.tsx
    lib/
      api.ts
      types.ts
```

## Backend Tasks

1. Create FastAPI app.
2. Add `/health` endpoint.
3. Add basic settings through environment variables.
4. Add structured error placeholder.
5. Add initial pytest test for `/health`.
6. Add smoke check script.

## Frontend Tasks

1. Create minimal Next.js App Router project.
2. Add landing page.
3. Add shared API client placeholder.
4. Add TypeScript types placeholder.
5. Add basic project metadata.

## Docker Tasks

1. Add `docker-compose.yml` with placeholders for:

```text
backend
frontend
postgres
```

2. Do not add vector database yet unless pgvector is used immediately.

## Validation

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

Docker:

```bash
docker compose config
```

## Acceptance Criteria

- Backend starts locally.
- `/health` returns a valid JSON response.
- Backend tests pass.
- Frontend builds successfully.
- Docker Compose config is valid.
- Repository has clear backend and frontend folders.

## Out of Scope

- Database models.
- RAG.
- LLM calls.
- Market APIs.
- Report generation.

---

# Phase 2 — Backend API Foundation

## Reference Documents

Read before implementation:

```text
docs/architecture.md
docs/mvp_scope.md
docs/demo_architecture.md
docs/testing.md
```

Use these documents to keep API routes, schemas, endpoint contracts, and safety boundaries aligned with the MVP.

## Objective

Create the initial backend API structure for analysis requests, reports, protocols, and document ingestion.

## Files to create or edit

```text
backend/app/main.py
backend/app/api/routes_analysis.py
backend/app/api/routes_reports.py
backend/app/api/routes_protocols.py
backend/app/api/routes_documents.py
backend/app/api/routes_market_data.py
backend/app/schemas/
  __init__.py
  analysis.py
  reports.py
  protocols.py
  documents.py
  market_data.py
backend/app/services/
  __init__.py
  analysis_service.py
  report_service.py
  protocol_service.py
backend/app/tests/
  test_analysis_routes.py
  test_protocol_routes.py
```

## API Endpoints

Create these endpoints with mocked or in-memory responses first:

```text
GET  /health
POST /api/analyze
GET  /api/reports/{report_id}
GET  /api/protocols
POST /api/documents/ingest
POST /api/market-data/fetch
```

## Data Contracts

### POST /api/analyze request

```json
{
  "strategy_description": "string",
  "protocols": ["pendle", "morpho"],
  "market_url": "string or null",
  "manual_inputs": {
    "borrow_apy": 0.0,
    "implied_apy": 0.0,
    "liquidity_usd": 0.0,
    "ltv": 0.0,
    "lltv": 0.0
  },
  "analysis_depth": "standard"
}
```

### POST /api/analyze response

```json
{
  "report_id": "string",
  "status": "completed",
  "risk_rating": "Aggressive",
  "summary": "string"
}
```

## Validation

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python scripts/run_smoke_checks.py
```

Manual API check:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"strategy_description":"Analyze a Pendle PT strategy using Morpho borrow.","protocols":["pendle","morpho"],"manual_inputs":{},"analysis_depth":"standard"}'
```

## Acceptance Criteria

- API routes exist.
- Request and response schemas are typed with Pydantic.
- Mock analysis flow returns a report ID.
- Report retrieval endpoint returns a mock report.
- Protocol endpoint returns Pendle, Morpho, and Aave.
- Tests pass.

## Out of Scope

- Real RAG.
- Real market data.
- Real database persistence.
- Real LLM generation.

---

# Phase 3 — Frontend Foundation

## Reference Documents

Read before implementation:

```text
README.md
docs/demo_architecture.md
docs/demo_script.md
docs/portfolio_readiness.md
docs/mvp_scope.md
```

Use these documents to build the UI around the intended portfolio demo flow, not around a generic crypto dashboard.

## Objective

Build the first usable frontend flow: home page, strategy input page, and report page using mocked API responses.

## Files to create or edit

```text
frontend/src/app/page.tsx
frontend/src/app/analyze/page.tsx
frontend/src/app/reports/[reportId]/page.tsx
frontend/src/app/protocols/page.tsx
frontend/src/app/about/page.tsx

frontend/src/components/
  StrategyInputForm.tsx
  RiskRatingCard.tsx
  ReportSection.tsx
  SourcesPanel.tsx
  MonitoringChecklist.tsx
  DataSummaryTable.tsx
  DisclaimerBox.tsx

frontend/src/lib/
  api.ts
  types.ts
  formatting.ts
```

## UI Requirements

### Home page

Must include:

- project title
- project description
- demo safety summary
- supported protocols
- call to action to analyze a strategy

### Analyze page

Must include:

- strategy description textarea
- optional protocol selector
- optional market URL field
- optional manual inputs section
- submit button
- loading state

### Report page

Must include:

- executive summary
- risk rating card
- strategy mechanics
- assumptions
- risk sections
- sources panel
- disclaimer
- markdown export placeholder

## Validation

```bash
cd frontend
npm run lint
npm run build
```

## Acceptance Criteria

- Home page renders.
- Analyze page accepts user input.
- Submit action calls backend API.
- Report page renders returned report data.
- Frontend build passes.
- UI clearly states no wallet/trading execution.

## Out of Scope

- Authentication.
- Saved user accounts.
- Real-time alerts.
- Wallet connection.
- Payment or billing.

---

# Phase 4 — Persistence Layer

## Reference Documents

Read before implementation:

```text
docs/architecture.md
docs/demo_architecture.md
docs/data_sources.md
docs/testing.md
```

Use these documents to decide which entities must be persisted for reports, cached data, document metadata, and demo traceability.

## Objective

Add PostgreSQL persistence for reports, analysis requests, document metadata, and cached market data.

## Files to create or edit

```text
backend/app/db/
  __init__.py
  session.py
  base.py

backend/app/models/
  __init__.py
  analysis_request.py
  report.py
  document_source.py
  market_data_cache.py

backend/alembic.ini
backend/migrations/
backend/app/services/report_service.py
backend/app/services/analysis_service.py
```

## Database Tables

### analysis_requests

Fields:

```text
id
strategy_description
protocols
market_url
manual_inputs_json
analysis_depth
created_at
```

### reports

Fields:

```text
id
analysis_request_id
title
risk_rating
summary
report_markdown
report_json
created_at
```

### document_sources

Fields:

```text
id
protocol
source_type
title
source_url
content_hash
ingested_at
metadata_json
```

### market_data_cache

Fields:

```text
id
source
cache_key
payload_json
fetched_at
expires_at
```

## Validation

```bash
cd backend
alembic revision --autogenerate -m "add initial tables"
alembic upgrade head
python -m pytest -q
```

## Acceptance Criteria

- Alembic is configured.
- Initial database tables are created.
- Report endpoint reads from database.
- Analysis endpoint stores request and report.
- Tests pass against test database or SQLite test setup.

## Out of Scope

- User accounts.
- Row-level permissions.
- Production authentication.
- Billing data.

---

# Phase 5 — Knowledge Base and RAG MVP

## Reference Documents

Read before implementation:

```text
docs/rag_design.md
docs/data_sources.md
docs/agent_design.md
docs/testing.md
docs/mvp_scope.md
```

Use these documents to implement ingestion, chunking, metadata, embeddings, vector storage, retrieval, citation behavior, and RAG validation.

## Objective

Implement the first RAG pipeline over curated protocol documentation and internal risk notes.

## Files to create or edit

```text
knowledge_base/
  pendle/
    README.md
  morpho/
    README.md
  aave/
    README.md
  chainlink/
    README.md
  internal_notes/
    defi_risk_notes.md

backend/app/rag/
  __init__.py
  ingest.py
  loaders.py
  chunking.py
  embeddings.py
  vector_store.py
  retriever.py
  citations.py

backend/scripts/
  ingest_demo_docs.py
  evaluate_retrieval.py

backend/app/tests/
  test_chunking.py
  test_retriever.py
```

## RAG Tasks

1. Add local markdown document loader.
2. Add chunking logic.
3. Add metadata extraction.
4. Add embedding provider abstraction.
5. Add vector storage abstraction.
6. Add retrieval service.
7. Add citation formatting.
8. Add demo ingestion script.
9. Add retrieval evaluation script.

## MVP Embedding Options

Start with one of:

```text
sentence-transformers
OpenAI-compatible embeddings
local lightweight model
```

The embedding provider should be configurable.

## Retrieval Evaluation Questions

Create test questions:

```text
What is a Pendle PT?
What is maturity risk?
What is LLTV?
What is Health Factor?
What is oracle risk?
What is liquidation risk?
```

## Validation

```bash
cd backend
python scripts/ingest_demo_docs.py
python scripts/evaluate_retrieval.py
python -m pytest -q
```

## Acceptance Criteria

- Demo documents can be ingested.
- Chunks are stored with metadata.
- Retrieval returns relevant chunks.
- Retrieved chunks include protocol and source metadata.
- Analysis workflow can call retriever.
- Evaluation script prints retrieval results for test questions.

## Out of Scope

- Web crawling.
- Scheduled ingestion.
- Automatic documentation updates.
- Fine-tuned reranker.
- Large-scale vector search optimization.

---

# Phase 6 — Market Data Adapters

## Reference Documents

Read before implementation:

```text
docs/data_sources.md
docs/architecture.md
docs/mvp_scope.md
docs/testing.md
```

Use these documents to implement public/free data adapters, caching, manual fallback, and missing-data handling without making paid APIs mandatory.

## Objective

Add basic public data adapters with caching and manual fallback.

## Files to create or edit

```text
backend/app/data_sources/
  __init__.py
  base.py
  manual.py
  coingecko.py
  defillama.py
  morpho.py
  aave.py
  pendle.py

backend/app/services/market_data_service.py
backend/app/tests/test_market_data_adapters.py
```

## Adapter Interface

Each adapter should implement:

```python
class DataSourceAdapter:
    name: str

    def fetch(self, query: dict) -> dict:
        ...

    def normalize(self, raw: dict) -> dict:
        ...
```

## MVP Adapters

### Manual adapter

Accepts user-provided values:

- borrow APY
- implied APY
- liquidity
- maturity date
- LTV
- LLTV
- collateral asset
- debt asset

### DefiLlama adapter

Use for:

- protocol TVL
- category
- yield data when available

### CoinGecko adapter

Use for:

- token price
- market cap
- 24h volume

### Morpho adapter

Use for:

- market metadata
- collateral asset
- loan asset
- LLTV
- borrow APY when available

### Aave adapter

Use for:

- reserve data
- supply APY
- borrow APY
- collateral parameters when available

### Pendle adapter

For MVP, this can start as:

- manual fallback
- placeholder API adapter
- future integration point

## Fallback Rule

```text
Try live API
    -> if unavailable, use cache
    -> if cache unavailable, use manual input
    -> if still missing, mark field as unknown
```

## Validation

```bash
cd backend
python -m pytest backend/app/tests/test_market_data_adapters.py -q
```

## Acceptance Criteria

- Data adapters have consistent normalized outputs.
- API failures do not crash analysis.
- Missing data is explicitly marked.
- Manual fallback works.
- Market data summary is included in report JSON.

## Out of Scope

- Paid API providers.
- High-frequency polling.
- Real-time websocket feeds.
- Wallet-specific portfolio data.

---

# Phase 7 — Risk Framework and Scoring

## Reference Documents

Read before implementation:

```text
docs/risk_framework.md
docs/mvp_scope.md
docs/demo_architecture.md
docs/testing.md
```

Use these documents to keep risk scoring explainable, deterministic, safe, and aligned with the four MVP risk ratings.

## Objective

Implement the rule-based MVP risk scoring engine.

## Files to create or edit

```text
backend/app/risk/
  __init__.py
  framework.py
  scoring.py
  scenarios.py
  checklist.py

backend/app/tests/
  test_risk_scoring.py
  test_stress_scenarios.py
```

## Risk Categories

The MVP must evaluate:

- protocol risk
- market risk
- liquidity risk
- oracle risk
- liquidation risk
- borrow rate risk
- maturity risk
- composability risk
- operational risk
- incentive risk

## Risk Ratings

Supported ratings:

```text
Conservative
Moderate
Aggressive
Very Risky
```

## Initial Scoring Logic

Example scoring:

```text
Base risk: 1

+1 if strategy uses more than one protocol
+1 if strategy uses leverage
+1 if collateral is volatile
+1 if borrow APY is variable
+1 if liquidity is low or unknown
+1 if exit depends on secondary market
+1 if oracle risk is unclear
+1 if maturity timing creates exit risk
+1 if incentives are important to yield
+1 if documentation or data is incomplete
```

Suggested mapping:

```text
0-2: Conservative
3-4: Moderate
5-6: Aggressive
7+: Very Risky
```

## Stress Scenarios

Generate basic stress scenarios:

- collateral price drops 10%
- borrow APY doubles
- liquidity drops 50%
- user exits before maturity
- oracle data becomes unavailable
- incentives disappear

## Validation

```bash
cd backend
python -m pytest backend/app/tests/test_risk_scoring.py -q
python -m pytest backend/app/tests/test_stress_scenarios.py -q
```

## Acceptance Criteria

- Risk scoring is deterministic.
- Score components are visible.
- Missing data increases uncertainty.
- Stress scenarios are generated.
- Monitoring checklist is generated.
- Tests cover conservative, moderate, aggressive, and very risky cases.

## Out of Scope

- Quantitative liquidation engine.
- Backtesting.
- Monte Carlo simulation.
- ML-based risk classifier.

---

# Phase 8 — Controlled Agent Orchestration

## Reference Documents

Read before implementation:

```text
docs/agent_design.md
docs/rag_design.md
docs/risk_framework.md
docs/demo_architecture.md
docs/mvp_scope.md
```

Use these documents to keep the agent workflow controlled, source-grounded, non-autonomous, and safe for the MVP.

## Objective

Connect RAG, market data, risk scoring, and report generation into one controlled analysis workflow.

## Files to create or edit

```text
backend/app/agents/
  __init__.py
  orchestrator.py
  strategy_parser.py
  protocol_research_agent.py
  market_data_agent.py
  risk_scoring_agent.py
  report_writer_agent.py

backend/app/services/analysis_service.py
backend/app/tests/test_analysis_workflow.py
```

## Workflow

```text
User request
    ↓
Parse strategy
    ↓
Detect protocols
    ↓
Retrieve documentation
    ↓
Fetch market data
    ↓
Normalize inputs
    ↓
Run risk scoring
    ↓
Generate report
    ↓
Store report
    ↓
Return report ID
```

## Implementation Rules

- Keep workflow deterministic where possible.
- Avoid open-ended autonomous loops in MVP.
- LLM should synthesize and write, not invent unsupported data.
- Every report must include missing data and disclaimer.
- If RAG retrieval fails, generate a partial report with warning.

## Validation

```bash
cd backend
python -m pytest backend/app/tests/test_analysis_workflow.py -q
python scripts/run_smoke_checks.py
```

## Acceptance Criteria

- `/api/analyze` runs complete workflow.
- Report is persisted.
- Report includes RAG sources.
- Report includes market data summary.
- Report includes risk rating.
- Report includes disclaimer.
- API returns report ID and summary.

## Out of Scope

- Multi-agent autonomy.
- Tool execution beyond internal safe tools.
- Human-in-the-loop queue.
- Scheduled monitoring.

---

# Phase 9 — Report Generation and Markdown Export

## Reference Documents

Read before implementation:

```text
docs/mvp_scope.md
docs/demo_script.md
docs/portfolio_readiness.md
docs/risk_framework.md
docs/rag_design.md
```

Use these documents to ensure every report includes the required sections, sources, assumptions, missing data, risk rating, and disclaimer.

## Objective

Create a consistent, portfolio-quality report format.

## Files to create or edit

```text
backend/app/reports/
  __init__.py
  templates.py
  renderer.py
  markdown_export.py

backend/app/tests/test_report_generation.py
frontend/src/components/ReportSection.tsx
frontend/src/components/MarkdownExportButton.tsx
```

## Report Template

Every report must include:

```text
1. Executive Summary
2. Strategy Description
3. Protocols Involved
4. Strategy Mechanics
5. Yield Source
6. Market Data Summary
7. Key Assumptions
8. Risk Analysis
9. Stress Scenarios
10. Exit Plan
11. Monitoring Checklist
12. Risk Rating
13. Missing Data and Uncertainty
14. Sources
15. Disclaimer
```

## Export

Support:

- rendered UI report
- JSON report payload
- Markdown export

## Validation

```bash
cd backend
python -m pytest backend/app/tests/test_report_generation.py -q
```

Frontend:

```bash
cd frontend
npm run build
```

## Acceptance Criteria

- Report structure is consistent.
- Markdown export works.
- Sources are visible.
- Missing data is visible.
- Disclaimer is always present.
- UI renders all required report sections.

## Out of Scope

- PDF export.
- Email delivery.
- Public sharing links.
- Team collaboration.

---

# Phase 10 — Docker, Local Environment, and CI

## Reference Documents

Read before implementation:

```text
docs/deployment.md
docs/testing.md
docs/demo_architecture.md
README.md
```

Use these documents to keep Docker, local execution, CI, and README quick-start commands consistent.

## Objective

Make the project easy to run and validate locally.

## Files to create or edit

```text
Dockerfile.backend
Dockerfile.frontend
docker-compose.yml
docker-compose.production.yml
.env.example

.github/workflows/ci.yml
```

## Docker Services

Recommended local services:

```text
backend
frontend
postgres
vector-db or pgvector
ollama, optional
```

## CI Jobs

Minimum CI should run:

- backend tests
- frontend lint
- frontend build
- Docker Compose config check

## Validation

```bash
docker compose config
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

CI local equivalent:

```bash
cd backend && python -m pytest -q
cd frontend && npm run lint && npm run build
docker compose config
```

## Acceptance Criteria

- Docker Compose starts core services.
- Backend health endpoint is reachable.
- Frontend is reachable.
- CI workflow exists.
- README quick start commands match real commands.

## Out of Scope

- Kubernetes.
- Terraform.
- Advanced deployment automation.
- Production monitoring.

---

# Phase 11 — Demo Data and Example Reports

## Reference Documents

Read before implementation:

```text
docs/demo_script.md
docs/portfolio_readiness.md
docs/mvp_scope.md
docs/risk_framework.md
docs/rag_design.md
```

Use these documents to create demo assets that clearly show the intended Pendle/Morpho/Aave analysis workflow.

## Objective

Create realistic demo assets for portfolio presentation.

## Files to create or edit

```text
examples/
  pendle_morpho_loop_report.md
  aave_lending_risk_report.md
  sample_analysis_request.json
  sample_analysis_response.json

knowledge_base/internal_notes/
  sample_defi_strategy_notes.md

docs/demo_script.md
docs/portfolio_readiness.md
```

## Demo Requirements

The demo must include:

- one complete Pendle + Morpho example
- one Aave lending risk example
- one report with missing data warnings
- one report with visible sources
- one markdown export example

## Validation

```bash
cd backend
python scripts/run_smoke_checks.py
```

Manual validation:

1. Open frontend.
2. Submit demo prompt.
3. Review generated report.
4. Export Markdown.
5. Compare with example report.

## Acceptance Criteria

- At least one full example report exists.
- Demo prompt works.
- Demo can be shown in under four minutes.
- README can link to example report.
- Report is safe and non-advisory.

## Out of Scope

- Real financial recommendations.
- Live production market monitoring.
- Automatic trading.

---

# Phase 12 — Public Portfolio Deployment

## Reference Documents

Read before implementation:

```text
docs/deployment.md
docs/demo_architecture.md
docs/current_state.md
docs/portfolio_readiness.md
README.md
```

Use these documents to update public links, hosting decisions, deployment notes, and demo safety language.

## Objective

Deploy the MVP demo publicly.

## Suggested Deployment

```text
Frontend: Vercel
Backend: Render
Database: Supabase PostgreSQL
Vector storage: pgvector, Qdrant, or Chroma
LLM: hosted OpenAI-compatible provider or local-only demo fallback
```

## Files to update

```text
README.md
docs/current_state.md
docs/deployment.md
docs/portfolio_readiness.md
```

## Deployment Tasks

1. Deploy frontend.
2. Deploy backend.
3. Configure CORS.
4. Configure environment variables.
5. Configure database.
6. Run migrations.
7. Ingest demo docs.
8. Test public `/health`.
9. Test public API docs.
10. Test full frontend flow.
11. Update README links.

## Validation

```bash
curl https://BACKEND_URL/health
```

Frontend:

```text
Open deployed frontend
Submit demo strategy
Open generated report
Check sources and disclaimer
```

## Acceptance Criteria

- Public frontend link works.
- Public backend health link works.
- Public API docs link works.
- Demo prompt works.
- README contains deployed links.
- Known limitations are explicit.
- Demo video can be recorded.

## Out of Scope

- Paid subscription.
- User login.
- Production user data.
- Production financial workflows.

---

# Phase 13 — Portfolio Polish

## Reference Documents

Read before implementation:

```text
README.md
docs/portfolio_readiness.md
docs/demo_script.md
docs/case_study.md
docs/current_state.md
```

Use these documents to make the repository clear for recruiters, clients, and demo reviewers.

## Objective

Make the repository portfolio-ready.

## Files to update

```text
README.md
docs/current_state.md
docs/case_study.md
docs/demo_script.md
docs/portfolio_readiness.md
docs/screenshots/
```

## Tasks

1. Add screenshots.
2. Add demo video link.
3. Add deployed frontend link.
4. Add backend health link.
5. Add API docs link.
6. Add example reports.
7. Add architecture diagram.
8. Add final known limitations.
9. Add final roadmap.
10. Add LinkedIn-ready summary.

## Acceptance Criteria

- README looks complete.
- Screenshots render in GitHub.
- Demo links work.
- Documentation is easy to navigate.
- Recruiter can understand the project in less than five minutes.
- Client can understand the business value in less than five minutes.

---

# Future Phase A — Source Monitoring and Automated Evaluation

## Reference Documents

Read before implementation:

```text
docs/data_sources.md
docs/agent_design.md
docs/rag_design.md
docs/demo_architecture.md
```

Use these documents to keep source monitoring safe, reviewable, and compatible with RAG ingestion.

## Objective

Add background monitoring for new DeFi products, markets, vaults, and documentation updates.

## Sources to monitor

- Pendle markets
- Morpho vaults
- Aave reserves
- DefiLlama yields
- Dune queries
- The Graph subgraphs
- governance forums
- protocol documentation
- Chainlink feeds

## Workflow

```text
Source Monitor
    ↓
Crawler or API Collector
    ↓
New Item Detector
    ↓
Data Normalizer
    ↓
AI Evaluation Agent
    ↓
Risk / Opportunity Scoring
    ↓
Human Review
    ↓
RAG Ingestion Pipeline
    ↓
Vector Database + Knowledge Base
```

## MVP Safety Rule

Start with:

```text
automatic discovery + automatic evaluation + manual approval
```

Only later allow fully automatic ingestion for trusted sources.

---

# Future Phase B — Watchlist and Alerts

## Reference Documents

Read before implementation:

```text
docs/risk_framework.md
docs/data_sources.md
docs/demo_architecture.md
docs/mvp_scope.md
```

Use these documents to ensure alerts remain analytical and risk-focused, not trading signals.

## Objective

Allow users to monitor strategies or markets.

## Possible Alerts

- borrow APY rises above strategy yield
- liquidity drops below threshold
- LTV approaches danger zone
- Health Factor approaches liquidation risk
- PT maturity approaches
- TVL changes significantly
- governance proposal affects parameters
- oracle source changes
- incentives decrease
- strategy spread turns negative

## Out of Scope for MVP

- push notifications
- email alerts
- paid alerting system
- wallet-specific monitoring

---

# Future Phase C — Strategy Simulator

## Reference Documents

Read before implementation:

```text
docs/risk_framework.md
docs/architecture.md
docs/mvp_scope.md
```

Use these documents to keep simulation deterministic, transparent, and non-advisory.

## Objective

Add deterministic scenario simulation.

## Scenarios

- collateral drops 5%, 10%, 20%, 30%
- borrow APY rises
- liquidity falls
- slippage increases
- exit occurs before maturity
- incentives disappear
- oracle delay occurs
- gas costs increase

## Outputs

- estimated LTV impact
- estimated liquidation buffer
- estimated net yield impact
- estimated exit loss
- updated risk rating

---

# Future Phase D — Options and Volatility Agent

## Reference Documents

Read before implementation:

```text
docs/agent_design.md
docs/risk_framework.md
docs/data_sources.md
docs/mvp_scope.md
```

Use these documents to keep options analysis analytical, source-aware, and non-advisory.

## Objective

Add support for Derive-style crypto options analysis.

## Features

- call analysis
- put analysis
- strike analysis
- expiration analysis
- implied volatility
- bid/ask spread
- breakeven
- maximum loss
- risk/reward scenarios
- volatility thesis

## Safety

The agent must remain analytical and non-advisory.

---

# Future Phase E — Fine-Tuning

## Reference Documents

Read before implementation:

```text
docs/rag_design.md
docs/risk_framework.md
docs/agent_design.md
docs/testing.md
```

Use these documents to decide where fine-tuning adds real value: risk classification, RAG reranking, strategy classification, or report style.

## Objective

Use fine-tuning after enough examples and labeled data exist.

## Possible Models

1. Risk classifier.
2. RAG reranker.
3. Strategy type classifier.
4. Report style model.

## Recommended Order

```text
1. Build RAG + agents first.
2. Save generated reports.
3. Create labeled examples.
4. Fine-tune risk classifier.
5. Fine-tune reranker.
6. Consider LoRA for report style only after the system is useful.
```

## Technologies

- PyTorch
- Hugging Face Transformers
- sentence-transformers
- LoRA, optional
- NeMo, optional future experiment

---

# Future Phase F — HPC and SLURM Readiness

## Reference Documents

Read before implementation:

```text
docs/architecture.md
docs/deployment.md
docs/testing.md
docs/rag_design.md
```

Use these documents to align HPC batch jobs with ingestion, embedding generation, evaluation, and future training tasks.

## Objective

Add HPC-ready scripts for batch processing and model experiments.

## Use Cases

- batch document ingestion
- large-scale embedding generation
- risk classifier training
- retrieval evaluation
- multi-model benchmarking
- fine-tuning experiments

## Files

```text
hpc/
  slurm_generate_embeddings.sbatch
  slurm_train_risk_classifier.sbatch
  slurm_evaluate_retrieval.sbatch
  apptainer.def
```

## Out of Scope for MVP

- real cluster dependency
- mandatory SLURM execution
- expensive large-model training

---

# Final MVP Checklist

The MVP is ready when:

- [ ] README is complete and links all active docs.
- [ ] `docs/development_plan.md` is active and current.
- [ ] `docs/demo_architecture.md` is linked from README.
- [ ] FastAPI backend runs locally.
- [ ] Next.js frontend runs locally.
- [ ] PostgreSQL persistence works.
- [ ] RAG ingestion works with demo docs.
- [ ] Retrieval returns source metadata.
- [ ] Market data adapters support public/free data or manual fallback.
- [ ] Risk scoring works.
- [ ] Analysis workflow creates a report.
- [ ] Report page renders in frontend.
- [ ] Markdown export works.
- [ ] Docker Compose works.
- [ ] Backend tests pass.
- [ ] Frontend build passes.
- [ ] Demo prompt works.
- [ ] Public demo links are updated.
- [ ] Demo video is recorded.
- [ ] Known limitations are explicit.
- [ ] No wallet connection exists.
- [ ] No trade execution exists.
- [ ] No private key handling exists.

---

# Codex Execution Guidance

When using Codex, implement one phase at a time.

Before implementing a phase, read the phase-specific **Reference Documents** listed in that phase. Do not implement from this plan alone when a specialized document exists.

Recommended instruction format:

```text
Implement Phase X from docs/development_plan.md.

Follow the existing project documentation and do not add wallet connection, transaction signing, trade execution, or paid API dependencies.

After implementation, run the validation commands listed in that phase and summarize:
1. files changed
2. commands run
3. tests passed or failed
4. remaining issues
```

This keeps implementation controlled, auditable, and aligned with the safe MVP boundary.

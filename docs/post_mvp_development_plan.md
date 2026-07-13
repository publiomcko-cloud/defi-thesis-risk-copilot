# Post-MVP Development Plan — DeFi Thesis & Risk Copilot

## 1. Purpose

This document defines the active product development plan after the Phase 10 MVP checkpoint.

The MVP foundation is now treated as complete through Phase 10:

```text
Phase 0-5: repository, backend, frontend, persistence, RAG MVP
Phase 6: market data adapters
Phase 7: rule-based risk framework
Phase 8: controlled agent orchestration
Phase 9: structured reports and Markdown export
Phase 10: Docker, local environment, and CI
```

The next work should improve the actual product before final portfolio polishing. The original MVP phases 11, 12, and 13 are intentionally moved to the end of this plan because they are portfolio/demo/deployment actions rather than core product intelligence work.

## 2. Current Baseline

Current baseline capabilities:

- FastAPI backend.
- Next.js frontend.
- SQLite/PostgreSQL persistence through SQLAlchemy and Alembic.
- Local curated RAG knowledge base.
- Lightweight local hash embeddings and JSON vector store.
- Manual, Pendle, Morpho, Aave, DefiLlama, and CoinGecko adapter layer.
- Controlled analysis workflow.
- Deterministic rule-based risk scoring.
- Structured report generation.
- Markdown export.
- Docker Compose and CI.

Current known limitations:

- Report writing has deterministic fallback behavior with optional LLM synthesis.
- RAG is local and curated only.
- Several protocol adapters are still manual fallback adapters.
- Source monitoring is manually triggered and discovery remains curated.
- Review queue foundations exist for newly discovered markets or sources.
- Strategy simulation is deterministic and scenario-based.
- Watchlists and in-app alerts are implemented for manual evaluation.
- Options and volatility analysis is deterministic and educational.
- Advanced RAG has optional hybrid retrieval, local semantic signals, reranking, citation validation, and evaluation metrics.
- Fine-tuning and HPC support are not implemented.

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

The application may:

- analyze public protocol data
- summarize strategy mechanics
- classify strategy risk
- simulate risk scenarios
- monitor public sources
- queue discoveries for human review
- ingest approved sources into the knowledge base
- generate educational, non-advisory reports

## 4. Active Phase Order

Recommended implementation order:

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
Final Phase 11: Demo data and example reports
Final Phase 12: Public portfolio deployment
Final Phase 13: Portfolio polish
```

## 5. Post-MVP Phase 1 — Optional Backend LLM Synthesis

### Objective

Add optional LLM-backed report synthesis while preserving deterministic fallback behavior.

The LLM should improve explanation quality, not replace risk scoring.

### Files to create or edit

```text
backend/app/llm/
  __init__.py
  base.py
  providers.py
  prompts.py
  synthesis.py

backend/app/agents/report_writer_agent.py
backend/app/core/config.py
backend/app/reports/templates.py
backend/app/tests/test_llm_synthesis.py
.env.example
docs/current_state.md
docs/architecture.md
docs/agent_design.md
docs/rag_design.md
```

### Tasks

1. Add an LLM provider abstraction.
2. Support `LLM_PROVIDER=disabled`, `ollama`, or `openai_compatible`.
3. Keep deterministic template generation as fallback.
4. Pass only structured context to the LLM:
   - user strategy
   - retrieved RAG chunks
   - market data summary
   - risk score components
   - missing data
   - required report sections
   - safety rules
5. Require the LLM output to preserve:
   - risk rating
   - missing data
   - sources
   - disclaimer
6. Add timeout and error handling.
7. Add tests that prove the app still works with `LLM_PROVIDER=disabled`.

### Acceptance Criteria

- The app works with no LLM configured.
- The report writer can optionally call an LLM.
- Risk score remains deterministic.
- LLM failure returns a valid deterministic report.
- No financial advice or trade instructions are generated.

### Out of Scope

- Fine-tuning.
- Autonomous agent loops.
- Wallet integration.
- Trading automation.

## 6. Post-MVP Phase 2 — Source Monitoring and Discovery

### Objective

Build a controlled source monitoring layer that discovers new DeFi items from public sources.

Start with manually triggered monitoring, not background automation.

### Initial source types

```text
Pendle markets
Morpho markets or vaults
Aave reserves
DefiLlama protocol/yield data
Protocol documentation pages
Governance forum pages
Risk/audit report links
```

### Files to create or edit

```text
backend/app/monitoring/
  __init__.py
  sources.py
  collectors.py
  normalizer.py
  discovery_service.py
  schemas.py

backend/app/api/routes_monitoring.py
backend/app/models/discovered_item.py
backend/app/models/source_watch.py
backend/migrations/versions/<new_revision>_add_monitoring_tables.py
backend/app/tests/test_source_monitoring.py
docs/data_sources.md
docs/agent_design.md
docs/architecture.md
```

### Tasks

1. Add source watch definitions.
2. Add a discovered item model.
3. Add manual trigger endpoint:

```text
POST /api/monitoring/run
GET  /api/monitoring/discovered-items
```

4. Normalize discovered items into a common schema:

```text
id
source
source_type
title
url
protocol
chain
asset
market_identifier
discovered_at
raw_payload
status
```

5. Mark all discoveries as `needs_review` by default.
6. Do not ingest automatically into RAG yet.

### Acceptance Criteria

- Manual monitoring run creates normalized discovered items.
- Duplicate discoveries are detected.
- Failures are recorded without crashing the app.
- Newly discovered items are not trusted automatically.

### Out of Scope

- Scheduled jobs.
- Email/push alerts.
- Automatic RAG ingestion.
- Trading signals.

## 7. Post-MVP Phase 3 — Automated Evaluation Pipeline and Review Queue

### Objective

Evaluate discovered items with the existing analysis workflow and place them into a human review queue.

### Files to create or edit

```text
backend/app/evaluation/
  __init__.py
  evaluator.py
  review_queue.py
  schemas.py

backend/app/api/routes_evaluation.py
backend/app/models/evaluation_result.py
backend/app/models/review_item.py
backend/migrations/versions/<new_revision>_add_evaluation_tables.py
frontend/src/app/review/page.tsx
frontend/src/components/ReviewQueueTable.tsx
backend/app/tests/test_evaluation_pipeline.py
```

### Workflow

```text
Discovered item
    -> normalize item
    -> enrich with available data
    -> run controlled analysis workflow
    -> generate risk summary
    -> create review item
    -> human approves, rejects, or marks needs research
```

### Review statuses

```text
needs_review
approved_for_rag
rejected
needs_more_data
archived
```

### Acceptance Criteria

- A discovered item can be evaluated.
- Evaluation creates a structured risk summary.
- Review status can be updated.
- Approved items can be prepared for RAG ingestion, but not silently ingested.
- All uncertainty remains visible.

### Out of Scope

- Fully autonomous approval.
- Production background workers.
- Public alert delivery.

## 8. Post-MVP Phase 4 — Strategy Simulator

### Objective

Add a deterministic simulator for strategy stress testing.

The simulator should help explain possible outcomes under assumptions. It must not recommend entering or exiting a position.

### Simulation types

```text
net spread estimate
borrow APY shock
liquidity/slippage shock
collateral drawdown
LTV and liquidation buffer approximation
early exit before maturity
incentive removal
combined adverse scenario
```

### Files to create or edit

```text
backend/app/simulation/
  __init__.py
  schemas.py
  spread.py
  ltv.py
  scenarios.py
  simulator.py

backend/app/api/routes_simulation.py
frontend/src/app/simulate/page.tsx
frontend/src/components/SimulationPanel.tsx
backend/app/tests/test_strategy_simulator.py
docs/risk_framework.md
docs/architecture.md
```

### Acceptance Criteria

- Simulator accepts explicit user inputs.
- Simulator returns deterministic scenarios.
- Results show assumptions and missing data.
- Reports can include a simulation section.
- No simulation output is framed as a guarantee.

## 9. Post-MVP Phase 5 — Watchlist and Alerts

### Objective

Add a user-visible watchlist for strategies, protocols, markets, or discovered items.

Start with in-app alerts only.

### Alert types

```text
borrow APY above threshold
net spread below threshold
liquidity below threshold
maturity date approaching
risk score changed
missing data resolved
new discovered item needs review
source update detected
```

### Files to create or edit

```text
backend/app/watchlist/
  __init__.py
  schemas.py
  rules.py
  service.py

backend/app/api/routes_watchlist.py
backend/app/models/watchlist_item.py
backend/app/models/alert_event.py
backend/migrations/versions/<new_revision>_add_watchlist_tables.py
frontend/src/app/watchlist/page.tsx
frontend/src/components/WatchlistTable.tsx
frontend/src/components/AlertEventsPanel.tsx
backend/app/tests/test_watchlist_alerts.py
```

### Acceptance Criteria

- Users can create a watchlist item.
- Rules can be evaluated manually.
- Alert events are stored and displayed.
- No push/email delivery is required yet.

### Out of Scope

- Automated trading.
- Real-time streaming infrastructure.
- Personalized investment recommendations.

## 10. Post-MVP Phase 6 — Options and Volatility Analysis Agent

### Objective

Add an options and volatility analysis workflow for Derive-style crypto options.

This phase supports educational options analysis, not trade recommendations.

### Concepts to support

```text
call and put mechanics
strike
expiration
premium
implied volatility
bid/ask spread
breakeven
max loss
risk/reward framing
volatility thesis
basic scenario table
```

### Files to create or edit

```text
backend/app/options/
  __init__.py
  schemas.py
  payoff.py
  volatility.py
  analysis.py

backend/app/api/routes_options.py
frontend/src/app/options/page.tsx
frontend/src/components/OptionsAnalysisForm.tsx
frontend/src/components/OptionsScenarioTable.tsx
backend/app/tests/test_options_analysis.py
docs/risk_framework.md
docs/agent_design.md
```

### Acceptance Criteria

- User can input option parameters manually.
- Backend calculates breakeven and payoff scenarios.
- Report explains risks and uncertainty.
- Output avoids direct buy/sell instructions.

## 11. Post-MVP Phase 7 — Advanced RAG and Retrieval Evaluation

### Objective

Improve retrieval quality beyond local hash embeddings.

### Improvements

```text
semantic embedding provider
hybrid keyword + vector search
metadata filters
freshness scoring
source quality scoring
reranking
citation validation
retrieval evaluation dataset
```

### Files to create or edit

```text
backend/app/rag/semantic_embeddings.py
backend/app/rag/hybrid_retriever.py
backend/app/rag/reranker.py
backend/app/rag/evaluation.py
backend/scripts/build_retrieval_eval_dataset.py
backend/scripts/evaluate_retrieval.py
docs/rag_design.md
backend/app/tests/test_advanced_retrieval.py
```

### Acceptance Criteria

- Existing local retrieval still works.
- Semantic retrieval can be enabled optionally.
- Evaluation metrics are recorded.
- Retrieved sources are cited and validated.

## 12. Post-MVP Phase 8 — Fine-Tuning and ML Risk Classifier Groundwork

### Objective

Prepare training data and baseline models for future fine-tuning.

Do not fine-tune before enough labeled examples exist.

### Files to create or edit

```text
model-training/
  datasets/
  scripts/
  notebooks/
  README.md

backend/app/ml/
  __init__.py
  dataset_export.py
  risk_classifier.py

backend/scripts/export_training_dataset.py
docs/risk_framework.md
docs/rag_design.md
docs/post_mvp_development_plan.md
```

### Tasks

1. Export historical analysis reports as candidate training examples.
2. Define labels:
   - risk rating
   - main risk drivers
   - protocol category
   - missing data severity
   - strategy type
3. Build a baseline classifier before any fine-tuning.
4. Keep model output advisory to the rule-based engine, not authoritative.

### Acceptance Criteria

- Dataset export script exists.
- Label schema is documented.
- Baseline classifier interface exists.
- No model silently overrides deterministic scoring.

## 13. Post-MVP Phase 9 — HPC and SLURM Readiness

### Objective

Prepare optional HPC workflows for batch ingestion, embedding generation, retrieval evaluation, and model training.

### Files to create

```text
hpc/
  slurm_generate_embeddings.sbatch
  slurm_evaluate_retrieval.sbatch
  slurm_train_risk_classifier.sbatch
  apptainer.def
  README.md
```

### Acceptance Criteria

- SLURM examples are documented.
- Apptainer/Singularity container definition exists.
- Scripts are optional and do not affect local MVP execution.

## 14. Final Phase 11 — Demo Data and Example Reports

This phase remains after the active product-expansion phases.

Purpose:

- create polished example reports
- create repeatable demo inputs
- update screenshots
- prepare demo script
- create showcase-ready sample data

## 15. Final Phase 12 — Public Portfolio Deployment

This phase remains after demo data is stable.

Purpose:

- deploy frontend
- deploy backend
- configure database
- configure environment variables
- test public demo links
- update README with live links

## 16. Final Phase 13 — Portfolio Polish

This phase remains last.

Purpose:

- polish UI screenshots
- record demo video
- finalize README presentation
- improve case study language
- update portfolio readiness checklist
- prepare LinkedIn/GitHub presentation material

## 17. Codex Execution Prompt

Use this template for each post-MVP phase:

```text
Implement Post-MVP Phase X from docs/post_mvp_development_plan.md.

Do not implement wallet connection, transaction signing, trade execution, custody, or personalized financial advice.

Preserve the existing Phase 10 MVP behavior and tests.

After implementation, run:
- cd backend && source .venv/bin/activate && python -m pytest -q
- cd frontend && npm run lint
- cd frontend && npm run build
- docker compose config

Summarize:
1. files changed
2. commands run
3. tests passed or failed
4. remaining issues
5. whether the project is ready for the next post-MVP phase
```

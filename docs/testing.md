# Testing — DeFi Thesis & Risk Copilot

## 1. Testing Goals

Testing should validate:

- backend API behavior
- risk scoring consistency
- RAG retrieval quality
- report generation structure
- data adapter fallbacks
- frontend build quality
- Docker configuration
- post-MVP source monitoring and evaluation workflows
- simulation and alert logic
- optional LLM synthesis fallback behavior

## 2. Baseline Validation

Before implementing any post-MVP phase, the Phase 10 baseline should pass:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python scripts/run_smoke_checks.py

cd ../frontend
npm run lint
npm run build

cd ..
docker compose config
docker compose -f docker-compose.production.yml config
```

## 3. Backend Tests

Recommended test areas:

- analysis endpoint
- report endpoint
- document ingestion
- retriever behavior
- risk scoring
- data adapter normalization
- missing data handling
- disclaimer presence
- Markdown export
- Alembic migrations from a clean database

## 4. Frontend Tests

Run:

```bash
cd frontend
npm run lint
npm run build
```

Future:

```bash
npm run test:e2e
```

Important UI flows:

- home page loads
- analyze page accepts basic and advanced manual inputs
- analysis redirects to report page
- report page displays risk rating and sections
- Markdown export renders
- error states are readable

## 5. RAG Tests

RAG evaluation questions:

- What is a Pendle PT?
- What is fixed yield?
- What is LLTV?
- What is Health Factor?
- What is liquidation risk?
- What is oracle risk?
- What is maturity risk?

The retriever should return relevant protocol chunks for each question.

Post-MVP RAG tests should also validate:

- semantic retrieval provider behavior
- hybrid retrieval behavior
- reranker behavior
- metadata filters
- citation validation
- stale-source detection
- evaluation dataset regressions

## 6. Risk Scoring Tests

Risk scoring should be deterministic.

Example tests:

- single-protocol no leverage strategy
- multi-protocol strategy
- leveraged strategy
- unknown liquidity
- volatile collateral
- variable borrow rate
- missing oracle data
- missing RAG context

## 7. Report Tests

Every generated report should include:

- executive summary
- protocols involved
- strategy mechanics
- assumptions
- risk rating
- missing data
- sources
- disclaimer
- Markdown export

If optional LLM synthesis is added, tests must confirm:

- deterministic fallback works with `LLM_PROVIDER=disabled`
- LLM timeout does not break report generation
- LLM output preserves risk rating, missing data, sources, and disclaimer
- LLM synthesis assumptions clearly state whether synthesis was used or skipped

The current local Ollama validation record is documented in `docs/llm_synthesis_validation.md`.

## 8. Post-MVP Source Monitoring Tests

When source monitoring is implemented, tests should validate:

- source watch creation
- manual monitoring run
- collector failure handling
- duplicate discovered item detection
- normalized discovered item schema
- `needs_review` default status
- no automatic RAG ingestion without review

## 9. Automated Evaluation and Review Queue Tests

When the evaluation pipeline is implemented, tests should validate:

- discovered item evaluation
- evaluation result persistence
- review item creation
- review status changes
- approved items become ingestion candidates
- rejected items are not ingested
- missing data remains visible

Current backend tests cover discovered-item evaluation, structured risk summaries, review item creation, review status updates, and the `approved_for_rag` prepared-only boundary.

## 10. Strategy Simulator Tests

When the simulator is implemented, tests should validate:

- net spread calculation
- borrow APY shock
- liquidity/slippage shock
- collateral drawdown
- LTV and liquidation buffer approximation
- early exit before maturity
- missing input handling
- non-advisory output language

Current simulator tests cover deterministic scenario generation, missing-data visibility, endpoint behavior, and non-advisory disclaimer language.

## 11. Watchlist and Alert Tests

When watchlists are implemented, tests should validate:

- watchlist item creation
- rule evaluation
- alert event creation
- alert status updates
- no external notification required in the first version
- no trading recommendation text

Current watchlist tests cover item creation, manual rule evaluation, alert event creation, alert status updates, and non-advisory alert text.

## 12. Options Analysis Tests

When options analysis is implemented, tests should validate:

- call payoff scenarios
- put payoff scenarios
- breakeven calculation
- maximum loss framing
- implied volatility field handling
- bid/ask spread warning
- expiration handling
- non-advisory output language

Current options tests cover call and put payoff scenarios, breakeven, maximum loss framing, implied volatility/missing data handling, bid/ask spread, endpoint behavior, and non-advisory output language.

## 13. ML and Fine-Tuning Tests

## 13. Advanced RAG Tests

Current advanced RAG tests validate:

- existing local retrieval still works
- hybrid retrieval supports metadata filters
- optional semantic retrieval can be enabled
- citation validation reports missing metadata
- retrieval evaluation writes metrics

Run retrieval evaluation with:

```bash
cd backend
python scripts/build_retrieval_eval_dataset.py
python scripts/evaluate_retrieval.py --retriever hybrid_semantic
```

## 14. ML and Fine-Tuning Tests

Before any model is used in the app, tests should validate:

- dataset export shape
- label schema
- baseline classifier interface
- deterministic risk scoring remains available
- model output cannot silently override deterministic scoring

## 15. Smoke Tests

Suggested smoke command:

```bash
cd backend
python scripts/run_smoke_checks.py
```

Smoke checks should verify:

- `/health`
- `/api/protocols`
- `/api/analyze`
- report creation
- report retrieval
- Markdown export

Post-MVP smoke checks may later add:

- monitoring run
- discovered item retrieval
- evaluation run
- simulation run
- watchlist rule evaluation

## 15. Final Portfolio Test Pass

Final phases 11, 12, and 13 should run only after product-expansion phases are stable.

Final portfolio validation should include:

- demo data loads
- example reports render
- screenshots are current
- public frontend works
- public backend health works
- README links are correct
- demo script matches the deployed product

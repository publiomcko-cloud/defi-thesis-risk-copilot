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

## 2. Backend Tests

Run:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

Recommended test areas:

- analysis endpoint
- report endpoint
- document ingestion
- retriever behavior
- risk scoring
- data adapter normalization
- missing data handling
- disclaimer presence

## 3. Frontend Tests

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

## 4. RAG Tests

RAG evaluation questions:

- What is a Pendle PT?
- What is fixed yield?
- What is LLTV?
- What is Health Factor?
- What is liquidation risk?
- What is oracle risk?
- What is maturity risk?

The retriever should return relevant protocol chunks for each question.

## 5. Risk Scoring Tests

Risk scoring should be deterministic.

Example tests:

- single-protocol no leverage strategy
- multi-protocol strategy
- leveraged strategy
- unknown liquidity
- volatile collateral
- variable borrow rate
- missing oracle data

## 6. Report Tests

Every generated report should include:

- executive summary
- protocols involved
- strategy mechanics
- assumptions
- risk rating
- missing data
- sources
- disclaimer

## 7. Smoke Tests

Suggested smoke command:

```bash
python scripts/run_smoke_checks.py
```

Smoke checks should verify:

- `/health`
- `/api/protocols`
- `/api/analyze`
- report creation
- report retrieval

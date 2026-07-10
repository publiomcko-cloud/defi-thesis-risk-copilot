# MVP Scope — DeFi Thesis & Risk Copilot

## 1. MVP Goal

The MVP goal is to build a working AI application where a user can submit a DeFi strategy and receive a structured research and risk report.

The MVP should be strong enough to demonstrate:

- generative AI
- RAG
- agentic workflows
- DeFi data modeling
- market data adapters
- risk scoring
- report generation
- full-stack product thinking
- Dockerized local execution
- GitHub-ready documentation

## 2. Included in MVP

The MVP includes:

1. Strategy input form.
2. Support for Pendle, Morpho, and Aave as initial protocol scope.
3. RAG over curated protocol documentation.
4. Basic market data adapters.
5. Manual fallback for missing data.
6. Rule-based risk scoring.
7. Structured report generation.
8. Source references.
9. Markdown export.
10. Dockerized local development.

## 3. Not Included in MVP

The MVP does not include:

1. Wallet connection.
2. Transaction signing.
3. Trade execution.
4. Smart contract interaction from the UI.
5. Paid API dependencies.
6. Real-time alerts.
7. Portfolio tracking.
8. Options analysis.
9. Backtesting engine.
10. Production authentication.
11. Billing or subscription system.

## 4. Main MVP Use Case

The main use case is a strategy report for a Pendle + Morpho or Aave-style lending strategy.

Example:

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

The system should produce:

1. Executive summary.
2. Protocols involved.
3. Strategy mechanics.
4. Yield source.
5. Market data summary.
6. Assumptions.
7. Risk analysis.
8. Stress scenarios.
9. Exit plan.
10. Monitoring checklist.
11. Risk rating.
12. Sources.
13. Disclaimer.

## 5. MVP Success Criteria

The MVP is complete when:

1. A user can submit a strategy.
2. The system retrieves relevant protocol context.
3. The system fetches or accepts basic market data.
4. The system generates a structured report.
5. The report includes risk rating, assumptions, missing data, and sources.
6. The app runs locally with Docker Compose.
7. The repository has portfolio-grade documentation.
8. A short demo video can show the full workflow.

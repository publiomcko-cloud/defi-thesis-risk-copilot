# Strategy Risk Report

Report ID: `demo_report_discovery_to_rag`

Risk rating: **Moderate**

## Executive Summary

Demo discovered protocol documentation is routed through review before becoming trusted RAG context.

## Strategy Description

Evaluate a newly discovered synthetic lending protocol source before knowledge-base ingestion.

## Protocols Involved

aurora-lend-demo

## Strategy Mechanics

Synthetic inputs demonstrate the workflow without using live positions or paid APIs.

## Yield Source

Demo yield assumptions come from fixed synthetic values, not investment recommendations.

## Market Data Summary

Market values are stable demo assumptions designed for reproducible review.

## Key Assumptions

Demo data is synthetic and deterministic.; No wallet, custody, transaction signing, or trade execution is involved.; Optional LLM synthesis is not required to reproduce this demo.

## Risk Analysis

Score 5/10. Human approval is required because documentation alone does not establish production safety.

## Stress Scenarios

Stress examples include borrow-rate shocks, liquidity drawdowns, and adverse exit conditions.

## Simulation Summary

Use the simulator page to reproduce deterministic scenario outputs with the provided assumptions.

## Exit Plan

Demo exit planning emphasizes monitoring and uncertainty, not instructions to trade.

## Monitoring Checklist

Track borrow APY, liquidity depth, oracle status, maturity dates, and missing data.

## Risk Rating

Moderate. Deterministic scoring remains the source of truth.

## Missing Data and Uncertainty

audit recency, oracle implementation, liquidity depth

## Sources

Local demo seed data and curated project documentation.

## Disclaimer

This demo is for educational research only. It is not financial, investment, legal, or tax advice. It does not recommend buying, selling, borrowing, lending, or entering any position.


## Limitations

- Demo values are synthetic and may not reflect live markets.
- Reports are educational research artifacts, not recommendations.
- No wallet connection, custody, transaction signing, or trade execution exists.


## How to Reproduce Inside the App

1. Start the local stack with `docker compose up -d --build`.
2. Run `POST /api/demo/seed` or use the Demo page seed action.
3. Open `/reports/demo_report_discovery_to_rag` or use `/demo` scenario links.


## Non-Advisory Disclaimer

This demo is for educational research only. It is not financial, investment, legal, or tax advice. It does not recommend buying, selling, borrowing, lending, or entering any position.

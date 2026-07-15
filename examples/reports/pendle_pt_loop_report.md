# Strategy Risk Report

Report ID: `demo_report_pendle_pt_loop`

Risk rating: **Moderate**

## Executive Summary

Synthetic Pendle PT loop shows attractive fixed-yield mechanics but meaningful borrow, liquidity, oracle, and liquidation sensitivity.

## Strategy Description

Analyze a synthetic Pendle PT position financed with Morpho/Aave-style borrowing.

## Protocols Involved

pendle, morpho, aave

## Strategy Mechanics

Synthetic inputs demonstrate the workflow without using live positions or paid APIs.

## Yield Source

Demo yield assumptions come from fixed synthetic values, not investment recommendations.

## Market Data Summary

Market values are stable demo assumptions designed for reproducible review.

## Key Assumptions

Demo data is synthetic and deterministic.; No wallet, custody, transaction signing, or trade execution is involved.; Optional LLM synthesis is not required to reproduce this demo.

## Risk Analysis

Score 5/10. Main drivers are leverage, borrow-rate sensitivity, PT liquidity, oracle assumptions, and maturity mismatch.

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

live borrow APY, oracle configuration, exit liquidity during stress

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
3. Open `/reports/demo_report_pendle_pt_loop` or use `/demo` scenario links.


## Non-Advisory Disclaimer

This demo is for educational research only. It is not financial, investment, legal, or tax advice. It does not recommend buying, selling, borrowing, lending, or entering any position.

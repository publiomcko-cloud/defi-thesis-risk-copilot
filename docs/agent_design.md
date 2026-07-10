# Agent Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The agent layer coordinates research, retrieval, market data lookup, risk scoring, and report generation.

The MVP should start with a controlled workflow rather than a fully autonomous agent.

## 2. MVP Agent Workflow

```text
User request
    |
    v
Parse strategy
    |
    v
Detect protocols
    |
    v
Retrieve documentation
    |
    v
Fetch market data
    |
    v
Normalize available inputs
    |
    v
Run risk scoring
    |
    v
Generate report
```

## 3. Agent Tools

Planned tools:

```text
retrieve_protocol_docs()
fetch_market_data()
normalize_strategy_inputs()
calculate_basic_spread()
calculate_ltv_metrics()
score_strategy_risk()
generate_stress_scenarios()
write_research_report()
```

## 4. Agent Responsibilities

### ProtocolResearchAgent

- identify involved protocols
- retrieve relevant documentation
- summarize protocol mechanisms
- identify protocol-specific risks

### MarketDataAgent

- call public data APIs
- normalize token and market data
- mark missing fields
- provide cached or manual fallback data

### RiskScoringAgent

- apply rule-based risk framework
- classify strategy risk
- explain score components
- identify missing data that affects confidence

### ReportWriterAgent

- generate final structured report
- include assumptions
- include missing data
- include sources
- include disclaimer

## 5. MVP Control Rules

The agent must not:

- execute trades
- connect wallets
- recommend direct buy or sell actions
- hide missing data
- present uncertain data as fact
- ignore source limitations

## 6. Future Multi-Agent Design

Future agents:

```text
ProtocolResearchAgent
MarketDataAgent
RiskScoringAgent
StrategySimulationAgent
OptionsAnalysisAgent
SourceValidationAgent
WatchlistAgent
ReportWriterAgent
```

## 7. Future Automation

Future versions may monitor sources for:

- new Pendle markets
- new Morpho vaults
- new Aave reserves
- new governance proposals
- material TVL changes
- borrow APY changes
- liquidity changes
- oracle changes

New items can be automatically evaluated and then queued for human review before being added to the RAG knowledge base.

# Agent Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The agent layer coordinates research, retrieval, market data lookup, risk scoring, report generation, and post-MVP product workflows.

The MVP starts with a controlled workflow rather than a fully autonomous agent. Post-MVP development should keep that same design principle: bounded workflows, explicit tool calls, visible missing data, and human review before trusting newly discovered sources.

## 2. Current MVP Agent Workflow

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
    |
    v
Persist report and Markdown export
```

## 3. Current Agent Tools

Implemented or planned around the Phase 10 baseline:

```text
retrieve_protocol_docs()
fetch_market_data()
normalize_strategy_inputs()
score_strategy_risk()
generate_stress_scenarios()
generate_monitoring_checklist()
write_research_report()
render_markdown_report()
```

## 4. Current Agent Responsibilities

### ProtocolResearchAgent

- identify involved protocols
- retrieve relevant documentation
- summarize protocol mechanisms
- identify protocol-specific risks

### MarketDataAgent

- call public data APIs where available
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
- optionally call an LLM synthesis layer in the next phase

## 5. Control Rules

The agent must not:

- execute trades
- connect wallets
- recommend direct buy or sell actions
- hide missing data
- present uncertain data as fact
- ignore source limitations
- automatically trust newly discovered sources
- allow LLM output to override deterministic risk scoring silently

## 6. Active Post-MVP Agent Expansion

The active post-MVP phases are now treated as product-development phases, not distant roadmap notes.

### 6.1 LLM Synthesis Layer

Purpose:

- improve natural-language report quality
- summarize retrieved RAG context
- explain risk drivers more clearly
- preserve deterministic score and missing data

Rules:

- LLM use must be optional.
- `LLM_PROVIDER=disabled` must keep the app working.
- LLM failure must fall back to deterministic report generation.
- The LLM must not calculate the risk score.
- The LLM must not produce direct financial advice.

### 6.2 SourceMonitoringAgent

Purpose:

- check public sources for new markets, vaults, reserves, proposals, or documentation changes
- normalize discovered items
- detect duplicates
- record source metadata and uncertainty

Initial monitored sources:

- Pendle markets
- Morpho markets or vaults
- Aave reserves
- DefiLlama protocol/yield data
- governance forums
- protocol documentation pages
- audit and risk report links

### 6.3 EvaluationAgent

Purpose:

- evaluate discovered items using the existing controlled workflow
- generate a short risk summary
- create review queue items
- mark missing data and uncertainty

The EvaluationAgent must not approve its own findings. Human review remains required.

### 6.4 ReviewQueueAgent

Purpose:

- track discovered items that need review
- allow statuses such as `needs_review`, `approved_for_rag`, `rejected`, `needs_more_data`, and `archived`
- prepare approved items for RAG ingestion

### 6.5 StrategySimulationAgent

Purpose:

- run deterministic stress scenarios
- estimate net spread under assumptions
- estimate borrow APY shock impact
- estimate liquidity/slippage shock impact
- estimate LTV and liquidation buffer approximations

The simulator must present assumptions and must not frame outputs as guarantees.

### 6.6 WatchlistAgent

Purpose:

- store watched strategies, protocols, or markets
- evaluate alert rules manually at first
- generate in-app alert events

Initial alert types:

- borrow APY above threshold
- net spread below threshold
- liquidity below threshold
- maturity date approaching
- risk score changed
- new discovered item needs review

### 6.7 OptionsAnalysisAgent

Purpose:

- analyze manually entered crypto option structures
- calculate breakeven and payoff scenarios
- explain premium, strike, expiration, implied volatility, and spread risk
- remain educational and non-advisory

### 6.8 AdvancedRAGAgent

Purpose:

- add semantic retrieval
- run retrieval evaluation
- validate citations
- rerank retrieved chunks
- score source freshness and quality

### 6.9 MLAssistAgent

Purpose:

- export labeled datasets
- train or evaluate baseline classifiers
- assist deterministic scoring with model outputs

The model must not silently replace the deterministic risk framework.

## 7. Active Agent Order

Recommended order:

```text
LLM Synthesis Layer
    -> SourceMonitoringAgent
    -> EvaluationAgent + ReviewQueueAgent
    -> StrategySimulationAgent
    -> WatchlistAgent
    -> OptionsAnalysisAgent
    -> AdvancedRAGAgent
    -> MLAssistAgent
```

## 8. Final Portfolio Agents

After product expansion, the final portfolio phase may add demo-only helpers:

- example report generator
- screenshot preparation helper
- demo script helper
- public deployment verification helper

These belong after active product development, not before it.

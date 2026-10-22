# Agent Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The agent layer coordinates research, retrieval, market data lookup, risk scoring, report generation, and post-MVP product workflows.

The MVP starts with a controlled workflow rather than a fully autonomous agent. Post-MVP development should keep that same design principle: bounded workflows, explicit tool calls, visible missing data, and human review before trusting newly discovered sources.

## Portfolio target: bounded deep research, not unrestricted autonomy

The owner-facing **Research Copilot** orchestrates tools that already exist or are being integrated: public/approved protocol retrieval, public/manual market adapters, deterministic risk/stress/options, thesis history, governed model synthesis and report persistence. A logical agent/tool role is **not** a dedicated worker process. Phase 17 workers provide optional durable background execution, leasing/cancellation/recovery; Phase 20C schedules reuse that substrate.

The next accepted flow must be **multi-step but bounded**:

```text
Owner thesis -> authorized bounded research run
  -> retrieve curated and approved protocol sources + provenance/freshness
  -> fetch permitted market data -> deterministic scenario/risk results
  -> model-assisted explanation with validated cited claims
  -> at most a bounded follow-up on explicit evidence gaps
  -> structured report/version/compare/export
  -> optional owner-approved scheduled watch -> deterministic delta evaluation
  -> in-app change/failure notification; optional budgeted research follow-up
```

Non-negotiable: tool whitelist, typed contracts, run/token/time/cost bounds, opt-in model route, secret-safe source prompts, source approval and tenant scope. Model output does not edit deterministic scores, underlying market facts or source identity. If source/model/provider data is unavailable, preserve missing/stale markers and deterministic fallback; do not hallucinate a research completion.

The implementation must label **implemented** vs **enabled** vs **validated**. The checked-in Phase 21D research intelligence is primarily deterministic; optional LLM synthesis is off by default. No autonomous end-to-end deeper-research agent or running private scheduled AI research is claimed yet.

A scheduled watch is a separate owner-controlled workflow (existing Phase 20C/20D), minimum hourly, maximum five active per user, DST/timezone-aware, one-winner/idempotent, notifications in-app. It checks deterministic deltas first and calls an approved LLM only if explicitly enabled and useful. Public scheduled dispatch stays off. Temporal/lease/recovery safety of the actual worker candidate must pass before activating personal dispatch; Phase 22 stays HOLD.

The [completion contract](portfolio_completion_contract.md) defines gates; [finalization plan](portfolio_finalization_plan.md) defines slices. The original MVP workflow below remains historical implemented behavior, not proof of this target.

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
- The deterministic report is always generated first.
- The LLM may only rewrite approved explanatory sections.
- The report writer restores immutable fields after synthesis, including risk rating, protocols, missing data, sources, market values, and disclaimer.

### 6.2 SourceMonitoringAgent

Purpose:

- check public sources for new markets, vaults, reserves, proposals, or documentation changes
- normalize discovered items
- detect duplicates
- record source metadata and uncertainty
- record collector failures without crashing the app
- keep every new item in `needs_review`

Initial monitored sources:

- Pendle markets
- Morpho markets or vaults
- Aave reserves
- DefiLlama protocol/yield data
- governance forums
- protocol documentation pages
- audit and risk report links

Current implementation:

- exposes manual monitoring through `POST /api/monitoring/run`
- lists candidates through `GET /api/monitoring/discovered-items`
- stores `source_watches` and `discovered_items`
- updates duplicate candidates using a stable discovery key
- does not ingest discovered items into RAG

### 6.3 EvaluationAgent

Purpose:

- evaluate discovered items using the existing controlled workflow
- generate a short risk summary
- create review queue items
- mark missing data and uncertainty

The EvaluationAgent must not approve its own findings. Human review remains required.

Current implementation:

- evaluates a discovered item through the controlled analysis workflow
- stores an `evaluation_result`
- creates or updates a `review_item`
- records risk score, risk rating, confidence, missing data, sources, and a short risk summary
- keeps the review item in `needs_review` unless a human changes it

### 6.4 ReviewQueueAgent

Purpose:

- track discovered items that need review
- allow statuses such as `needs_review`, `approved_for_rag`, `rejected`, `needs_more_data`, and `archived`
- prepare approved items for RAG ingestion

Current implementation:

- exposes review items through `GET /api/evaluation/review-items`
- updates review status through `PATCH /api/evaluation/review-items/{review_item_id}`
- marks `approved_for_rag` items as prepared only
- does not ingest reviewed items into RAG

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

Current implementation:

- exposes deterministic options analysis through `POST /api/options/analyze`
- supports call and put payoff scenarios
- returns breakeven, max loss, bid/ask spread, volatility summary, risks, and missing data
- does not provide buy/sell instructions

### 6.8 AdvancedRAGAgent

Purpose:

- add semantic retrieval
- run retrieval evaluation
- validate citations
- rerank retrieved chunks
- score source freshness and quality

Current implementation:

- keeps the original local retriever available
- adds `HybridRetriever` with keyword, vector, metadata, quality, freshness, and reranking signals
- supports optional deterministic `local_semantic` embeddings
- validates required citation metadata
- records retrieval evaluation metrics through backend scripts

### 6.9 MLAssistAgent

Purpose:

- export labeled datasets
- train or evaluate baseline classifiers
- assist deterministic scoring with model outputs

The model must not silently replace the deterministic risk framework.

Current implementation:

- exports labeled candidate training examples from persisted reports
- defines labels for risk rating, risk drivers, protocol category, missing data severity, and strategy type
- provides a baseline advisory classifier interface
- preserves deterministic risk rating as the authoritative output

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

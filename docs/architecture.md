# Architecture — DeFi Thesis & Risk Copilot

## 1. Architectural Overview

DeFi Thesis & Risk Copilot is a full-stack AI research application for DeFi strategy analysis.

The architecture is designed around five core principles:

- clear separation between frontend, backend, data adapters, RAG, agents, and risk logic
- source-grounded analysis using protocol documentation
- deterministic calculations where possible
- LLM generation only after retrieval, normalization, and risk scoring
- portfolio-grade maintainability and documentation

The MVP focuses on Pendle, Morpho, and Aave strategy analysis.

The Phase 10 baseline now supports a working controlled analysis workflow. The next product work should extend this baseline with optional LLM synthesis, source monitoring, automated evaluation, strategy simulation, watchlists, options analysis, advanced RAG, and ML/HPC support before final portfolio deployment and polish.

## 2. Architecture Goals

The architecture must support:

- strategy input from a user-facing dashboard
- protocol detection from natural language
- retrieval of relevant protocol documentation
- basic market data lookup
- manual fallback for missing market data
- risk scoring based on visible assumptions
- structured report generation
- source citations
- Dockerized local execution
- optional LLM-backed report synthesis
- source monitoring and discovery
- automated evaluation with human review
- watchlists and alerts
- strategy simulation
- options and volatility analysis
- advanced RAG evaluation and reranking
- future fine-tuning and HPC batch processing

## 3. High-Level System Flow

```text
User Browser
    |
    v
Next.js Strategy Analysis UI
    |
    v
FastAPI Backend
    |
    +------------------------------+
    |                              |
    v                              v
Agent Orchestrator              PostgreSQL
    |
    +--> RAG Retriever
    |
    +--> Market Data Adapters
    |
    +--> Calculation Tools
    |
    +--> Risk Scoring Service
    |
    +--> Report Writer
    |
    v
Vector Database / pgvector
    |
    v
Optional LLM Provider
```

## 4. Main Applications

## 4.1 Strategy input interface

The strategy input interface is the user-facing entry point.

Responsibilities:

- collect strategy description
- accept optional protocol selection
- accept optional market URL
- accept optional manual parameters
- display missing data warnings
- submit the strategy for analysis

## 4.2 Report interface

The report interface displays the generated research output.

Responsibilities:

- show executive summary
- show risk rating
- show strategy mechanics
- show data assumptions
- show risk breakdown
- show stress scenarios
- show monitoring checklist
- show retrieved sources
- allow markdown export

## 4.3 Admin or developer tools

The first version may include a minimal developer-only interface.

Responsibilities:

- inspect ingested documents
- trigger document ingestion
- inspect retrieved chunks
- inspect market data adapter responses
- debug risk score inputs
- test prompt templates
- inspect discovered source items
- inspect evaluation results
- review queued items before RAG ingestion

## 5. Main Backend Domains

Backend structure:

```text
backend/app/
├── api/
│   ├── routes_analysis.py
│   ├── routes_reports.py
│   ├── routes_documents.py
│   ├── routes_market_data.py
│   ├── routes_protocols.py
│   └── routes_health.py
├── agents/
│   ├── orchestrator.py
│   ├── protocol_research_agent.py
│   ├── strategy_parser.py
│   ├── market_data_agent.py
│   ├── risk_scoring_agent.py
│   └── report_writer_agent.py
├── rag/
│   ├── ingest.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── retriever.py
│   ├── vector_store.py
│   └── citations.py
├── data_sources/
│   ├── base.py
│   ├── coingecko.py
│   ├── defillama.py
│   ├── morpho.py
│   ├── aave.py
│   ├── pendle.py
│   └── manual.py
├── risk/
│   ├── framework.py
│   ├── scoring.py
│   ├── scenarios.py
│   └── checklist.py
├── reports/
│   ├── templates.py
│   ├── renderer.py
│   └── markdown_export.py
├── llm/
│   ├── base.py
│   ├── providers.py
│   ├── prompts.py
│   └── synthesis.py
├── core/
│   ├── config.py
│   ├── logging.py
│   └── errors.py
├── db/
│   ├── session.py
│   └── base.py
└── tests/
```

Further post-MVP backend domains will add:

```text
backend/app/
├── monitoring/
│   ├── sources.py
│   ├── collectors.py
│   ├── normalizer.py
│   └── discovery_service.py
├── evaluation/
│   ├── evaluator.py
│   └── review_queue.py
├── simulation/
│   ├── spread.py
│   ├── ltv.py
│   ├── scenarios.py
│   └── simulator.py
├── watchlist/
│   ├── rules.py
│   └── service.py
├── options/
│   ├── payoff.py
│   ├── volatility.py
│   └── analysis.py
└── ml/
    ├── dataset_export.py
    └── risk_classifier.py
```

## 6. Frontend Structure

Frontend route structure:

```text
frontend/src/
├── app/
│   ├── page.tsx
│   ├── analyze/page.tsx
│   ├── reports/[reportId]/page.tsx
│   ├── protocols/page.tsx
│   └── about/page.tsx
├── components/
│   ├── StrategyInputForm.tsx
│   ├── RiskRatingCard.tsx
│   ├── ReportSection.tsx
│   ├── SourcesPanel.tsx
│   ├── DataSummaryTable.tsx
│   ├── MarkdownExportButton.tsx
│   └── MonitoringChecklist.tsx
├── lib/
│   ├── api.ts
│   ├── types.ts
│   └── formatting.ts
└── styles/
```

Post-MVP frontend routes may add:

```text
frontend/src/app/
├── review/page.tsx
├── simulate/page.tsx
├── watchlist/page.tsx
└── options/page.tsx
```

## 7. RAG Architecture

The RAG system should ingest selected protocol documentation and internal risk notes.

```text
Documentation Source
    |
    v
Document Loader
    |
    v
Text Cleaning
    |
    v
Chunking
    |
    v
Metadata Extraction
    |
    v
Embedding Model
    |
    v
Vector Database
    |
    v
Retriever
    |
    v
Context Builder
    |
    v
Optional LLM Synthesis
```

The MVP should prioritize quality over quantity. A small curated knowledge base is better than a large noisy one.

Post-MVP RAG should add semantic embeddings, hybrid retrieval, source freshness, citation validation, and a retrieval evaluation dataset.

Source monitoring now discovers review candidates separately from RAG ingestion. Discovered items must pass later evaluation and human review before they can become ingestion candidates.

## 8. Agent Architecture

The MVP uses one controlled workflow instead of fully autonomous agents.

```text
Analysis Request
    |
    v
Parse Strategy
    |
    v
Retrieve Protocol Context
    |
    v
Fetch Market Data
    |
    v
Normalize Inputs
    |
    v
Run Risk Score
    |
    v
Generate Report
    |
    v
Optional LLM Synthesis
    |
    v
Manual Source Monitoring
    |
    v
Discovered Items Requiring Review
    |
    v
Automated Evaluation Summary
    |
    v
Human Review Queue
    |
    v
Deterministic Strategy Simulator
```

Post-MVP versions may split this workflow into specialized agents, but orchestration should remain bounded, observable, and reviewable.

## 9. Data Architecture

The data layer should support:

- live API calls
- cached responses
- manual fallback data
- normalized protocol entities
- report persistence
- source metadata
- vector search metadata
- discovered source items
- evaluation results
- review status
- watchlist items
- alert events
- simulation inputs and outputs

The MVP should avoid depending on paid APIs. Premium providers may be added later as optional adapters.

## 10. Safety Architecture

Safety requirements:

- no wallet connection
- no trade execution
- no private key handling
- no direct buy/sell recommendations
- clear disclaimer in every report
- explicit uncertainty when data is missing
- source references for protocol-specific claims
- human review before automatically trusting discovered sources
- deterministic fallback when LLM output fails or is disabled
- no model output may override deterministic risk scoring silently

## 11. Active Product Expansion Architecture

After Post-MVP Phase 5, the remaining active product architecture expands in this order:

```text
Options and Volatility Analysis
    -> Advanced RAG
    -> Fine-tuning Groundwork
    -> HPC Readiness
```

The original MVP Phase 11, Phase 12, and Phase 13 remain final portfolio actions after these product-expansion phases.

## 12. Final Portfolio Architecture

The final portfolio deployment should happen only after the active product-expansion phases are stable.

Final sequence:

```text
Demo data and example reports
    -> public frontend/backend deployment
    -> portfolio polish
    -> screenshots and demo video
    -> README and case study finalization
```

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
- future watchlists, alerts, simulators, options analysis, and fine-tuning

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
LLM Provider
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

## 5. Main Backend Domains

Planned backend structure:

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
│   ├── strategy_analysis_agent.py
│   ├── market_data_agent.py
│   ├── risk_scoring_agent.py
│   └── report_writer_agent.py
├── rag/
│   ├── ingest.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── retriever.py
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
│   └── scenarios.py
├── reports/
│   ├── templates.py
│   ├── renderer.py
│   └── markdown_export.py
├── core/
│   ├── config.py
│   ├── logging.py
│   └── errors.py
├── db/
│   ├── session.py
│   └── models.py
└── tests/
```

## 6. Frontend Structure

Planned frontend route structure:

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
│   └── MonitoringChecklist.tsx
├── lib/
│   ├── api.ts
│   ├── types.ts
│   └── formatting.ts
└── styles/
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
LLM Context Builder
```

The MVP should prioritize quality over quantity. A small curated knowledge base is better than a large noisy one.

## 8. Agent Architecture

The MVP can start with one orchestrated workflow instead of fully autonomous agents.

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
```

Future versions may split this workflow into specialized agents.

## 9. Data Architecture

The data layer should support:

- live API calls
- cached responses
- manual fallback data
- normalized protocol entities
- report persistence
- source metadata
- vector search metadata

The MVP should avoid depending on paid APIs.

## 10. Safety Architecture

Safety requirements:

- no wallet connection in MVP
- no trade execution
- no private key handling
- no direct buy/sell recommendations
- clear disclaimer in every report
- explicit uncertainty when data is missing
- source references for protocol-specific claims

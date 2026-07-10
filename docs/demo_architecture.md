# Demo Architecture — DeFi Thesis & Risk Copilot

## 1. Purpose

This document defines the demo architecture for DeFi Thesis & Risk Copilot.

The goal of the demo is to show a safe, portfolio-ready AI application that analyzes DeFi strategies using RAG, LLM agents, market data adapters, rule-based risk scoring, and structured report generation.

The demo is intentionally designed as a **research and risk analysis system**, not as a trading bot.

The demo must not:

- connect wallets
- request private keys
- sign transactions
- execute trades
- custody funds
- provide personalized financial advice

The demo should clearly show how the system transforms a user strategy prompt into a structured, source-backed DeFi risk report.

---

## 2. Demo Architecture Goals

The demo architecture must support:

- a clean browser-based user interface
- natural language strategy input
- protocol detection
- RAG retrieval from protocol documentation
- public or cached market data lookup
- manual fallback for missing data
- deterministic risk scoring
- LLM-based report generation
- source and assumption visibility
- markdown export
- local Docker-based execution
- future deployment to Vercel, Render, and Supabase

---

## 3. High-Level Demo Architecture

```text
User Browser
    |
    v
Next.js Frontend
    |
    v
FastAPI Backend
    |
    v
Agent Orchestrator
    |
    +--> Strategy Parser
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
PostgreSQL + Vector Database
    |
    v
LLM Provider
```

The frontend collects the user request.  
The backend coordinates retrieval, data lookup, scoring, and report generation.  
The vector database stores embedded protocol documentation.  
The LLM provider generates the final explanation and report using retrieved context and structured intermediate data.

---

## 4. Demo User Flow

```text
Home page
    |
    v
Strategy input page
    |
    v
Submit strategy description
    |
    v
Backend analysis request
    |
    v
Protocol detection
    |
    v
RAG retrieval
    |
    v
Market data lookup
    |
    v
Risk scoring
    |
    v
Report generation
    |
    v
Report page
    |
    v
Markdown export
```

Example demo prompt:

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

---

## 5. Local Demo Architecture

The local demo should run with Docker Compose.

```text
Developer Machine
    |
    +--> Next.js Frontend
    |
    +--> FastAPI Backend
    |
    +--> PostgreSQL
    |
    +--> Vector Database
    |
    +--> Optional Ollama LLM
```

Suggested local services:

```text
frontend
backend
postgres
vector-db
ollama, optional
```

The local demo can use either:

1. **Ollama local model**
   - useful for offline or low-cost testing
   - slower depending on hardware
   - avoids hosted LLM costs

2. **OpenAI-compatible API provider**
   - useful for stronger hosted demo quality
   - requires API key
   - should be optional

The system should support this through environment configuration:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

or:

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
```

---

## 6. Public Portfolio Demo Architecture

Recommended public deployment:

```text
Browser
    |
    v
Vercel
    |
    v
Render
    |
    v
Supabase PostgreSQL
    |
    v
Vector Storage
    |
    v
Hosted LLM Provider
```

Suggested mapping:

```text
Frontend:
Vercel

Backend:
Render

Relational database:
Supabase PostgreSQL

Vector storage:
pgvector on Supabase, Qdrant Cloud, Chroma, or another vector database

LLM:
OpenAI-compatible hosted provider

Market data:
Public APIs and cached demo data
```

For the first public demo, the safest option is:

```text
Vercel frontend
Render backend
Supabase PostgreSQL with pgvector
Hosted LLM provider
Cached or limited public data APIs
```

---

## 7. Demo Data Flow

```text
User Prompt
    |
    v
Strategy Parser
    |
    +--> detects protocols
    +--> extracts assets
    +--> extracts requested analysis dimensions
    +--> identifies missing fields
    |
    v
RAG Retriever
    |
    +--> searches protocol documentation
    +--> returns relevant chunks
    +--> attaches source metadata
    |
    v
Market Data Layer
    |
    +--> calls public APIs
    +--> reads cached demo data
    +--> accepts manual fallback values
    |
    v
Risk Scoring Service
    |
    +--> evaluates risk categories
    +--> assigns risk rating
    +--> explains score drivers
    |
    v
Report Writer
    |
    +--> generates structured report
    +--> includes assumptions
    +--> includes missing data
    +--> includes sources
    +--> includes disclaimer
```

---

## 8. Demo Components

## 8.1 Frontend

Responsibilities:

- display landing page
- explain the product
- show safety disclaimer
- collect strategy prompt
- display loading states
- render generated report
- show risk rating card
- show source panel
- export report as Markdown

Suggested pages:

```text
/
  Home page

/analyze
  Strategy input page

/reports/[reportId]
  Report detail page

/protocols
  Supported protocols page

/about
  Project explanation page
```

---

## 8.2 Backend

Responsibilities:

- expose API endpoints
- validate request payloads
- coordinate the analysis workflow
- call RAG retriever
- call data adapters
- apply risk scoring
- store reports
- return structured report payload

Suggested endpoints:

```text
GET  /health
POST /api/analyze
GET  /api/reports/{report_id}
GET  /api/protocols
POST /api/documents/ingest
POST /api/risk-score
POST /api/market-data/fetch
POST /api/reports/{report_id}/export
```

---

## 8.3 RAG Layer

Responsibilities:

- ingest protocol documentation
- clean and chunk documents
- generate embeddings
- store vectors
- retrieve relevant chunks
- return source metadata

Initial sources:

```text
Pendle documentation
Morpho documentation
Aave documentation
Chainlink documentation
Internal DeFi risk notes
```

The demo should show source-backed analysis, even if the knowledge base is small.

---

## 8.4 Market Data Layer

Responsibilities:

- fetch public DeFi and token data
- normalize API responses
- cache results
- handle API failures
- mark missing fields
- support manual fallback values

Initial data adapters:

```text
DefiLlama
CoinGecko
Morpho
Aave
Manual fallback
```

Future adapters:

```text
Pendle API
The Graph
Dune
Chainlink feeds
Token Terminal
Messari
Nansen
Arkham
```

---

## 8.5 Agent Orchestrator

The MVP should use a controlled agentic workflow rather than a fully autonomous open-ended agent.

Responsibilities:

- parse the strategy request
- select relevant tools
- retrieve documentation
- request market data
- normalize available data
- run calculations
- run risk scoring
- produce final report

The orchestrator should be deterministic where possible and use the LLM mainly for explanation, synthesis, and report writing.

---

## 8.6 Risk Scoring Service

Responsibilities:

- classify risk into one of four levels
- explain why the rating was assigned
- identify the biggest risk drivers
- identify missing data that reduces confidence

MVP ratings:

```text
Conservative
Moderate
Aggressive
Very Risky
```

Initial scoring can be rule-based.

Future versions may replace or augment this with a fine-tuned classifier.

---

## 8.7 Report Writer

Responsibilities:

- generate the final report
- follow a consistent structure
- include assumptions
- include missing data
- include risk rating
- include sources
- include disclaimer
- support markdown export

Report sections:

```text
1. Executive Summary
2. Strategy Description
3. Protocols Involved
4. Strategy Mechanics
5. Yield Source
6. Market Data Summary
7. Key Assumptions
8. Risk Analysis
9. Stress Scenarios
10. Exit Plan
11. Monitoring Checklist
12. Risk Rating
13. Missing Data and Uncertainty
14. Sources
15. Disclaimer
```

---

## 9. Demo Safety Boundaries

The demo must keep strict boundaries.

Allowed:

- analyze public information
- retrieve documentation
- summarize protocol mechanics
- estimate risk categories
- generate educational reports
- display missing data
- generate monitoring checklists

Not allowed in demo:

- wallet connection
- transaction execution
- trading automation
- private key handling
- seed phrase input
- direct personalized investment advice
- guaranteed return claims
- hidden assumptions

Every report should include:

```text
This tool is for educational and research purposes only. It does not provide financial, investment, legal, or tax advice. DeFi strategies involve significant risks, including smart contract risk, liquidation risk, oracle risk, liquidity risk, and total loss of funds. Always verify data independently before making decisions.
```

---

## 10. Demo Scenario

The first demo should use one main scenario:

```text
Pendle PT + Morpho borrow strategy
```

The scenario should demonstrate:

- protocol documentation retrieval
- fixed-yield explanation
- borrow rate dependency
- liquidity and exit risk
- oracle risk
- liquidation risk
- maturity risk
- risk rating
- monitoring checklist

The demo should avoid real capital allocation and use either a hypothetical strategy or clearly marked public market examples.

---

## 11. Demo Screens

Minimum demo screens:

```text
1. Home page
2. Strategy input page
3. Loading / analysis progress state
4. Report page
5. Sources panel
6. Markdown export view
```

Optional screens:

```text
1. Protocol library
2. Previous reports
3. Data source status
4. Risk framework explainer
5. Developer ingestion panel
```

---

## 12. Demo Storage

The demo should store:

```text
reports
analysis requests
retrieved source references
risk score outputs
manual data inputs
cached market data
document metadata
```

The demo does not need to store:

```text
wallet addresses
private keys
user portfolio balances
signed transactions
sensitive personal data
```

---

## 13. Demo Observability

The backend should log:

- request ID
- analysis start and end
- detected protocols
- data adapters called
- missing data fields
- risk score
- report generation status
- errors

Future versions may add:

- structured logging
- trace IDs
- background job status
- admin dashboard
- cost tracking for LLM calls

---

## 14. Failure Handling

The demo should handle common failures gracefully.

Examples:

```text
LLM provider unavailable:
Return a clear error and suggest retry or local model configuration.

Market API rate-limited:
Use cached data or mark the field as unavailable.

No relevant RAG source found:
State that the system could not find enough source material.

Missing strategy parameters:
Generate a partial report and list required missing fields.

Vector database unavailable:
Return a clear backend health error.
```

The system should prefer partial, transparent analysis over unsupported conclusions.

---

## 15. Future Demo Extensions

After the MVP demo, the architecture can evolve into:

## 15.1 Source Monitoring

A background worker monitors:

- new Pendle markets
- new Morpho vaults
- new Aave reserves
- new governance proposals
- new protocol documentation
- major TVL changes
- borrow APY changes

Detected items can be evaluated and queued for RAG ingestion.

## 15.2 Watchlist and Alerts

Users can define strategy watchlists.

Alerts can trigger when:

- borrow APY rises above strategy yield
- liquidity drops below threshold
- LTV approaches danger zone
- Health Factor approaches liquidation risk
- PT maturity is approaching
- governance proposal changes risk assumptions

## 15.3 Strategy Simulator

The simulator can test:

- collateral price drop
- borrow APY increase
- liquidity reduction
- early exit before maturity
- oracle delay
- incentive removal
- slippage increase

## 15.4 Options and Volatility Agent

Future support for Derive-style options analysis:

- calls
- puts
- strike price
- expiration
- implied volatility
- bid/ask spread
- breakeven
- max loss
- risk/reward scenarios

## 15.5 Fine-Tuning

Fine-tuning can be added after enough reports and labels exist.

Possible use cases:

- risk classifier
- RAG reranker
- report style model
- DeFi strategy type classifier

## 15.6 HPC Readiness

Future HPC support can include:

- batch document ingestion
- large-scale embedding generation
- model fine-tuning
- retrieval evaluation
- benchmark jobs
- SLURM scripts
- Apptainer or Singularity container support

---

## 16. Demo Completion Checklist

The demo architecture is complete when:

- [ ] frontend can submit a strategy prompt
- [ ] backend receives and validates the request
- [ ] protocols are detected
- [ ] RAG retrieves relevant documentation
- [ ] market data is fetched or marked as missing
- [ ] risk score is generated
- [ ] structured report is created
- [ ] report is displayed in the UI
- [ ] sources are visible
- [ ] disclaimer is visible
- [ ] markdown export works
- [ ] Docker Compose runs locally
- [ ] README links to this document
- [ ] demo video can show the full workflow in under four minutes

---

## 17. Final Demo Definition

The demo is complete when a reviewer can open the application, submit a DeFi strategy prompt, and receive a structured, source-backed risk report that clearly explains the strategy, assumptions, risks, missing data, monitoring checklist, and safety disclaimer.

At this stage, the application is not a trading terminal. It is a safe and explainable AI research copilot for DeFi strategy analysis.

# RAG Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The RAG layer grounds DeFi analysis in curated protocol documentation, internal risk notes, and human-approved discovered sources.

The LLM should not answer protocol-specific questions from memory alone. It should retrieve relevant documentation before generating or synthesizing report sections.

## 2. Current Knowledge Base

Current knowledge base:

```text
knowledge_base/
├── pendle/
├── morpho/
├── aave/
├── chainlink/
├── internal_notes/
└── discovered/        # planned Phase 10 controlled ingestion target
```

Current behavior:

- curated markdown files
- markdown/header-aware chunking
- metadata extraction
- lightweight local hash embeddings
- JSON vector index
- source references in reports
- optional hybrid retrieval with keyword, vector, metadata, source quality, freshness, and reranking signals
- optional deterministic local semantic embedding provider for offline evaluation
- citation metadata validation for retrieved chunks

## 3. Ingestion Flow

Current curated ingestion:

```text
Curated source documents
    -> document loader
    -> text cleaning
    -> chunking
    -> metadata extraction
    -> embedding generation
    -> local vector store
```

Planned Phase 10 controlled ingestion:

```text
Auto-discovered candidate
    -> normalized discovered item
    -> automated evaluation
    -> human review
    -> approved_for_rag
    -> explicit ingest-to-RAG action
    -> curated markdown under knowledge_base/discovered/
    -> RAG index refresh
    -> retrieval evaluation
```

The app must never ingest a newly discovered source automatically. Human approval and an explicit ingestion action are required.

## 4. Required Metadata

Every ingested chunk should preserve metadata such as:

- protocol
- source URL
- source type
- document title
- section title
- ingestion date
- discovery source
- review status
- reviewer notes if available
- source quality level
- freshness status
- risk category if available

For discovered sources, generated markdown must clearly state that the item was automatically discovered and human-approved before ingestion.

## 5. Retrieval Strategy

The retriever should return:

- top relevant chunks
- source metadata
- similarity score
- protocol label
- document title
- section title

Advanced retrieval already supports optional hybrid retrieval, local semantic signals, metadata filters, source quality scoring, freshness scoring, reranking, citation validation, and retrieval evaluation metrics.

Default report retrieval remains safe and deterministic. Optional semantic retrieval is controlled by environment configuration.

## 6. Prompt Construction for Optional LLM Synthesis

The optional LLM prompt should include:

1. user request
2. normalized strategy data
3. retrieved protocol context
4. market data summary
5. risk scoring output
6. missing data
7. required report template
8. safety rules
9. citation instructions

The LLM must not:

- invent missing fields
- change deterministic risk score
- remove disclaimers
- provide direct buy/sell instructions
- hide uncertainty

If LLM synthesis fails or is disabled, deterministic report generation remains the fallback.

## 7. RAG Evaluation

Retrieval evaluation should check whether the retriever finds correct information for questions such as:

- What is a Pendle PT?
- What is fixed yield?
- What is LLTV?
- What is Health Factor?
- What is liquidation risk?
- What is oracle risk?
- What is maturity risk?

Post-MVP retrieval evaluation includes a stored JSON evaluation dataset, citation coverage checks, source freshness/quality signals, and JSON metrics written by `backend/scripts/evaluate_retrieval.py`.

## 8. Phase 10 Requirements

Phase 10 must add the missing bridge from reviewed discoveries into the knowledge base:

```text
POST /api/evaluation/review-items/{review_item_id}/ingest-to-rag
```

Rules:

- only `approved_for_rag` items can be ingested
- rejected, archived, `needs_review`, or `needs_more_data` items cannot be ingested
- duplicate ingestion must be prevented
- generated markdown must include source URL and review metadata
- RAG index refresh must run after successful ingestion
- future analysis reports may cite ingested discovered sources

## 9. Guardrails

RAG improvements must preserve:

- visible citations
- visible missing data
- source freshness metadata
- source quality metadata
- deterministic fallback
- human approval before trusting monitored sources
- no autonomous financial advice
- no wallet or transaction execution

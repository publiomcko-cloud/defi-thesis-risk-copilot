# RAG Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The RAG layer exists to reduce hallucination and ground DeFi analysis in protocol documentation and curated risk notes.

The LLM should not answer protocol-specific questions from memory alone. It should retrieve relevant documentation before generating or synthesizing report sections.

The Phase 10 baseline uses a curated local knowledge base, lightweight hash embeddings, and a JSON vector store. Post-MVP work should improve retrieval quality and add controlled ingestion from reviewed discovered sources.

## 2. Current MVP Knowledge Base

Initial knowledge base:

```text
knowledge_base/
├── pendle/
├── morpho/
├── aave/
├── chainlink/
└── internal_notes/
```

Current behavior:

- local curated markdown files
- markdown/header-aware chunking
- metadata extraction
- lightweight local hash embeddings
- JSON vector index
- source references in reports

## 3. Ingestion Flow

```text
Source documents
    |
    v
Document loader
    |
    v
Text cleaning
    |
    v
Chunking
    |
    v
Metadata extraction
    |
    v
Embedding generation
    |
    v
Vector database or local vector store
```

## 4. Chunking Strategy

The MVP should use simple semantic chunking or markdown-header-aware chunking.

Recommended metadata:

- protocol
- source URL
- document title
- section title
- ingestion date
- content type
- risk category
- version or date if available
- source quality level
- freshness status
- review status

## 5. Retrieval Strategy

The retriever should return:

- top relevant chunks
- source metadata
- similarity score
- protocol label
- document title
- section title

Current retrieval is sufficient for the MVP, but post-MVP phases should improve:

- hybrid search
- semantic embeddings
- reranking
- query rewriting
- metadata filters
- source quality scoring
- freshness scoring
- citation validation

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
- change the deterministic risk score
- remove disclaimers
- provide direct buy/sell instructions
- hide uncertainty

If LLM synthesis fails or is disabled, deterministic report generation remains the fallback.

Current implementation supports optional backend LLM synthesis after local RAG retrieval. The prompt includes retrieved chunks, market data, deterministic risk components, missing data, and safety rules. The synthesis layer can enrich explanatory wording only; deterministic report fields remain authoritative.

## 7. RAG Evaluation

MVP evaluation should test whether the retriever finds correct information for questions such as:

- What is a Pendle PT?
- What is fixed yield?
- What is LLTV?
- What is Health Factor?
- What is liquidation risk?
- What is oracle risk?
- What is maturity risk?

Post-MVP retrieval evaluation should add:

- a stored evaluation dataset
- expected source IDs or source titles
- faithfulness checks
- citation coverage checks
- stale-source checks
- regression tracking across retriever changes

## 8. Reviewed Source Ingestion

Post-MVP source monitoring may discover new items, but those items should not be blindly ingested.

Recommended flow:

```text
Discovered source
    -> normalized discovered item
    -> automated evaluation
    -> human review
    -> approved_for_rag
    -> ingestion
    -> retrieval evaluation
```

Review statuses:

```text
needs_review
approved_for_rag
rejected
needs_more_data
archived
```

## 9. Active RAG Improvement Phases

Recommended order:

```text
Phase 1: optional LLM synthesis using current RAG context
Phase 2: source monitoring creates discovered items
Phase 3: reviewed items become RAG ingestion candidates
Phase 7: semantic embeddings, hybrid retrieval, reranking, and eval dataset
Phase 8: export retrieval/report examples for future fine-tuning
```

## 10. Future RAG Guardrails

Future RAG improvements must preserve:

- visible citations
- visible missing data
- source freshness metadata
- source quality metadata
- deterministic fallback
- human review before trusting monitored sources

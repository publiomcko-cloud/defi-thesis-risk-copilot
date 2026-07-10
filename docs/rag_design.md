# RAG Design — DeFi Thesis & Risk Copilot

## 1. Purpose

The RAG layer exists to reduce hallucination and ground DeFi analysis in protocol documentation and curated risk notes.

The LLM should not answer protocol-specific questions from memory alone. It should retrieve relevant documentation before generating the final report.

## 2. MVP Knowledge Base

Initial knowledge base:

```text
knowledge_base/
├── pendle/
├── morpho/
├── aave/
├── chainlink/
└── internal_notes/
```

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
Vector database
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

## 5. Retrieval Strategy

The retriever should return:

- top relevant chunks
- source metadata
- similarity score
- protocol label
- document title
- section title

Future improvements:

- hybrid search
- reranking
- query rewriting
- metadata filters
- source quality scoring
- freshness scoring

## 6. Prompt Construction

The final LLM prompt should include:

1. user request
2. normalized strategy data
3. retrieved protocol context
4. risk scoring output
5. required report template
6. safety rules
7. citation instructions

## 7. RAG Evaluation

MVP evaluation should test whether the retriever finds correct information for questions such as:

- What is a Pendle PT?
- What is LLTV in Morpho?
- What is Health Factor in Aave?
- What is oracle risk?
- What is liquidation risk?
- What happens near PT maturity?

## 8. Future RAG Improvements

Future phases:

- fine-tuned reranker
- dataset of DeFi retrieval questions
- answer faithfulness evaluation
- citation validation
- automatic stale-document detection
- scheduled documentation refresh

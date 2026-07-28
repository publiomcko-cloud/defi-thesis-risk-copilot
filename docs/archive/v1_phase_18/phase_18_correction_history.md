# Phase 18 Correction History

Phase 18 corrections preserved the public JSON path while hardening the durable path:

- added generation-specific embeddings, exact active-generation selection, same-profile rollback, and the reversible `0021` migration;
- derived authenticated public/private/organization retrieval scope exclusively on the server and preserved anonymous public-only behavior;
- made curated corpus import convergent, fail-closed on deterministic-ID collisions, and compensating across object writes and database failure;
- added retrieval evaluation with declared relevant lineage, expected-empty cases, citation checks, and tenant-leakage coverage;
- added pgvector extension preflight and metadata-only account export for private knowledge;
- hardened object ownership tracking so only objects created by the current import attempt are compensated;
- made the operator import own final database commit and compensate created objects after flush or commit failure;
- extended repair to validate chunk content/checksums/metadata and deterministic embedding dimensions, values, checksums, and populated PostgreSQL vectors.

The complete implementation chronology and slice gates are retained in the [archived execution plan](phase_18_execution_plan.md) and repository history.

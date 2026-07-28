# Phase 18 Migration and Rollback Notes

Phase 18 introduced additive migrations:

| Revision | Purpose |
| --- | --- |
| `0017` | durable knowledge-source, document, immutable-version, and chunk foundation |
| `0018` | pgvector embedding structures and index support |
| `0019` | privacy-safe shadow retrieval events |
| `0020` | lifecycle, tombstone, and cleanup support |
| `0021` | generation-specific embeddings and exact active-generation selection |

The PostgreSQL `vector` extension must be provisioned by a database administrator before application migrations; application migrations intentionally do not create it. Run `python -m scripts.preflight_pgvector` before enabling vector-backed behavior.

Migration `0021` fails closed on downgrade once multiple completed generations exist for a version/profile, rather than discarding historical embeddings. That behavior protects data but means production rollback is feature-flag based, not destructive schema downgrade. Migrations do not import objects, rebuild embeddings, or activate durable retrieval.

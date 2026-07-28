# Phase 18 Deployment, Cutover, and Rollback Notes

All durable knowledge capabilities are feature-gated and disabled by default. A controlled deployment begins with non-mutating readiness checks and a synthetic tenant/private-bucket probe. It must then validate worker access, object policy, pgvector readiness, tenant isolation, shadow metrics, and report citation behavior before any primary retrieval flag is considered.

Do not enable all flags together. Keep the local JSON RAG path available throughout validation. The supported production rollback after activation is disabling `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED`, which returns report retrieval to JSON without deleting durable knowledge records. Do not use schema downgrade as an operational rollback plan.

Phase 19 may collect observability, readiness, shadow-mode, alerting, and controlled deployment evidence. Phase 22 retains authority for final deployed storage-policy proof, two-user verification, worker verification, launch approval, and the final release claim. Real Vast.ai rentals remain disabled.

# V1 Phase 18 Archive — Production RAG and Knowledge Storage

Phase 18 was merged into `main` by PR [#4](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/pull/4) on 2026-07-28 (`53d87ad`). It delivered the complete code and local/CI validation record for durable, tenant-safe knowledge storage and retrieval.

Phase 18 is not a production cutover claim. The knowledge-storage, ingestion, embedding, shadow-retrieval, corpus-import, and durable-primary flags remain disabled by default. The checked-in curated Markdown/local JSON RAG path remains the production fallback and immediate rollback path. Controlled deployment evidence may be gathered during Phase 19; final deployed validation and launch approval remain Phase 22 responsibilities. Real Vast.ai rentals remain disabled.

## Archived evidence

- [Execution plan and completion gates](phase_18_execution_plan.md)
- [Final validation summary](phase_18_validation_summary.md)
- [Correction history](phase_18_correction_history.md)
- [Deployment, cutover, and rollback limitations](phase_18_deployment_and_cutover.md)
- [Migration and rollback notes](phase_18_migration_notes.md)

The retrieval-evaluation dataset is retained at [`backend/retrieval_eval_dataset.json`](../../../backend/retrieval_eval_dataset.json), and the evaluation command is documented in the validation summary. Historical implementation code, tests, migrations, and CI workflows remain in the repository history and `main`.

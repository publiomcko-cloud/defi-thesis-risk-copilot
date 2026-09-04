# Phase 21 Evidence Matrix

Status: **Active — 21A not yet implemented.**

Base merge: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Branch: `agent/v1-phase-21-model-research-intelligence`

| Checkpoint | Status | Required evidence |
| --- | --- | --- |
| 21A Model governance foundation | Next | Migration/rollback if used; registry constraints; no credentials; prompt/schema version linkage; bounded model-run provenance; deterministic-field preservation; tenant/privacy/logging/lifecycle tests; existing report-synthesis compatibility; PostgreSQL and default-disabled regression. |
| 21B Evaluation/routing | Planned | Versioned datasets; baseline/candidate metrics; promotion thresholds; one-winner promotion/rollback; task routing; provider/privacy/cost policy; failure/fallback; PostgreSQL concurrency; no browser authority. |
| 21C Quality/feedback | Planned | Citation/source consistency; unsupported-claim checks; injection/poisoning corpus; bounded feedback taxonomy; owner isolation; export/deletion; dataset review/versioning; no automatic training/promotion. |
| 21D Research intelligence | Planned | Thesis/assumption/catalyst/report comparison/staleness/scenario workflows; provenance; uncertainty; tenant isolation; browser UX; no execution/advisory regression. |
| 21E Worker compute/training governance | Planned | Phase 17 job authority; local/fake/dry-run compute; cost/capacity/cancellation/cleanup; dataset provenance/splits/leakage checks; model card; no private-tenant training; no real rental in CI. |
| 21F Closeout | Planned | Full PostgreSQL/backend/frontend/browser/Compose/security regression; migration-cycle evidence; exact-head hosted CI; docs; Phase 22 handoff. |

## Entry evidence

The entry architecture review confirms that the repository already has:

- provider interfaces and Ollama/OpenAI-compatible adapters;
- optional report synthesis with strict JSON parsing and deterministic-field
  restoration;
- code-owned prompt safety rules;
- retrieval/ML evaluation groundwork;
- durable Phase 17 workers and cost controls;
- dry-run/disabled Vast.ai defaults;
- tenant-safe knowledge and Phase 20 portfolio boundaries.

The review also confirms that model registry, prompt-version provenance,
task-level routing, evaluation-before-promotion, model quality/adversarial
regression, feedback governance, dedicated research intelligence, and
worker-bound model evaluation/training lineage remain unimplemented Phase 21
work.

No checkpoint should be marked complete until its concrete implementation and
required evidence are committed and reviewed.

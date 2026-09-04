# Phase 21 Evidence Matrix

Status: **Active — 21A implemented; 21B–21F remain planned.**

Base merge: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Branch: `agent/v1-phase-21-model-research-intelligence`

| Checkpoint | Status | Required evidence |
| --- | --- | --- |
| 21A Model governance foundation | Implemented | Migration `20260904_0030`; code-owned seven-task registry; bounded credential-free model registry/capabilities; immutable prompt/schema/safety checksum record; one immutable, retry-safe report-synthesis provenance row; deterministic fallback/validation; untrusted-source and private/org fail-closed policy. Async analysis derives private/organization scope only from validated durable job ownership and visibility, rejects mismatched worker provenance against the server-configured provider, and never reclassifies it as public. The historical `prompt.v1` seed remains immutable; current `prompt.v2` hashes the complete static contract. Model privacy classification is immutable configured identity. Export/deletion/org/anonymous lifecycle tests; SQLite and PostgreSQL `0029 -> 0030 -> 0029 -> 0030`; PostgreSQL concurrent registry one-winner. Synthesis remains disabled by default and no provider is promoted. |
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

Checkpoint 21A has concrete implementation and local PostgreSQL evidence; its
PASS is limited to that checkpoint. No later checkpoint is complete until its
own implementation and evidence are committed and reviewed.

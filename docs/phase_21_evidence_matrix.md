# Phase 21 Evidence Matrix

Status: **Active — 21A and 21B implemented; 21C–21F remain planned.**

Base merge: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Branch: `agent/v1-phase-21-model-research-intelligence`

| Checkpoint | Status | Required evidence |
| --- | --- | --- |
| 21A Model governance foundation | Implemented | Migration `20260904_0030`; code-owned seven-task registry; bounded credential-free model registry/capabilities; immutable prompt/schema/safety checksum record; one immutable, retry-safe report-synthesis provenance row; deterministic fallback/validation; untrusted-source and private/org fail-closed policy. Async analysis derives private/organization scope only from validated durable job ownership and visibility. The historical `prompt.v1` seed remains immutable; current `prompt.v2` hashes the complete static contract. |
| 21B Evaluation/routing | Implemented | Reversible `0030 -> 0031 -> 0030 -> 0031` SQLite and PostgreSQL cycles; checked-in public/synthetic 14-case `report_synthesis_public_v2` with explicit retrieval fixtures, expected behavior, and failure class; immutable dataset identity, completed runs, case checksums/metrics, route history, and transitions; current `report_synthesis.promotion.v1` policy/checksum, authoritative dataset, and exact prompt linkage required for promotion; explicit platform-admin promotion/rollback only; one lockable active assignment per bounded server environment; unknown environment fails closed. Async jobs capture a secret-free server-owned route snapshot at start and preserve it across retry/recovery. Only `succeeded/accepted` can persist model wording; an authoritative provider or validation failure keeps exact route/evaluation/model provenance while persisting the deterministic baseline. Promotion/rollback are prospective and never rewrite that provenance; spoofed/missing/policy-denied snapshots persist deterministic wording with no forged route claim. Exact adapter/model identity and private/org privacy gates remain enforced. Real PostgreSQL simultaneous-promotion, promotion-vs-rollback, and historical-snapshot route-change tests pass. No automatic promotion, browser authority, paid provider, or production activation. |
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

Checkpoints 21A and 21B have concrete implementation and local PostgreSQL
evidence; each PASS is limited to its checkpoint. 21C remains the next
checkpoint and is not started.

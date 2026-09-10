# Phase 21 Evidence Matrix

Status: **Active — 21A–21C implemented; 21D–21F remain planned.**

21A–21B base merge: PR #32, `37fc065b95434622dbfdf407a2bda7930f2c4547`

Branch: `agent/v1-phase-21c-quality-feedback-governance`

| Checkpoint | Status | Required evidence |
| --- | --- | --- |
| 21A Model governance foundation | Implemented | Migration `20260904_0030`; code-owned seven-task registry; bounded credential-free model registry/capabilities; immutable prompt/schema/safety checksum record; one immutable, retry-safe report-synthesis provenance row; deterministic fallback/validation; untrusted-source and private/org fail-closed policy. Async analysis derives private/organization scope only from validated durable job ownership and visibility. Historical prompt versions remain immutable. |
| 21B Evaluation/routing | Implemented | Reversible `0030 -> 0031 -> 0030 -> 0031` SQLite and PostgreSQL cycles; checked-in public/synthetic 14-case `report_synthesis_public_v2`; immutable dataset identity, completed runs, case checksums/metrics, route history, and transitions; explicit platform-admin promotion/rollback only; one lockable active assignment per bounded server environment. Async jobs capture a secret-free server-owned route snapshot and retain truthful historical route/evaluation provenance while deterministic fallback persists on invalid, denied, or failed output. No automatic promotion, browser authority, paid provider, or production activation. |
| 21C Quality/feedback | Implemented | Reversible `0031 -> 0032 -> 0031 -> 0032` SQLite and PostgreSQL cycles; server-owned source trust classification; `report_synthesis.prompt.v3`; immutable `report_synthesis.quality.v1` evidence; public/synthetic 17-case `report_synthesis_adversarial_v1`; `report_synthesis.promotion.v2` hard quality invariants; async control-plane recomputation of report-verifiable quality, exact bounded worker-evidence agreement, and deterministic fallback preserving truthful failed route provenance; source-poisoning flags remain bounded authenticated-worker evidence after exact execution-route snapshot validation and cannot override a control-plane failure; rollback skips obsolete prompt/policy/dataset evidence. Bounded feedback taxonomy/API/UI, explicit admin review with a safe future reference only, tenant/report access, export, account deletion, organization context clearing, expiry behavior, and comment non-leakage coverage remain intact. No automatic training, dataset mutation, provider activation, or production claim. |
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

The review confirms that the model registry, prompt/version provenance,
task-level routing, evaluation-before-promotion, quality/adversarial
regression, and feedback governance are implemented through 21C. Research
intelligence and worker-bound evaluation/training lineage remain later Phase 21
work.

The 21C closeout security gate also refreshed the frontend to patched
`next@15.5.25` and `sharp@0.35.4` after the hosted production dependency audit
identified newly disclosed high/critical findings in the prior locked versions.
The lockfile was regenerated on a clean Node 24 runner and the production npm
audit passed before the refreshed branch head was submitted to hosted PR CI.

Checkpoints 21A–21C have concrete implementation and local PostgreSQL
evidence; each PASS is limited to its checkpoint. Phase 21 remains active and
21D is next; no production activation is implied.

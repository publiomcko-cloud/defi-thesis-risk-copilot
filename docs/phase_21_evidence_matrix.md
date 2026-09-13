# Phase 21 Evidence Matrix

Status: **Active — 21A–21E implemented locally; 21F remains planned.**

21A–21B base merge: PR #32, `37fc065b95434622dbfdf407a2bda7930f2c4547`

21C merge: PR #33, `772e0a5461a56f52729d8fa91a728594e615e61a`

21D merge: PR #34, `468db4a1529b456afed6d1b5d482c8ea0ff932bd`

Branch: `agent/v1-phase-21e-worker-compute-training-governance`

| Checkpoint | Status | Required evidence |
| --- | --- | --- |
| 21A Model governance foundation | Implemented | Migration `20260904_0030`; code-owned seven-task registry; bounded credential-free model registry/capabilities; immutable prompt/schema/safety checksum record; one immutable, retry-safe report-synthesis provenance row; deterministic fallback/validation; untrusted-source and private/org fail-closed policy. Async analysis derives private/organization scope only from validated durable job ownership and visibility. Historical prompt versions remain immutable. |
| 21B Evaluation/routing | Implemented | Reversible `0030 -> 0031 -> 0030 -> 0031` SQLite and PostgreSQL cycles; checked-in public/synthetic 14-case `report_synthesis_public_v2`; immutable dataset identity, completed runs, case checksums/metrics, route history, and transitions; explicit platform-admin promotion/rollback only; one lockable active assignment per bounded server environment. Async jobs capture a secret-free server-owned route snapshot and retain truthful historical route/evaluation provenance while deterministic fallback persists on invalid, denied, or failed output. No automatic promotion, browser authority, paid provider, or production activation. |
| 21C Quality/feedback | Implemented | Reversible `0031 -> 0032 -> 0031 -> 0032` SQLite and PostgreSQL cycles; server-owned source trust classification; `report_synthesis.prompt.v3`; immutable `report_synthesis.quality.v1` evidence; public/synthetic 17-case `report_synthesis_adversarial_v1`; `report_synthesis.promotion.v2` hard quality invariants; async control-plane recomputation of report-verifiable quality, exact bounded worker-evidence agreement, and deterministic fallback preserving truthful failed route provenance; source-poisoning flags remain bounded authenticated-worker evidence after exact execution-route snapshot validation and cannot override a control-plane failure; rollback skips obsolete prompt/policy/dataset evidence. Bounded feedback taxonomy/API/UI, explicit admin review with a safe future reference only, tenant/report access, export, account deletion, organization context clearing, expiry behavior, and comment non-leakage coverage remain intact. No automatic training, dataset mutation, provider activation, or production claim. |
| 21D Research intelligence | Merged through PR #34 at `468db4a1529b456afed6d1b5d482c8ea0ff932bd` | Reversible `0032 -> 0033 -> 0032 -> 0033` SQLite/PostgreSQL evidence; immutable thesis revisions pin exact append-only assumption record/version state with PostgreSQL current-head locking; first legacy mutation baselines exact pre-update content under the thesis lock; bounded catalyst date precision/uncertainty; destination-thesis-scope evidence enforcement; organization-visible saved theses require current active organization membership/role before base CRUD or 21D research access, so historical creator ownership cannot bypass member removal, disablement, or deletion; visibility moves require target-scope authority and reject retained report-backed evidence whose immutable scope is incompatible with the destination; deterministic comparison computation with checksummed inputs, same-scope authorization, and durable provenance distinguishing deterministic, model-assisted, fallback, and unknown report-section content; citation-lineage current/superseded/deleted/unavailable/unknown signals without report rewriting; deterministic scenario deltas and bounded non-execution monitoring questions; thesis/account/organization lifecycle disposal and export; focused thesis/report UI/BFF contracts. No model route/task, provider activation, automatic schedule/notification, execution, wallet, custody, or advice capability. |
| 21E Worker compute/training governance | Implemented locally; hosted exact-head validation pending | Reversible `0033 -> 0034 -> 0033 -> 0034` SQLite/PostgreSQL migration evidence for immutable `training_dataset_manifests`, `training_dataset_entries`, and `training_runs`; the sole `report_synthesis_training_synthetic_v1` source is checked-in synthetic material, sealed with content/manifest/held-out checksums, deterministic SHA-256 ranked train/validation/test splits, duplicate rejection, and an explicit approved eligibility result. Current Phase 21B/21C evaluation corpus fingerprints, feedback, private user, and organization material are excluded before sealing. A dedicated `model.training.prepare.v1` Phase 17 job accepts only a server-created run identifier, carries an immutable server-owned execution snapshot, and uses the code-owned `local_fake_v1` profile with no provider, network, credentials, GPU, shell, or cost path. Durable global/user/provider reservation rows retain Phase 17 authority; the named profile scope permits one pending/running run and PostgreSQL contention accepts one submission while rejecting the other. Manifest/entry and run-snapshot database guards reject direct mutation. Worker lease/start/retry/cancel/dead-letter paths retain immutable evidence; terminal completion verifies the exact result and creates one checksummed model-card plus receipt metadata pair, while stale/forged completion is rejected. Runs are `not_registry_eligible`; no registry, candidate evaluation, promotion, route, production activation, real weights, real rental, or private-tenant training is created. Account disposal detaches the actor but preserves manifest, entries, and run evidence. The admin UI/API expose profile, manifests, and runs only; no source-body, image, offer, credential, or shell control is exposed. |
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
regression, feedback governance, and deterministic research intelligence are
implemented through 21D. Worker-bound evaluation/training lineage remains later
Phase 21 work.

The 21C closeout security gate also refreshed the frontend to patched
`next@15.5.25` and `sharp@0.35.4` after the hosted production dependency audit
identified newly disclosed high/critical findings in the prior locked versions.
The lockfile was regenerated on a clean Node 24 runner and the production npm
audit passed before the refreshed branch head was submitted to hosted PR CI.

Checkpoints 21A–21E have concrete implementation and local evidence; each PASS
is limited to its checkpoint. Phase 21 remains active, 21F is next, and no
production activation is implied.

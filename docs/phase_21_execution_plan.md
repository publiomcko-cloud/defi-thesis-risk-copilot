# V1 Phase 21 Execution Plan — Model and Research Intelligence Expansion

Status: **Active — checkpoints 21A and 21B implemented; 21C is next.**

Base merge: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Current branch: `agent/v1-phase-21-model-research-intelligence`

Authority:

1. [`portfolio_profile.md`](portfolio_profile.md) — portfolio-vs-product boundary;
2. [`decisions/phase_21_portfolio_scope_approval.md`](decisions/phase_21_portfolio_scope_approval.md) — selected Phase 21 owner scope;
3. this execution plan — checkpoint ordering and implementation constraints;
4. [`phase_21_evidence_matrix.md`](phase_21_evidence_matrix.md) — completion evidence;
5. [`future_phase_contracts.md`](future_phase_contracts.md) — broader Phase 21 product-capable contract;
6. [`productization_backlog.md`](productization_backlog.md) — intentionally deferred provider/commercial work.

## Permanent Phase 21 boundaries

- deterministic risk, market facts, source authority, missing data, and
  disclaimers remain authoritative;
- browser input cannot select or promote a provider/model;
- model/provider credentials never live in registry rows, prompts, analytics,
  logs, or browser payloads;
- private tenant data may leave the trusted boundary only when a server-owned
  provider privacy policy explicitly permits that task/provider combination;
- model output is schema-validated and cannot silently mutate deterministic
  fields;
- retrieved content is untrusted data and cannot become system instructions;
- model feedback does not become training data or promotion evidence
  automatically;
- real Vast.ai rentals and paid provider activation remain disabled unless
  separately approved;
- no wallet, signing, custody, execution, capital allocation, or personalized
  financial advice;
- Phase 15–20 tenant, lifecycle, quota, security, BFF, and rollback boundaries
  remain regression requirements.

## Checkpoint 21A — Model governance foundation

Goal: make the existing optional report-synthesis path versioned, durable,
auditable, and ready for later evaluation/routing without changing its
server-owned deterministic authority.

Implemented scope:

- reconcile stale post-Phase-20 merge documentation first;
- verify Alembic head is `20260828_0029` and no conflicting `0030` exists;
- introduce one reversible Phase 21 governance migration if required;
- code-owned task registry using the approved task taxonomy;
- durable model registry metadata with no credentials;
- durable prompt/schema version metadata linked to code-owned templates;
- task/model capability and route-state metadata sufficient for later
  candidate/baseline/promotion control;
- immutable/bounded model-assisted run provenance;
- retrofit the existing `report_synthesis` path to emit structured provenance
  for disabled, unavailable, success, validation-fallback, and provider-failure
  outcomes;
- record provider/model/prompt/schema identifiers, deterministic input checksum,
  retrieval/source references or bounded hashes, validation outcome, fallback
  reason, latency and bounded cost metadata when available;
- do not persist raw private prompt text or private retrieved chunk bodies in
  operational provenance;
- preserve the current strict JSON validation, safety-language checks, fallback,
  and immutable-field restoration;
- add PostgreSQL migration/constraint/tenant/lifecycle tests;
- keep runtime model synthesis disabled by default.

21A is backend/governance authority. It does not activate new model tasks or
add a public provider-selection UI. Migration `20260904_0030` and the focused
SQLite/PostgreSQL evidence record the implementation; Phase 21 remains active
until every later checkpoint is complete.

## Checkpoint 21B — Evaluation, promotion, routing, rollback

Goal: replace global provider choice with a server-owned task routing decision
that is gated by durable evaluation evidence.

Implemented scope:

- versioned regression datasets and cases;
- baseline/candidate evaluation runs;
- structured-output validity, deterministic preservation, source/citation
  consistency, missing-data honesty, unsafe-language rate, latency and cost;
- task-specific promotion thresholds;
- explicit candidate -> promoted -> rolled_back/retired transitions;
- one authoritative promoted route per task/environment boundary;
- safe fallback to baseline/disabled deterministic behavior;
- provider availability/failure handling;
- tenant/provider privacy classification enforcement;
- no automatic promotion from user feedback;
- PostgreSQL race tests for promotion/rollback authority;
- operator/admin read surfaces only as needed; no browser model authority.

Implementation record:

- reversible migration `20260906_0031_add_model_evaluation_routing.py` follows
  `20260904_0030` without changing 0030 or the reserved 0027 gap;
- checked-in `report_synthesis_public_v2` is a public/synthetic 14-case
  regression corpus. Each case declares a retrieval fixture, expected safe
  result, and expected failure class; SQL stores only its immutable identity/checksum and
  bounded case checksums/results, never prompts, retrieved chunks, outputs, or
  tenant content;
- `report_synthesis.promotion.v1` requires 100% structured validity,
  deterministic preservation, source integrity, and missing-data honesty; zero
  unsafe, privacy, and provider-failure results; and an explicit 1000ms mean
  latency ceiling. Cost is informational when supplied and unknown otherwise;
- a completed passing evaluation remains a candidate until a platform operator
  explicitly promotes it. Immutable route versions and transitions plus one
  lockable assignment give one active route for a task/version/environment;
- `LLM_SYNTHESIS_ENABLED=false` remains the global kill switch. When enabled,
  runtime still falls back unless an active route, exact prompt/evaluation/model
  linkage, exact server-configured adapter identity, and scope privacy policy
  all validate. Configuration alone is not authority;
- only the bounded server environment taxonomy (`development`, `test`,
  `staging`, `production`, `portfolio_demo`, `exercise`) can resolve a route;
  documented `dev`, `testing`, and `prod` aliases normalize server-side, while
  unknown non-empty values fail closed to deterministic output;
- an async analysis captures a secret-free execution-route snapshot in its
  existing server-owned durable job context when the control plane starts it.
  The worker receives that snapshot only through the authenticated start
  response. Completion accepts model wording only when its candidate exactly
  matches the snapshot and its historical route/evaluation/model/prompt
  evidence remains valid. A missing, corrupt, spoofed, or policy-denied
  snapshot persists the explicit deterministic baseline, never relabeled model
  wording;
- promotion and rollback are prospective assignment changes. They do not
  rewrite an already-started valid execution: its immutable provenance keeps
  the recorded execution route if that route's historical evidence remains
  valid. Retries and recovery preserve the original snapshot exactly;
- promotion additionally requires the run's current code-owned policy
  version/checksum, current checked-in dataset identity/checksum/version, and
  exact current prompt linkage. Older completed evidence must be re-evaluated;
- rollback locks the assignment, restores only the promoted route recorded as
  the prior known-good route, or clears the assignment to deterministic output.
  It never searches registered models for a replacement;
- the existing 21A report provenance now records safe route/evaluation IDs for
  successful routed work. The durable worker completion path resolves and
  verifies the same route before accepting worker provenance.

No provider is automatically promoted, no browser can choose a model/provider,
and no paid provider or real Vast.ai rental is activated by 21B.

## Checkpoint 21C — Quality, injection safety, feedback governance

Goal: make model quality measurable and adversarially tested.

Expected scope:

- source/citation consistency scoring;
- unsupported-claim checks;
- prompt-injection and source-poisoning regression corpus;
- instruction-like source-content detection/flagging;
- bounded helpful/incorrect/missing-source/bad-citation/unclear/entity/unsafe
  feedback taxonomy;
- owner/tenant-safe feedback storage;
- dataset-version linkage and explicit review before feedback can enter an
  evaluation dataset;
- no automatic training or promotion;
- privacy/export/deletion behavior and bounded analytics/logging.

## Checkpoint 21D — Research intelligence

Goal: add high-value research workflows that use the evaluated model layer but
remain source-grounded research tools.

Selected portfolio direction:

- thesis status/history;
- explicit assumptions and assumption changes;
- catalyst records/calendar;
- report-to-report comparison;
- source-change/staleness signals;
- scenario comparison;
- bounded monitoring-question generation.

Every generated claim must retain source/provenance and uncertainty. These
features must not generate trade instructions or execute capital actions.

## Checkpoint 21E — Worker compute and training governance

Goal: demonstrate controlled offline model work without requiring real provider
spend.

Expected scope:

- Phase 17 job types for model evaluation and approved training/fine-tuning
  preparation;
- local/fake/dry-run ephemeral GPU execution only by default;
- approved image/model allowlists;
- bounded runtime, concurrency, disk/GPU and cost controls;
- cancellation, retry, cleanup, artifact isolation and idempotency;
- versioned dataset purpose/provenance and train/validation/test splits;
- duplication/leakage checks;
- model-card and limitations artifact;
- no private tenant training data without a new explicit policy/consent
  approval;
- no real Vast rental requirement for portfolio completion.

## Checkpoint 21F — Phase closeout

Goal: prove the complete Phase 21 portfolio architecture and hand off to Phase
22 without adding new capability.

Required:

- full backend/PostgreSQL regression;
- complete Phase 21 migration-cycle evidence;
- frontend/browser/BFF/accessibility/security regression;
- Compose/worker/failure/recovery evidence;
- CodeQL/supply-chain/secret/container checks;
- exact-head hosted CI;
- current-state/architecture/development-plan reconciliation;
- accurate implemented/enabled/disabled/deferred labels;
- Phase 22 handoff with remaining deployed-provider/legal gates intact.

## Checkpoint discipline

- do not begin the next checkpoint before review of the current one;
- each checkpoint must return an explicit PASS/HOLD verdict;
- migrations are added only for durable state actually needed by that checkpoint;
- a later checkpoint may refine a prior schema only through a new reviewed
  migration; never rewrite an already-merged migration;
- no checkpoint is complete merely because interfaces or placeholder rows exist;
- final Phase 21 completion requires exact-head hosted evidence, not local tests
  alone.

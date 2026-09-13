# V1 Phase 21 Execution Plan — Model and Research Intelligence Expansion

Status: **Active — checkpoints 21A–21E implemented locally; 21F is next.**

21A–21B base merge: PR #32, `37fc065b95434622dbfdf407a2bda7930f2c4547`

21C merge: PR #33, `772e0a5461a56f52729d8fa91a728594e615e61a`

21D merge: PR #34, `468db4a1529b456afed6d1b5d482c8ea0ff932bd`

Current branch: `agent/v1-phase-21e-worker-compute-training-governance`

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
  wording. A valid provider or validation failure retains its exact historical
  route/evaluation provenance, but only an accepted synthesis may persist model
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

Implemented scope:

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

Implementation record:

- reversible `20260906_0031 -> 20260907_0032 -> 20260906_0031 ->
  20260907_0032` SQLite and PostgreSQL cycles leave Phase 20F `free-v1` and
  21A–21B structures intact, preserve the intentionally absent `0027`, and
  remove only 21C state on downgrade;
- `report_synthesis.prompt.v3` preserves historical prompt records and marks
  every retrieved chunk as server-classified untrusted evidence. The bounded
  classes are `trusted_code_owned`, `curated_public`, `tenant_private`, and
  fail-closed `untrusted_external`;
- the separate checked-in `report_synthesis_adversarial_v1` corpus has 17
  public/synthetic injection, poisoning, citation, source-replacement,
  missing-data, unsafe-advice, and safe-quoted-discussion cases. SQL stores
  immutable corpus identity/checksum and bounded results, never chunk text;
- `report_synthesis.quality.v1` persists one immutable linked quality record
  per model run. `report_synthesis.promotion.v2` is a new immutable policy
  requiring all hard citation, deterministic, missing-data, uncertainty, and
  source-poisoning invariants. Evaluation remains explicit-operator promotion
  only;
- worker completion treats its quality envelope as bounded execution evidence,
  never final persistence authority. After verifying the server-owned route
  snapshot, the control plane recomputes every report-verifiable v1 invariant
  from the deterministic baseline and proposed report, requires exact agreement
  on those fields, and persists wording only on the authoritative pass. Raw
  retrieval chunks remain outside durable job/provenance state; source-flag and
  poisoning evidence is therefore bounded authenticated-worker evidence tied to
  the verified execution snapshot and can never override a control-plane
  failure. A malformed or disagreeing envelope fails closed. Quality failure
  keeps truthful route, evaluation, and model provenance while persisting the
  deterministic report;
- rollback restores a prior route only when its route, model, completed
  promotion-eligible evaluation, current prompt, current promotion policy, and
  current ordinary/adversarial datasets still satisfy current authority. An
  obsolete prior route clears the assignment to deterministic/no-model output;
- feedback is limited to the approved taxonomy and accessible report scope.
  It supports explicit server-side review but cannot train, promote, route,
  mutate a prompt, or mutate an evaluation dataset. Lifecycle/export paths keep
  comments out of analytics, audit metadata, logs, prompts, and providers.

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

Implementation record:

- reversible `20260907_0032 -> 20260910_0033 -> 20260907_0032 ->
  20260910_0033` migration coverage creates only `thesis_revisions`, immutable
  `thesis_assumptions` plus lockable heads, `thesis_catalysts`, and compact
  `research_report_comparisons`; the 21A–21C governance/evaluation/quality
  tables and seven `free-v1` limits remain intact;
- existing `saved_theses` remains the CRUD authority. New theses receive an
  immutable initial revision, while legacy records receive one idempotent local
  baseline preserving their exact existing `assumptions_json` before any first
  mutation. A first legacy mutation may initialize revision 1 atomically; once
  a revision exists, mutable thesis/research operations require its exact
  expected revision and stale requests return `409`. Every later material
  thesis/status/assumption/catalyst change appends a revision that pins each
  current immutable assumption record ID and version number;
- report comparisons are deterministic, require access to both reports and an
  identical private owner or organization scope, and evidence attached to a
  thesis must exactly match that destination thesis scope. Comparisons store
  input checksums and compact classification-only diffs, distinguish
  deterministic computation from deterministic, model-assisted, fallback, or
  unknown report-section content using durable synthesis provenance, and never
  persist report bodies. Citation lineage is checked against current durable
  knowledge source/document/version/chunk state without changing historical
  reports;
- scenario deltas and monitoring questions are deterministic and research-only.
  Questions never create schedules/notifications and reject execution language.
  No Phase 21 model task or provider route was added because the deterministic
  implementation fully meets the checkpoint without weakening 21A–21C policy;
- account deletion, thesis soft deletion, organization deletion/context
  clearing, report access expiry/deletion, and membership revocation fail closed
  through explicit saved-thesis and derived-state disposal authority. An
  organization-visible thesis is governed by its current active organization
  membership and role, never by historical `owner_user_id`; disabled/deleted
  organizations and removed memberships therefore conceal base CRUD and 21D
  research endpoints. A visibility move requires optimistic revision authority
  plus destination-scope authority, and is rejected when any retained
  report-backed authoritative evidence is incompatible with that destination.

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

Implementation record:

- reversible `20260910_0033 -> 20260911_0034 -> 20260910_0033 ->
  20260911_0034` evidence covers the three immutable dataset/run tables and
  preserves Phase 21A–21D, Phase 17 artifacts/jobs, `vast_sessions`, and the
  Phase 20F `free-v1` catalog;
- only `report_synthesis_training_synthetic_v1`, a checked-in synthetic fixture,
  may be sealed. Its code-owned eligibility policy excludes private user data,
  organization data, Phase 21C feedback, and Phase 21B held-out evaluation
  datasets. SHA-256-ranked train/validation/test partitioning and normalized
  content uniqueness prevent deterministic split drift and duplicate rows;
- `model.training.prepare.v1` is a dedicated administrator submission path.
  The client can provide no dataset body, provider/image/offer, credential, or
  shell input. The server creates the immutable manifest/run/execution snapshot
  and Phase 17 idempotency/capacity reservation together;
- `local_fake_v1` has no provider or network path, zero GPU, a 90-second runtime,
  one profile slot, 1 GiB disk ceiling, and zero total/hourly cost. It cannot call
  the existing Vast lifecycle and creates no provider cost reservation;
- terminal control-plane completion validates the deterministic local-fake result
  against the server snapshot, produces checksummed model-card and execution
  receipt artifacts, and explicitly marks the run `not_registry_eligible`.
  No model is registered, evaluated, promoted, or routed automatically;
- cancellation/dead-letter/queue-expiry/authorization-revocation paths preserve
  the run record with an honest terminal state. Account disposal detaches actor
  references but does not delete sealed manifests, entries, or immutable runs.

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

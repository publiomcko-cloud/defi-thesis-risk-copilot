# Phase 21 Architecture Review

Date: 2026-09-04

Base: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Branch: `agent/v1-phase-21-model-research-intelligence`

## Existing foundations to reuse

The repository already has a useful Phase 21 starting point:

- `backend/app/llm/base.py` defines the model provider request/response boundary;
- `backend/app/llm/providers.py` implements Ollama and OpenAI-compatible
  providers behind server-side configuration;
- `backend/app/llm/prompts.py` keeps the current report-synthesis prompt and
  safety rules in code;
- `backend/app/llm/synthesis.py` parses strict JSON, falls back safely, blocks
  advisory phrases, and restores immutable deterministic report fields after
  synthesis;
- `report_writer_agent.py` invokes optional model wording only after retrieval,
  market data, deterministic risk scoring, simulation, and source assembly;
- Phase 7 already provides retrieval evaluation foundations;
- Phase 8 already provides ML/dataset groundwork with deterministic labels
  separated from human labels;
- Phase 17 provides durable jobs, leasing, cancellation, cost/capacity controls,
  and worker identity;
- the Vast.ai path is already dry-run/disabled by default;
- Phases 18–20 provide tenant-aware retrieval, provenance, lifecycle,
  entitlements, security, and portfolio-safe provider gates.

## 21A implemented architecture

Migration `20260904_0030` adds `model_registry`,
`model_task_capabilities`, `model_prompt_versions`, and
`model_run_provenance`. The registry is server-owned and bounded: it stores no
credentials, headers, arbitrary metadata, prompts, source bodies, or model
output. The static task registry contains the approved seven tasks, but only
`report_synthesis` is implemented at runtime.

The existing synthesis path now records one immutable provenance row with a
prompt/schema/safety checksum, safe provider identity when available,
server-derived scope, report-input checksum, bounded retrieval digest/count,
validation and outcome codes, and supplied bounded usage values. A unique
report/task/version constraint provides retry safety. Synthesis remains
disabled by default; unknown/private external provider privacy classification
fails closed before private or organization content is sent. Account deletion,
organization deletion/context clearing, and expired anonymous report cleanup
use existing lifecycle authority.

## 21B implemented architecture

Migration `20260906_0031` adds immutable evaluation-dataset identity,
evaluation-run and bounded case-result evidence, immutable route versions and
transitions, and a single mutable/lockable assignment pointer. It adds only
safe route/evaluation foreign keys to 21A run provenance. The checked-in
`report_synthesis_public_v1` corpus is public/synthetic and is deliberately
not copied into SQL.

The code-owned `report_synthesis.promotion.v1` policy has hard 100% schema,
deterministic, source, and missing-data thresholds; zero unsafe/privacy/provider
failure tolerance; a 1000ms average-latency ceiling; and informational-only
cost accounting. An evaluation completion changes no route. A platform admin
must explicitly promote a completed passing run. PostgreSQL locks serialize the
single assignment, and rollback restores the immutable prior route or clears it
to deterministic/no-model output.

Runtime no longer treats `LLM_PROVIDER` configuration or model registration as
authority. The server first applies the global `LLM_SYNTHESIS_ENABLED=false`
kill switch, then resolves a task/version/server-environment route, exact
evaluation/prompt/model linkage, exact configured adapter identity, and the
existing private/organization privacy policy. Any missing or corrupt state
falls back deterministically. The Phase 17 durable completion path uses the
same resolver before it accepts worker provenance.

## Remaining Phase 21 gaps

The current model path is intentionally simple and does not yet satisfy the
Phase 21 contract:

1. no larger model-specific prompt-injection/source-poisoning corpus exists;
2. human feedback is not yet a bounded, privacy-governed, versioned evaluation
   input;
3. thesis/catalyst/assumption/report-comparison intelligence is not yet a
   dedicated domain;
4. model evaluation/training is not yet represented as bounded Phase 17 worker
   jobs with durable model/dataset lineage.

## Refactoring direction

Phase 21 should extend the existing `app.llm` boundary rather than replace it.
The first checkpoint should separate four concerns that are currently coupled:

```text
code-owned task definition
  -> durable model/prompt registry
  -> server-owned route decision
  -> provider adapter
  -> schema/deterministic validation
  -> bounded run provenance
```

The existing `LLM_SYNTHESIS_ENABLED=false` safety behavior remains the rollback
baseline. No new provider should become production-authoritative merely because
it is registered.

Model evaluation should remain distinct from source-candidate evaluation under
`app.evaluation`; reuse patterns where useful but do not overload source review
records with model-promotion semantics.

## Phase sizing conclusion

Phase 21 is too large for one implementation interaction. Provider routing,
model registry, evaluation/promotion, injection defenses, feedback governance,
research-intelligence features, worker compute, and training governance have
separate data/lifecycle/security concerns. The approved 21A–21F sequence in
`phase_21_execution_plan.md` is therefore the authoritative implementation
order for the portfolio profile.

# Phase 21 Entry Architecture Review

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

## Material Phase 21 gaps

The current model path is intentionally simple and does not yet satisfy the
Phase 21 contract:

1. provider selection is global configuration, not task-level routing;
2. there is no durable model registry with task capability/privacy/evaluation
   and promotion state;
3. prompt/schema templates are code-owned but not durably version-linked to
   model-assisted artifacts;
4. report synthesis records provider/model only in explanatory report text, not
   as structured durable provenance;
5. there is no evaluation-before-promotion state machine or automatic
   regression gate for model candidates;
6. there is no explicit task-level cost/privacy routing policy;
7. retrieved text is placed in the synthesis context without a dedicated
   instruction-like-source classification/flagging layer;
8. there is no model-specific prompt-injection/source-poisoning regression set;
9. human feedback is not yet a bounded, privacy-governed, versioned evaluation
   input;
10. thesis/catalyst/assumption/report-comparison intelligence is not yet a
    dedicated domain;
11. model evaluation/training is not yet represented as bounded Phase 17 worker
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

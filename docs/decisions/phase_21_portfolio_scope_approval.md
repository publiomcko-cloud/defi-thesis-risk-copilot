# Phase 21 Portfolio Scope Approval

Date: 2026-09-04

Status: **Approved for implementation — portfolio profile.**

Base merge: `2de0043e2556781d8f34cc9d9308564cc2e3c8a7`

Implementation branch: `agent/v1-phase-21-model-research-intelligence`

## Owner decision

Proceed with Phase 21 as evaluated model and research intelligence architecture.
The objective is to demonstrate production-grade AI engineering without turning
the portfolio into an actively commercialized model service.

This approval does **not** authorize:

- real paid-model or real Vast.ai activation in the public demo or CI;
- browser-selected provider/model authority;
- autonomous model promotion;
- automatic trust of discovered sources;
- training or fine-tuning on private tenant data;
- storing secrets, raw credentials, support/privacy request text, or raw private
  prompts in model provenance records;
- model output replacing deterministic risk, market facts, missing data,
  citations, source authority, or disclaimers;
- wallet connection, transaction signing, custody, trade execution, personalized
  financial advice, or capital allocation.

## Initial task taxonomy

The Phase 21 registry may recognize these code-owned task keys:

- `report_synthesis`
- `strategy_parsing`
- `source_classification`
- `retrieval_reranking`
- `entity_extraction`
- `scenario_explanation`
- `research_summarization`

Only an actually implemented and evaluated task may become runtime-promoted.
At Phase 21 entry, `report_synthesis` is the only existing model-assisted runtime
path. Merely registering another task does not make it implemented or enabled.

## Authority boundaries

- task/provider/model selection is server-owned;
- model and prompt versions are immutable once referenced by durable evidence;
- provider credentials remain in the existing server-side credential/settings
  boundaries and never enter the registry;
- evaluation is required before promotion;
- promotion and rollback are explicit server-side state transitions;
- runtime feedback never promotes a model automatically;
- deterministic output fields remain authoritative after every model call;
- retrieved/source content is untrusted data, never instructions;
- tenant/provider privacy policy is checked before a private prompt can leave the
  trusted boundary;
- default public configuration remains model-disabled unless a separately
  approved route is enabled.

## Provenance policy

Durable model-run evidence should contain bounded metadata and references, not
raw sensitive payloads. It may record:

- task key;
- provider/model/version identifiers;
- prompt/schema version identifiers and checksums;
- tenant-safe resource references;
- retrieval/source identifiers or bounded hashes;
- deterministic-input checksum;
- structured validation result;
- fallback/rollback path;
- latency and bounded cost metadata;
- evaluation lineage;
- bounded human feedback linkage when later approved.

It must not persist provider secrets, authorization headers, cookies, raw private
prompt bodies, raw private retrieved chunks, or unrestricted model responses as
operational metadata.

## Migration policy

Phase 20 ends at `20260828_0029`. Phase 21 may begin with `0030` only after the
implementation confirms no conflicting migration exists and that the current
Alembic head is exactly `0029`. `0027` remains reserved/deferred for Phase 20G
billing and must not be fabricated.

## Checkpoint sequence

Phase 21 is intentionally subdivided. Completion of one checkpoint does not
imply completion of Phase 21.

1. **21A — Model governance foundation**: durable model/prompt/task registry,
   bounded model-run provenance, compatibility with existing report synthesis,
   deterministic-field preservation, privacy/source-safety baseline.
2. **21B — Evaluation and routing**: regression datasets, baseline/candidate
   evaluation, explicit promotion/rollback, server-owned task routing,
   provider failure/fallback, cost/privacy policy.
3. **21C — Quality and feedback**: source/citation consistency metrics,
   prompt-injection/source-poisoning regression, bounded user feedback, dataset
   versioning and privacy controls.
4. **21D — Research intelligence**: selected thesis/catalyst/assumption/report
   comparison and stale-research workflows, preserving research-only and
   non-execution boundaries.
5. **21E — Worker compute and training governance**: Phase 17 worker-bound
   evaluation/training jobs, fake/local/dry-run ephemeral compute, dataset/model
   cards, cost/cleanup/rollback evidence; no real rental requirement.
6. **21F — Architecture closeout**: full regression, security, PostgreSQL,
   browser, Compose, hosted exact-head CI, documentation and Phase 22 handoff.

Do not begin a later checkpoint until the current checkpoint has been reviewed
and accepted.

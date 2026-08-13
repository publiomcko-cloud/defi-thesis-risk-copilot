# Project Memory — Stable Context

Status: **Stable agent context**

Purpose: give a new implementation agent a compact, durable understanding of this repository after a chat/context reset. This file summarizes stable architecture, trust boundaries, phase history, and documentation precedence. It is not a substitute for checking the current branch, migration head, tests, or active phase evidence before making changes.

## 1. Project identity

DeFi Thesis & Risk Copilot is a production-grade **portfolio anchor** for applied AI, data/retrieval, backend, security, and SaaS architecture.

The system turns a DeFi strategy thesis into a structured, source-grounded research report with deterministic risk scoring, visible assumptions, missing data, stress scenarios, provenance, and monitoring requirements.

Current development optimizes for engineering credibility rather than operating a commercial SaaS business. The architecture must remain convertible back into a real product. Product-only requirements are preserved in [`../productization_backlog.md`](../productization_backlog.md).

The project does **not** connect wallets, sign transactions, hold funds, execute trades, allocate capital automatically, or provide personalized financial advice.

## 2. High-level architecture

Public/deployed shape:

```text
Browser
  -> Vercel Next.js frontend/BFF
  -> Render FastAPI backend
  -> Supabase PostgreSQL
```

Authenticated flows use managed/anonymous HttpOnly cookies at the BFF, backend token verification, and application-database authorization.

Important subsystems:

- Next.js frontend and BFF/API proxy boundaries;
- FastAPI API and domain services;
- PostgreSQL/Alembic persistence and concurrency controls;
- Phase 16 identity, ownership, organizations, quotas, consent, export, deletion, and audit foundations;
- Phase 17 durable jobs, workers, retries, idempotency, cancellation, recovery, capacity, and cost controls;
- Phase 18 durable knowledge metadata, guarded private storage/vector retrieval, citation lineage, and JSON RAG fallback;
- Phase 19 observability, rate limiting, edge/upload hardening, security scans, recovery evidence, incident runbooks, and failure exercises;
- Phase 20A governance/privacy/provider/data-model contracts;
- Phase 20B first-party consent-aware product analytics.

Optional model synthesis and heavy compute must remain non-authoritative and safely disableable.

## 3. Permanent trust and product boundaries

These invariants survive phase/profile changes unless an explicit reviewed architecture decision changes them.

### Deterministic authority

Model-generated text cannot silently replace authoritative deterministic values such as:

- risk score/rating;
- market values;
- assumptions and missing-data state;
- protocol identity;
- source/citation references;
- required disclaimers.

### Identity is not authorization

Authentication establishes who the actor is. Server/database state establishes authorization, including:

- platform/account state;
- resource ownership;
- organization membership and role;
- visibility;
- plan/entitlement state;
- quota.

Never trust browser-provided owner IDs, organization scope, plan names, quantities, provider state, or privilege claims as authorization.

### Tenant isolation

Derive tenant scope server-side and apply it consistently to list/detail/create/update/delete/export paths, workers, background jobs, retrieval, analytics, and future support/commercial domains.

### Retrieval trust

Discovery does not imply trust:

```text
discovery
  -> evaluation
  -> human review
  -> approved_for_rag
  -> explicit ingestion
```

Private/vector retrieval remains guarded and must preserve server-derived scope. JSON/public fallback remains a safe rollback path until cutover evidence says otherwise.

### Separate control domains

Do not collapse these concepts into one counter or authority:

- network rate limiting;
- product quotas;
- plan entitlements;
- usage metering;
- product analytics;
- operational telemetry;
- security/audit records;
- future billing evidence.

A user analytics opt-out must never suppress required security, audit, reliability, quota, or lifecycle evidence.

### Lifecycle authority

Existing Phase 16 account/organization export and deletion mechanisms remain authoritative. Later phases extend them through projections/hooks; they do not create competing export/deletion authorities.

### External/secret safety

- Browser code receives only public/safe configuration.
- Provider credentials, signing keys, worker secrets, and opaque external IDs stay server-side.
- External callbacks and outbound destinations require bounded schemas, verification, replay/idempotency controls, and SSRF-safe behavior when applicable.
- Never commit secrets, private customer data, runtime credentials, or production payload fixtures.

## 4. Phase history in one page

| Phase range | Stable result |
| --- | --- |
| 0–14 | MVP and post-MVP research/risk-analysis foundation |
| 15 | Public-safe anonymous/demo deployment profile |
| 16 | Managed identity, ownership, organizations, quotas, consent, lifecycle, export/deletion, frontend account foundations |
| 17 | Durable async jobs/workers, cancellation, idempotency, recovery and controlled Vast job foundations |
| 18 | Durable knowledge/source/document architecture, guarded private storage/vector retrieval, citation lineage, evaluation and JSON fallback |
| 19 | Operations/security foundation: observability, rate limits, edge/upload controls, supply-chain security, recovery, incidents and failure exercises |
| 20A | Threat/privacy/event/usage/entitlement/provider/data-model governance foundation |
| 20B | First-party authenticated opt-in analytics with immutable decision evidence, bounded events, lifecycle integration and deployment-disabled production activation |

Current portfolio roadmap is governed by [`../portfolio_profile.md`](../portfolio_profile.md) and [`../phase_20_execution_plan.md`](../phase_20_execution_plan.md), not by older commercial-roadmap prose that may remain in historical/living documents.

## 5. Safe feature posture

Unless a later reviewed phase explicitly changes them, preserve these safe defaults/postures:

- `PRODUCT_ANALYTICS_ENABLED=false` in production;
- `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` until controlled cutover evidence exists;
- private/RAG functionality remains feature-gated with safe JSON/public fallback;
- `VAST_DRY_RUN=true`;
- `VAST_REAL_RENTALS_ENABLED=false`;
- public demo remains bounded and cannot gain administrative/internal capabilities through browser input.

A feature may be **implemented** while remaining intentionally **disabled in production**. Do not confuse implementation-complete with production-activated.

## 6. Documentation precedence for current work

Read in this order:

1. this file for stable context;
2. [`CURRENT_HANDOFF.md`](CURRENT_HANDOFF.md) for the latest recorded development snapshot;
3. [`../portfolio_profile.md`](../portfolio_profile.md) for the active implementation profile;
4. the active phase execution plan and evidence matrix;
5. [`../current_state.md`](../current_state.md) for detailed implementation/deployment history;
6. [`../development_plan.md`](../development_plan.md) for broader historical roadmap context;
7. [`../architecture.md`](../architecture.md), [`../deployment.md`](../deployment.md), and [`../testing.md`](../testing.md) for permanent technical contracts;
8. archived phase records and domain-specific documents when touching those areas;
9. [`../future_phase_contracts.md`](../future_phase_contracts.md) and [`../productization_backlog.md`](../productization_backlog.md) for broader/future product scope.

If documents conflict:

- verify code, migrations, tests, configuration, branch/PR state, and active evidence;
- current portfolio profile + active execution/evidence take precedence over stale commercial roadmap wording;
- never claim planned scaffolding as implemented;
- update the documentation mismatch as part of the scoped task when appropriate.

## 7. Repository working rules

- Work on a scoped branch.
- Inspect the actual diff before editing or staging.
- Preserve prior-phase behavior and safety boundaries.
- Add reversible migrations and PostgreSQL concurrency evidence when persistence/concurrency changes.
- Run the validation required by [`../testing.md`](../testing.md) and the active phase contract.
- Keep documentation synchronized with reality.
- Open draft PRs by default when publication is requested.
- Never merge without explicit project-owner instruction.
- Never mark a phase complete solely because code compiles or a UI renders.

## 8. Resume protocol after context loss

Before implementing anything after a new chat/session/context reset:

1. read this file;
2. read [`CURRENT_HANDOFF.md`](CURRENT_HANDOFF.md);
3. verify the current Git branch/head and compare it with the handoff snapshot;
4. verify open PR state and hosted checks if relevant;
5. verify Alembic migration head;
6. read the active phase execution/evidence documents;
7. inspect the code/tests that implement the subsystem being changed;
8. only then plan or modify the next slice.

`CURRENT_HANDOFF.md` is intentionally time-sensitive. If Git state has advanced, trust verified repository state and update the handoff rather than forcing the repository to match an old snapshot.

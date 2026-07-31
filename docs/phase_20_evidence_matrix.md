# Phase 20 Evidence Matrix

Status: **In Progress — Phase 20B locally implemented; production analytics
activation remains blocked pending qualified privacy/legal review**

Allowed status labels follow [`agent_execution_guide.md`](agent_execution_guide.md):
`Planned`, `In Progress`, `Implemented Foundation`, `Complete`, or `Blocked`.

| Requirement or gate | Status | Phase 20A evidence | Remaining evidence or approval | Earliest dependent slice |
| --- | --- | --- | --- | --- |
| Authoritative Phase 20 scope and dependency graph | Implemented Foundation | [`future_phase_contracts.md`](future_phase_contracts.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md) | Re-review when a new dependency or failure mode is discovered | All |
| Phase 20 threat model | Implemented Foundation | [`phase_20_threat_model.md`](phase_20_threat_model.md) covers analytics, lifecycle, schedules, notifications, metering, billing, organizations, support, providers, and prior-phase regressions | Security, privacy/legal, product, and finance review | All |
| Event-purpose and metadata taxonomy | Complete | Phase 20B: `app/product_analytics/registry.py` enforces the exact four-event, five-field enum registry; negative tests reject undeclared events, fields and values | New approval required for any event, value, purpose, sampling or processor change | 20B |
| Analytics legal basis and consent policy | Implemented Foundation | [`decisions/phase_20b_analytics_approval.md`](decisions/phase_20b_analytics_approval.md) permits explicit opt-in implementation and synthetic/private validation; default and anonymous paths are off | Qualified privacy/legal review by jurisdiction plus production notice/copy approval | 20B production activation |
| Immutable consent/preference evidence decision | Complete | Phase 20B migration `0023`, append-only `privacy_preference_decisions`, current `privacy_preferences`, exact policy-version re-consent, row locking and PostgreSQL races | Production legal gate only; future policy changes require a new version/decision | 20B |
| Phase 16 account export reuse | Complete | Phase 20B safe preference, decision and event projections are registered in existing `/api/account/export` without owner/source identifiers | Add projections for later Phase 20 domains as implemented | 20B and later |
| Phase 16 account deletion reuse | Complete | Phase 20B hooks in existing `/api/account` immediately remove event/projection rows; shared cleanup retains decisions for exactly 30 days then removes them | Legal-hold behavior remains a later qualified-policy decision | 20B and later |
| Organization lifecycle reuse | Implemented Foundation | Existing organization membership/deletion authority identified; no duplicate service proposed | Organization export is a documented gap for 20H; lifecycle/concurrency implementation evidence | 20H |
| Retention classification | Complete | Phase 20B event expiry is 30 days; withdrawal deletes immediately; decision evidence is account life plus 30 days; dry-run cleanup is covered | Qualified privacy/legal production review; later domains need separate periods | 20B |
| Anonymous analytics policy | Complete | Phase 20B has no anonymous schema/identifier/emitter/UI path and APIs require authentication | Any future anonymous proposal requires a separate reviewed design and migration | Future only |
| Operational telemetry separation | Complete | Phase 20B optional emitter has separate tables/purpose, catches failures after primary commits, and does not suppress audit/operations/quota behavior | Continue regression checks in later slices | 20B |
| Usage-unit registry | Implemented Foundation | [`phase_20_usage_entitlement_registry.md`](phase_20_usage_entitlement_registry.md) defines candidate units, meter points, idempotency, reversals, and non-billable defaults | Product/finance approval and runtime reconciliation | 20F |
| Entitlement registry | Implemented Foundation | Candidate feature/limit keys and current `UserModel.plan`/environment fallback are documented | Product/security/finance approval; immutable plan schema and resolver shadow tests | 20F |
| Four control domains remain separate | Implemented Foundation | Network rate limits, product quotas, billable usage, and plan entitlements have separate authorities and identifiers | 20F tests proving no cross-domain write or authorization | 20F |
| Notification classification | Implemented Foundation | [`phase_20_notification_classification.md`](phase_20_notification_classification.md) defines categories, required/optional treatment, content classes, destinations, and verification | Product, privacy/legal, and security approval | 20D/20E |
| Provider ADR process | Implemented Foundation | [`decisions/phase_20_provider_adr_template.md`](decisions/phase_20_provider_adr_template.md) requires data flow, security, privacy, cost, sandbox, failure, rollback, and exit evidence | Human approval of each completed capability ADR | Provider-dependent slices |
| Provider alternatives and scorecards | Implemented Foundation | [`phase_20_provider_scorecards.md`](phase_20_provider_scorecards.md) records candidates, weighted method, hard gates, and `not assessed` results | Evidence collection and approvals; no provider selected | 20E/20G/20I |
| Migration/data-model review | Complete | Phase 20B reversible `20260731_0023` creates the three reviewed tables with deliberate FKs, checks, unique constraints and indexes; SQLite/PostgreSQL cycles pass | Reconfirm head and models before `0024` | 20B onward |
| No migration or runtime change in 20A | Complete | Branch scope check contains documentation artifacts and living-document updates only | Repeat diff-scope check before merge | 20A |
| Preference API and accessible UI | Complete | Phase 20B authenticated GET/PATCH endpoints, strict body, idempotency key, native keyboard switch, default-off/collection-disabled/re-consent states, browser E2E | Qualified review of production copy | 20B |
| Event trigger and idempotency behavior | Complete | Phase 20B successful sync/durable report, terminal durable failure, thesis-save and watchlist-create commit points; source boundary is one-way hashed; concurrent duplicate and withdrawal tests pass | Continue worker failure-path regression in hosted CI | 20B |
| Analytics disabled-by-default rollout | Complete | Phase 20B `.env.example` and both Compose files default false; production configuration fails closed if enabled before approval | Qualified approval and Phase 22 controlled deployed evidence | 20B activation |
| Durable scheduled monitoring | Planned | 20A schedule terms, threat boundaries, proposed `0024`, and candidate usage/entitlement keys | 20A common-definition approval, then 20C schema/API/worker/PostgreSQL evidence | 20C |
| In-app notification domain | Planned | 20A classification, threat boundaries, and proposed `0025` | Approved category model plus 20C outcomes or existing alert source | 20D |
| External notification delivery | Blocked | ADR and scorecard process only | Approved provider/channel ADR, Phase 19 relevant gates, sandbox, and 20E tests | 20E |
| Usage metering and entitlements | Planned | Registry and proposed `0026` only | Product/finance/security approvals and 20F implementation | 20F |
| Billing sandbox | Blocked | ADR template, billing scorecard, threats, and proposed `0027` only | Provider decision, privacy/legal/finance/tax approval, Phase 19 prerequisites, sandbox | 20G |
| Organization commercial workflows | Planned | Proposed invitation/seat/commercial profile boundary and existing authority reuse | 20F plus 20H implementation and PostgreSQL authorization/concurrency tests | 20H |
| Support/status/privacy-request foundation | Planned | Provider-neutral first-party boundary and proposed `0029` | Common privacy/support approval; provider ADR only if an external system is used | 20I |
| Qualified legal/commercial closeout | Blocked | Required decision inventory exists | Qualified review of implemented behavior, providers, terms, privacy, tax/refunds, claims | 20J |
| Phase 19 external operational gates | Blocked | [`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md) remains authoritative | Central telemetry, alert delivery, provider restore, secret rotation, branch protection, and controlled deployment evidence | Provider activation as applicable |
| Final deployed-provider and launch approval | Planned | Explicit Phase 22 handoff retained | Phase 22 production/provider/browser/legal evidence | Phase 22 |

---

## Threat coverage

| Threat IDs | Evidence owner |
| --- | --- |
| `T20-01`, `T20-02`, `T20-03`, `T20-04`, `T20-05`, `T20-06`, `T20-07` | Event/privacy matrix, taxonomy schema/examples, data-model review |
| `T20-08`, `T20-09` | Execution plan, data-model review, future 20C tests |
| `T20-10`, `T20-11`, `T20-12`, `T20-13` | Notification classification, provider ADR template, future 20D/20E tests |
| `T20-14`, `T20-15`, `T20-16` | Usage/entitlement registry, data-model review, future 20F tests |
| `T20-17`, `T20-18` | Provider ADR template, billing scorecard, data-model review, future 20G tests |
| `T20-19` | Data-model review, future 20H authorization/concurrency tests |
| `T20-20`, `T20-21` | Threat/data-model reviews, future 20I role and input tests |
| `T20-22` | Provider ADR template/scorecards and Phase 19 evidence matrix |
| `T20-23`, `T20-24` | Permanent regression suite, JSON fallback and Vast safety checks |

---

## Phase 20B local validation — 2026-07-31

| Validation | Result |
| --- | --- |
| Python compile and SQLite migration/focused lifecycle tests | Pass; `0023` is head and the reversible temporary-database test passes |
| PostgreSQL `upgrade -> downgrade -1 -> upgrade` | Pass against the isolated local PostgreSQL 16/pgvector service |
| Complete backend suite | Pass; 304 passed and 23 PostgreSQL-only tests skipped in the SQLite run |
| Complete PostgreSQL integration suite | Pass; 23 passed, including three Phase 20B contention/idempotency tests |
| Backend smoke, cleanup dry run and durable-job recovery dry run | Pass; no destructive cleanup was run |
| Frontend install, type check, BFF, MFA, accessibility and security contracts | Pass; `npm ci` reports zero vulnerabilities and accessibility covers 31 route pages |
| Production frontend build, browser E2E and route smoke | Pass; browser includes keyboard analytics opt-in/withdrawal and route smoke covers 11 account/auth pages |
| Supply-chain workflow, lockfile and exception policies | Pass |
| Phase 20B JSON Schema 2020-12 taxonomy | Pass; exactly four approved events validate |
| Development, worker-profile and production Compose rendering | Pass |

No production credential, customer data, external analytics processor, browser
analytics SDK, notification send, payment or real Vast rental was used. Hosted
PR checks and production activation evidence remain separate gates.

---

## Phase 20B checkpoint

Phase 20A produced the design and decision artifacts, and the project owner
recorded the scoped Phase 20B implementation approval. Therefore:

- Phase 20 remains `In Progress`;
- Phase 20B is locally implemented and validated;
- production analytics activation remains `Blocked` on qualified privacy/legal
  approval and controlled deployed evidence;
- 20C, 20F, and provider-neutral portions of 20I require approval of their
  applicable common definitions before implementation;
- no provider-dependent slice is eligible;
- no analytics provider or browser SDK is selected, and no production
  collection claim is made.

Evidence must be updated with implementation files, migrations, automated
tests, provider sandbox records, rollout owners, and rollback results as later
slices proceed.

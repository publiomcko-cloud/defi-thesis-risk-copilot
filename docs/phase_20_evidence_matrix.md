# Phase 20 Evidence Matrix

Status: **In Progress — Phase 20A artifacts implemented; human approvals
remain blocked; no Phase 20 runtime capability exists**

Allowed status labels follow [`agent_execution_guide.md`](agent_execution_guide.md):
`Planned`, `In Progress`, `Implemented Foundation`, `Complete`, or `Blocked`.

| Requirement or gate | Status | Phase 20A evidence | Remaining evidence or approval | Earliest dependent slice |
| --- | --- | --- | --- | --- |
| Authoritative Phase 20 scope and dependency graph | Implemented Foundation | [`future_phase_contracts.md`](future_phase_contracts.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md) | Re-review when a new dependency or failure mode is discovered | All |
| Phase 20 threat model | Implemented Foundation | [`phase_20_threat_model.md`](phase_20_threat_model.md) covers analytics, lifecycle, schedules, notifications, metering, billing, organizations, support, providers, and prior-phase regressions | Security, privacy/legal, product, and finance review | All |
| Event-purpose and metadata taxonomy | Implemented Foundation | [`phase_20_event_privacy_matrix.md`](phase_20_event_privacy_matrix.md), documentation JSON Schema, and bounded examples | Product and privacy/legal approval; 20B runtime registry and negative tests | 20B |
| Analytics legal basis and consent policy | Blocked | Default is no optional analytics and no anonymous analytics; required decisions are enumerated | Qualified privacy/legal decision by purpose and jurisdiction; user-facing copy approval | 20B |
| Immutable consent/preference evidence decision | Implemented Foundation | Existing `consent_records` gap analysis and proposed separate granular preference decision ledger in the data-model review | Privacy/legal and architecture approval; migration and concurrency tests | 20B |
| Phase 16 account export reuse | Implemented Foundation | Existing `/api/account/export` remains authoritative; Phase 20 projections are specified, not implemented | Export contract/version design and implementation tests for each new domain | 20B and later |
| Phase 16 account deletion reuse | Implemented Foundation | Existing `/api/account` deletion, retention cleanup, job disposal, and knowledge tombstones remain authoritative | Registered Phase 20 lifecycle hooks, legal-hold rules, cleanup and recovery-guard tests | 20B and later |
| Organization lifecycle reuse | Implemented Foundation | Existing organization membership/deletion authority identified; no duplicate service proposed | Organization export is a documented gap for 20H; lifecycle/concurrency implementation evidence | 20H |
| Retention classification | Blocked | Draft classes and event mappings are in the event/privacy matrix | Privacy/legal approval of periods, legal holds, and deletion/anonymization behavior | 20B and provider slices |
| Anonymous analytics policy | Blocked | Fail-closed default is disabled; short-lived purpose-specific pseudonym is only a proposal | Privacy/legal, security, and product approval; secret rotation and browser behavior evidence | 20B |
| Operational telemetry separation | Implemented Foundation | Purpose matrix keeps Phase 19 operational/security telemetry outside analytics consent | Runtime emitter separation and no-regression tests | 20B |
| Usage-unit registry | Implemented Foundation | [`phase_20_usage_entitlement_registry.md`](phase_20_usage_entitlement_registry.md) defines candidate units, meter points, idempotency, reversals, and non-billable defaults | Product/finance approval and runtime reconciliation | 20F |
| Entitlement registry | Implemented Foundation | Candidate feature/limit keys and current `UserModel.plan`/environment fallback are documented | Product/security/finance approval; immutable plan schema and resolver shadow tests | 20F |
| Four control domains remain separate | Implemented Foundation | Network rate limits, product quotas, billable usage, and plan entitlements have separate authorities and identifiers | 20F tests proving no cross-domain write or authorization | 20F |
| Notification classification | Implemented Foundation | [`phase_20_notification_classification.md`](phase_20_notification_classification.md) defines categories, required/optional treatment, content classes, destinations, and verification | Product, privacy/legal, and security approval | 20D/20E |
| Provider ADR process | Implemented Foundation | [`decisions/phase_20_provider_adr_template.md`](decisions/phase_20_provider_adr_template.md) requires data flow, security, privacy, cost, sandbox, failure, rollback, and exit evidence | Human approval of each completed capability ADR | Provider-dependent slices |
| Provider alternatives and scorecards | Implemented Foundation | [`phase_20_provider_scorecards.md`](phase_20_provider_scorecards.md) records candidates, weighted method, hard gates, and `not assessed` results | Evidence collection and approvals; no provider selected | 20E/20G/20I |
| Proposed migration/data-model review | Implemented Foundation | [`phase_20_data_model_review.md`](phase_20_data_model_review.md) confirms head `20260728_0022`, current authorities, proposed `0023`–`0029`, FKs, lifecycle, indexes, and rollback | Architecture/privacy/security review before migration implementation | 20B onward |
| No migration or runtime change in 20A | Complete | Branch scope check contains documentation artifacts and living-document updates only | Repeat diff-scope check before merge | 20A |
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

## Phase 20A checkpoint

Phase 20A has produced the required design and decision artifacts. It has not
received the human approvals required by its completion gate. Therefore:

- Phase 20 is `In Progress`;
- Phase 20A is an `Implemented Foundation`, not `Complete`;
- 20B is `Blocked` on analytics privacy/legal approval;
- 20C, 20F, and provider-neutral portions of 20I require approval of their
  applicable common definitions before implementation;
- no provider-dependent slice is eligible;
- no production or runtime claim is made.

Evidence must be updated with implementation files, migrations, automated
tests, provider sandbox records, rollout owners, and rollback results as later
slices proceed.

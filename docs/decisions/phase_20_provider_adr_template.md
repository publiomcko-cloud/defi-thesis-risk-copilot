# Phase 20 Provider ADR Template

Status: **Planned — copy this template for a specific capability; no provider
decision is recorded here**

File name:

```text
docs/decisions/phase_20_<capability>_provider.md
```

Do not replace this template with provider marketing material. Cite reviewed
contracts, security documentation, DPA/subprocessor records, sandbox evidence,
and repository tests. Do not place credentials, customer data, private URLs,
contract-confidential terms, or raw provider payloads in the ADR.

---

## Decision header

| Field | Value |
| --- | --- |
| Capability | `<analytics/consent/email/webhook/messaging/billing/status/support>` |
| Status | `Planned`, `In Progress`, `Blocked`, `Complete`, or `Implemented Foundation` |
| Decision owner | `<role, not a credential or private contact>` |
| Engineering reviewer | `<role>` |
| Security reviewer | `<role>` |
| Privacy/legal reviewer | `<role>` |
| Product reviewer | `<role>` |
| Finance/commercial reviewer | `<role or not applicable>` |
| Decision date | `<YYYY-MM-DD>` |
| Re-review date | `<YYYY-MM-DD>` |
| Supersedes | `<ADR path or none>` |
| Related Phase 19 gate | `<evidence row/runbook or none>` |
| Target Phase 20 slice | `<20B/20E/20G/20I>` |

An ADR cannot be `Complete` until every required approver has recorded a
decision and the sandbox/rollback evidence exists. Absence of a reviewer is a
`Blocked` state, not implicit approval.

---

## 1. Context and decision

Describe:

- the exact capability and user need;
- why the existing first-party path is insufficient, if applicable;
- whether `defer/no provider` remains viable;
- the selected option, or state `no selection`;
- the scope that remains disabled;
- the earliest rollout environment and feature flag;
- why this decision does not weaken tenant, lifecycle, job, RAG, or provider
  safety boundaries.

Decision:

```text
No selection until this ADR is approved.
```

---

## 2. Alternatives

Include at minimum:

1. first-party implementation where feasible;
2. at least two credible external alternatives;
3. defer/remain unpaid/no external channel;
4. migration/exit from each option.

| Option | Hosting/processor model | Key benefit | Key risk | Evidence references | Hard-gate result | Weighted score |
| --- | --- | --- | --- | --- | --- | --- |
| `<option>` | `<first-party/SaaS/self-hosted/defer>` | `<bounded>` | `<bounded>` | `<links or pending>` | `<pass/fail/pending>` | `<0–500 or withheld>` |

Use the approved method in
[`../phase_20_provider_scorecards.md`](../phase_20_provider_scorecards.md).
Never assign a non-pending score from unreviewed assumptions.

---

## 3. Requirements and exclusions

List:

- functional requirements;
- explicit non-requirements;
- traffic/volume assumptions;
- availability and recovery targets;
- accessibility and localization requirements;
- sandbox/test requirements;
- cost ceiling and approval owner;
- prohibited data and actions;
- public-demo behavior;
- fail-closed and degraded behavior.

The provider must not:

- establish application identity, tenant scope, plan, entitlement, usage
  quantity, billing authority, or resource authorization by itself;
- receive raw private strategy/source/report/support content unless a later
  explicit approved design requires it;
- expose secrets or private provider identifiers to browser JavaScript;
- enable real Vast.ai rentals, trading, signing, custody, or execution;
- disable JSON RAG fallback or broaden knowledge retrieval.

---

## 4. Data-flow diagram

Provide exact flows for:

```text
application -> provider
provider -> exact callback
operator -> provider control plane
user -> application preference/verification
export/deletion -> provider request
failure/rollback -> first-party fallback
```

For every arrow, document:

- initiator and authenticated identity;
- tenant derivation;
- endpoint/allowlist;
- fields and classification;
- encryption;
- retention;
- logs/telemetry;
- retry/idempotency;
- failure response;
- deletion/export propagation.

---

## 5. Data inventory

| Field/category | Purpose | Direction | Provider retention | Application retention | Export | Deletion | Prohibited joins |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<field>` | `<purpose>` | `<to/from>` | `<period>` | `<period>` | `<behavior>` | `<behavior>` | `<domains>` |

Required statements:

- whether personal data is processed;
- whether special/sensitive financial or support data is processed;
- whether identifiers are direct, pseudonymous, or provider-generated;
- whether provider logs contain payloads;
- whether subprocessors receive data;
- whether cross-border transfers occur;
- whether training/advertising/secondary use is contractually disabled;
- whether provider export/deletion APIs meet the lifecycle requirements.

---

## 6. Privacy and legal review

Record reviewed evidence for:

- purpose and legal basis/consent;
- DPA and controller/processor roles;
- subprocessor list/change notice;
- data location and transfers;
- retention and deletion;
- data-subject export/access/deletion;
- cookie/browser SDK behavior;
- marketing/electronic communication rules;
- tax, refund, trial, grace, cancellation, and merchant-of-record obligations
  for billing;
- public terms/privacy/subprocessor copy;
- qualified reviewer decision.

Internal drafting is not legal certification.

---

## 7. Security review

Cover:

- credential types, scope, storage, rotation, emergency revocation, and owner;
- server-only versus public configuration;
- exact callback/signature/replay/body/idempotency controls;
- outbound SSRF/DNS/redirect/timeout/response-size controls;
- destination verification and revocation;
- tenant isolation and server-derived authorization;
- admin role/MFA/audit;
- provider dashboard RBAC;
- SDK/package provenance and CI scanning;
- incident notification and evidence handling;
- sandbox/production separation;
- abuse, rate, spend, and volume limits;
- compromise and outage behavior.

Reference relevant Phase 19 evidence. A local runbook does not prove deployed
secret rotation, alert delivery, restore, or protected-branch enforcement.

---

## 8. Reliability and operations

Document:

- SLO/SLA and dependency criticality;
- timeout, retry, backoff, dead-letter, and circuit behavior;
- idempotency and ordering semantics;
- authoritative reconciliation path;
- queue/capacity/spend limits;
- monitoring signals and alert owner;
- status page/support path;
- backup/export and recovery;
- provider outage fallback;
- data consistency after retry/recovery;
- on-call and escalation evidence.

---

## 9. Commercial and portability review

Document:

- sandbox and expected production pricing;
- fixed, usage, overage, egress, support, and tax costs;
- free-tier limitations;
- contract term/termination;
- merchant-of-record or processor responsibilities;
- refund/dispute handling;
- data/config/template export;
- replacement adapter boundary;
- lock-in;
- migration time and cost;
- deletion after termination.

Do not commit confidential negotiated pricing. Store it in an approved private
commercial system and reference only an evidence identifier.

---

## 10. Implementation plan

List:

- adapter interface and implementation files;
- schema/migration;
- exact API/BFF route additions;
- frontend controls and disabled states;
- environment variables and secret owners;
- Phase 17 job type/scopes;
- audit events;
- export/deletion/retention hooks;
- test fakes and sandbox;
- rollout flag/mode;
- monitoring and rollback.

No implementation begins while the ADR is `Blocked`.

---

## 11. Tests and evidence

At minimum:

- authorization and tenant isolation;
- secret/redaction/no-browser-exposure;
- schema and measured body bounds;
- signature/replay/idempotency/concurrency/order where applicable;
- SSRF/destination verification for outbound callbacks;
- retry/dead-letter/outage/recovery;
- consent/preference/export/deletion/retention;
- provider sandbox with synthetic identities and no customer data;
- public-demo regression;
- Phase 17 worker/recovery where used;
- no change to JSON RAG fallback or Vast safety;
- rollback exercise.

Record commands, run identifiers, date, environment classification, and
aggregate secret-free outcome.

---

## 12. Rollout and rollback

Rollout:

1. merge schema/adapter disabled;
2. use provider fake;
3. use isolated provider sandbox with synthetic data;
4. enable a private test scope;
5. monitor bounded signals;
6. expand only with approval;
7. retain first-party/defer fallback.

Rollback:

- disable new submission/application;
- preserve immutable consent/audit/usage/billing evidence;
- cancel/reconcile queued work safely;
- revoke/rotate provider credentials;
- return to in-app/first-party/unpaid behavior;
- export then delete provider data according to contract;
- verify no orphaned tenant data or entitlement remains.

Define the exact rollback switch and tested evidence.

---

## 13. Decision outcome

| Approver role | Decision | Date | Evidence reference | Conditions |
| --- | --- | --- | --- | --- |
| Product | `<approved/rejected/blocked>` | | | |
| Engineering | `<approved/rejected/blocked>` | | | |
| Security | `<approved/rejected/blocked>` | | | |
| Privacy/legal | `<approved/rejected/blocked>` | | | |
| Finance/commercial | `<approved/rejected/blocked/not applicable>` | | | |

Final statement:

```text
The selected option is <option/no selection>. Runtime activation is
<disabled/approved for sandbox/approved for controlled rollout>. Phase 22
retains final deployed-provider and launch approval.
```

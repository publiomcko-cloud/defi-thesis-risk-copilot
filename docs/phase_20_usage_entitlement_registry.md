# Phase 20 Usage-Unit and Entitlement Registry

Status: **Implemented Foundation — candidate registry; product, finance,
security, and privacy/legal approvals remain blocked**

This Phase 20A artifact defines vocabulary and proposed server-owned contracts.
It does not meter usage, grant an entitlement, change a quota, select a plan,
or create billing behavior.

---

## 1. Separate authorities

| Authority | Current/future source of truth | Decision point | Identifier namespace | Never used as |
| --- | --- | --- | --- | --- |
| Network rate limit | Phase 19 shared limiter or documented legacy rollback | Before bounded request/compute admission | Existing `compute.public`, `compute.authenticated`, `jobs.submit` | Product allowance, billable usage, or plan |
| Product quota | Existing atomic `usage_quotas` and resource-count checks | Before action/resource admission | Existing `analysis`, `simulation`, `options_analysis`, `market_data_fetch`, `resource_count:*` | Invoice evidence, analytics, or request-frequency limit |
| Billable usage | Future immutable `billable_usage_events` with reversal and reconciliation | At the exact approved server-owned meter point | Versioned `usage.*.v1` units | Mutable quota counter, analytics event, or browser quantity |
| Plan entitlement | Future immutable plan/entitlement versions and effective server-owned assignments | Before feature/hard-limit access | Versioned `feature.*` and `limit.*` keys | JWT/browser flag, unverified provider state, or analytics dimension |
| Product analytics | Future approved event registry | After purpose and decision gate | Candidate event taxonomy | Quota, billing, or authorization |

Current production behavior remains:

- `UserModel.plan` is database-owned;
- quota limits come from server settings;
- `UsageQuotaModel` enforces daily action and persistent resource-count limits;
- admin quota exemptions are server settings;
- no billable usage ledger or versioned entitlement catalog exists.

Phase 20F must shadow existing decisions before changing their authority.

---

## 2. Usage-unit contract

Every future usage unit must define:

- immutable key and version;
- human description and commercial interpretation;
- subject type derived server-side;
- exact meter point;
- quantity source and unit;
- source resource type/ID;
- idempotency key;
- reversal policy;
- reconciliation source;
- quota relationship;
- retention/export/deletion class;
- whether it is billable for a particular plan version.

A usage unit is not billable merely because it is registered. Each plan version
must explicitly map a unit to billing treatment after finance/legal approval.

### Candidate units

| Unit key | Quantity | Proposed meter point | Idempotency/source | Existing quota relationship | Default billing status | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| `usage.analysis.completed.v1` | One completed report | Successful report transaction/control-plane completion | One per report/result lineage | `analysis` quota is currently consumed at admission and remains separate | Non-billable | **Blocked** |
| `usage.simulation.completed.v1` | One successful simulation response | Successful deterministic simulation completion | One per server request/idempotency key | `simulation` quota consumed at admission | Non-billable | **Blocked** |
| `usage.options.completed.v1` | One successful options-analysis response | Successful deterministic options completion | One per server request/idempotency key | `options_analysis` quota consumed at admission | Non-billable | **Blocked** |
| `usage.market_data.fetch_completed.v1` | One normalized fetch completion | Successful adapter normalization/cache outcome under approved semantics | One per fetch operation/idempotency key | `market_data_fetch` quota consumed at admission | Non-billable | **Blocked** |
| `usage.schedule.run_completed.v1` | One terminal successful scheduled evaluation | Successful schedule-run result linked to one occurrence | Unique schedule ID plus scheduled-for occurrence | Future schedule quota/entitlement only | Non-billable | **Blocked** |
| `usage.notification.external_accepted.v1` | One provider-accepted external delivery | Verified provider acceptance, not intent/retry | Unique notification delivery, channel, and terminal provider reference | Future channel/delivery limits | Non-billable | **Blocked** |
| `usage.storage.byte_day.v1` | Byte-day of retained tenant document content | Approved daily snapshot/reconciliation, not upload request | Subject/date/storage inventory fingerprint | Future storage capacity entitlement | Non-billable | **Blocked** |
| `usage.organization.seat_day.v1` | Active/reserved seat-day under approved rule | Approved daily organization seat snapshot | Organization/date/member-state lineage | Future seat hard limit | Non-billable | **Blocked** |
| `usage.compute.second.v1` | Bounded trusted-worker execution second | Terminal attempt/provider-cost reconciliation | Job attempt plus provider ledger lineage | Job runtime/concurrency limits remain separate | Non-billable | **Blocked** |
| `usage.model.request_completed.v1` | One approved model-provider completion | Reconciled provider completion after Phase 21 policy | Job/attempt/provider request lineage | Future provider/model entitlement | Non-billable | **Blocked** |

Open unit decisions:

- whether billable analyses count completed reports, admitted requests, or
  another outcome;
- whether deterministic fallback reports count the same as enriched reports;
- failed/cancelled/partially completed treatment;
- provider cost pass-through versus included allowance;
- byte-day and seat-day snapshot timezone/rounding;
- notification acceptance versus confirmed delivery;
- reversal and credit behavior;
- legal retention and customer-visible reconciliation periods.

Until approved, every candidate unit is non-billable and no ledger exists.

---

## 3. Idempotency and reversal rules

Future usage rows must be immutable except for narrowly bounded reconciliation
state. Corrections use a linked reversal or superseding adjustment.

Required keys:

```text
unit_key
subject_type + subject_id
source_type + source_id
meter_version
idempotency_key
quantity
occurred_at
period_start + period_end
reversal_of_usage_event_id
reconciliation_status
```

Required invariants:

- unique `(unit_key, idempotency_key)`;
- quantity calculated server-side and greater than zero for original events;
- reversal quantity exactly references a prior event and cannot be reversed
  twice without an explicit adjustment chain;
- job retries, lease loss, stale completion, and recovery do not create a
  second original event;
- analytics event IDs are never usage idempotency keys;
- quota rows are not mutated by usage reconciliation;
- billing provider callbacks do not create usage without server product
  lineage;
- account/organization export returns understandable unit/quantity/period
  metadata, not internal idempotency/provider secrets.

---

## 4. Entitlement registry

Entitlements are server-owned, versioned keys. They define feature access or a
hard limit, not observed usage.

### Feature keys

| Key | Meaning | Candidate subject | Current fallback | Approval |
| --- | --- | --- | --- | --- |
| `feature.analysis` | Submit authenticated analysis | User, organization where supported | Existing authenticated analysis policy | **Blocked** |
| `feature.simulation` | Run strategy simulation | User | Existing route plus quota | **Blocked** |
| `feature.options_analysis` | Run options/volatility analysis | User | Existing route plus quota | **Blocked** |
| `feature.saved_theses` | Persist private theses | User | Existing authenticated policy/resource limit | **Blocked** |
| `feature.watchlists` | Persist/evaluate watchlists | User, future organization | Existing policy/resource limit | **Blocked** |
| `feature.scheduled_monitoring` | Create active durable schedules | User, organization | Disabled/not implemented | **Blocked** |
| `feature.notification.in_app` | Receive in-app notifications | User | Disabled/not implemented | **Blocked** |
| `feature.notification.email` | Enable approved email delivery | User | Disabled/not implemented | **Blocked** |
| `feature.notification.webhook` | Enable approved signed webhook delivery | User, organization | Disabled/not implemented | **Blocked** |
| `feature.notification.telegram` | Enable approved Telegram delivery | User | Disabled/not implemented | **Blocked** |
| `feature.organization` | Create/use commercial organization workspace | User/organization | Existing organization policy, no commercial plan control | **Blocked** |
| `feature.private_knowledge` | Use tenant durable knowledge when deployed | User, organization | Feature-gated Phase 18; JSON fallback | **Blocked** |
| `feature.model_provider` | Use an approved optional provider/model | User, organization | Current optional synthesis/provider flags | **Blocked** |
| `feature.billing_portal` | Open sandbox/production billing portal | Billing owner | Disabled/not implemented | **Blocked** |

### Hard-limit keys

| Key | Unit | Candidate period/scope | Current fallback | Approval |
| --- | --- | --- | --- | --- |
| `limit.analysis.count` | Admissions | Day, user/anonymous | Existing analysis quota settings | **Phase 20F shadow-only** |
| `limit.simulation.count` | Admissions | Day, user | Existing simulation quota | **Phase 20F shadow-only** |
| `limit.options.count` | Admissions | Day, user | Existing options quota | **Phase 20F shadow-only** |
| `limit.market_data.count` | Admissions | Day, user | Existing market-data quota | **Phase 20F shadow-only** |
| `limit.saved_thesis.count` | Active resources | User | Existing resource-count limit | **Phase 20F shadow-only** |
| `limit.watchlist.count` | Active resources | User | Existing resource-count limit | **Phase 20F shadow-only** |
| `limit.schedule.active_count` | Active resources | User | Existing active-schedule limit | **Phase 20F shadow-only** |
| `limit.organization.members_active` | Active plus reserved seats | Organization | No commercial seat limit | **Blocked** |
| `limit.knowledge.storage_bytes` | Retained bytes | User/organization | Existing storage feature gate/provider limits | **Blocked** |
| `limit.jobs.pending` | Pending jobs | User/organization | Existing Phase 17 capacity policy | **Blocked** |
| `limit.jobs.running` | Running jobs | User/organization | Existing Phase 17 capacity policy | **Blocked** |
| `limit.notification.external_per_day` | Accepted external deliveries | User/organization/channel | Disabled/not implemented | **Blocked** |
| `limit.retention.days` | Retention allowance | Resource class/plan | Existing per-domain retention settings | **Blocked** |
| `limit.model_provider.requests` | Completed provider requests | Period/user/organization | Existing provider/cost flags | **Blocked** |

The future entitlement resolver must not overwrite Phase 17 safety capacity,
provider cost ceilings, Phase 19 rate limits, storage safety flags, or legal
retention minimums. A commercial plan may be stricter, but it cannot weaken
those controls.

---

## 5. Plan and assignment rules

Proposed future invariants:

- activated `plan_versions` and `plan_entitlements` are immutable;
- assignments are server-created with effective start/end and source;
- overlapping assignments for one subject/type require deterministic priority
  and PostgreSQL constraints or serialized resolution;
- provider subscription state is normalized and reconciled before creating an
  assignment;
- browser/JWT/provider plan labels are display/input hints only;
- an organization entitlement does not silently grant access to a non-member;
- membership is checked separately from entitlement;
- anonymous demo policy remains server configuration and cannot be upgraded;
- admin exemptions are explicit, narrow, server-owned, and audited;
- unknown/missing/corrupt plan state fails to reviewed fallback limits, never
  unlimited access;
- rollback returns to existing `UserModel.plan` plus environment quota policy.

---

## 6. Export, deletion, and retention

Use existing lifecycle authorities:

- account export gains normalized current entitlement, assignment, usage, and
  reconciliation metadata;
- organization export is implemented in 20H through organization
  authorization;
- no export includes internal idempotency keys, provider secrets, fraud/risk
  controls, or complete callback payloads;
- account/organization deletion cancels future activity and removes or
  restricts subject links according to approved legal retention;
- usage/billing evidence retained for legal reasons is unavailable to normal
  product serving and uses an explicit legal-hold/restricted state;
- cleanup remains idempotent, dry-run capable, and recovery guarded.

---

## 7. Approval record

No plan, price, allowance, billable unit, entitlement, or commercial term is
approved by this registry.

| Decision | Required approvers | Status |
| --- | --- | --- |
| Unit semantics and meter points | Product, engineering, finance | **Blocked** |
| Billable versus included treatment and reversals | Finance/commercial, legal, product | **Blocked** |
| Entitlement keys, defaults, limits, and fallback | Product, security, engineering | **Blocked** |
| Organization seat/storage/retention semantics | Product, finance, privacy/legal | **Blocked** |
| Export/deletion/legal retention | Privacy/legal, finance, security | **Blocked** |
| Admin/internal/test exemptions | Security, finance, product | **Blocked** |

Phase 20F is not eligible until its applicable registry rows and fallback
semantics are approved.

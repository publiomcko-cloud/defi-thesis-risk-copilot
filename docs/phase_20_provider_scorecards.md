# Phase 20 Provider Scorecards

Status: **Implemented Foundation — alternatives instantiated; evidence scores
and selections remain blocked**

These scorecards prevent provider choice by convenience. No provider is
selected, approved, installed, configured, or scored as a winner in Phase 20A.
Every candidate is `not assessed` because current contracts, DPAs,
subprocessors, pricing, sandbox behavior, and security evidence have not been
reviewed by the required humans.

Use [`decisions/phase_20_provider_adr_template.md`](decisions/phase_20_provider_adr_template.md)
to complete one capability decision at a time.

---

## 1. Scoring method

Score each criterion from `0` to `5` only after attaching reviewed evidence:

| Score | Meaning |
| --- | --- |
| `0` | Fails requirement or no credible path |
| `1` | Major unresolved deficiency |
| `2` | Material gaps or costly mitigation |
| `3` | Meets minimum with documented conditions |
| `4` | Strong fit with minor conditions |
| `5` | Fully evidenced fit and tested exit/rollback |

Weighted total:

```text
sum(score * weight)
```

Maximum is `500`. A numeric total does not override a hard gate or human
approval.

| Criterion | Weight | Required evidence |
| --- | ---: | --- |
| Privacy/legal/data governance | 20 | Purpose/legal basis, DPA, subprocessors, location/transfers, retention, export/deletion, secondary-use terms |
| Security and tenant boundary | 20 | Secrets, RBAC, callbacks, signatures, SSRF, isolation, audit, incident process, SDK provenance |
| Reliability and failure behavior | 15 | SLA/status, idempotency, ordering, retry, recovery, limits, outage fallback |
| Lifecycle and portability | 15 | Data/config export, deletion, adapter boundary, termination, migration/exit exercise |
| Functional/accessibility fit | 10 | Required capability, API, accessibility, localization, admin/user controls |
| Sandbox and testability | 10 | Isolated sandbox, fakes, synthetic test support, deterministic callbacks, no live-cost requirement |
| Cost/commercial fit | 10 | Pricing, egress/overage/support costs, contract, tax/MoR where applicable, cost ceiling |

### Hard gates

Any `fail` or `pending` hard gate blocks selection:

- required human owners and approvals;
- approved purpose/legal basis and DPA where applicable;
- subprocessor/data-location review;
- export/deletion and retention support;
- server-only secret handling and emergency revocation;
- exact callback/outbound security;
- tenant isolation and no browser authority;
- sandbox/production separation;
- tested fail-closed behavior and rollback;
- cost ceiling and commercial/tax ownership where applicable;
- no conflict with Phase 19 gates, JSON fallback, or disabled real Vast.ai
  rentals.

`Defer/no provider` must always be scored as an alternative.

---

## 2. Product analytics scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| First-party PostgreSQL | Existing application processor/storage | Pending privacy, retention, access, scale, and deletion review | Not assessed | Withheld | No selection |
| PostHog Cloud | External processor | Pending DPA/subprocessors/location/SDK and lifecycle review | Not assessed | Withheld | No selection |
| PostHog self-hosted | Additional self-operated service | Pending operational/security/backup/cost review | Not assessed | Withheld | No selection |
| Plausible | External or self-hosted analytics | Pending event-model, DPA/lifecycle, and server-ingestion review | Not assessed | Withheld | No selection |
| Another reviewed processor | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| Defer optional analytics | No processor/collection | Passes data-minimization default; product trade-off unreviewed | Partial repository evidence | Withheld | Current fail-closed default |

Capability-specific evidence:

- bounded custom-event/metadata support;
- server-side ingestion without browser SDK requirement;
- consent/purpose enforcement;
- pseudonymous identifier control;
- per-user export/deletion;
- retention configuration;
- aggregation without raw user content;
- processor outage cannot fail the product action.

---

## 3. Consent-management scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| First-party preference UI and decision ledger | Application-owned | Pending legal/regional policy, accessibility, evidence, and lifecycle review | Not assessed | Withheld | No selection |
| Cookiebot | External CMP | Pending DPA/subprocessors/location, cookie blocking, export/deletion review | Not assessed | Withheld | No selection |
| OneTrust | External CMP | Pending DPA/subprocessors/location, integration, accessibility, cost review | Not assessed | Withheld | No selection |
| Another reviewed CMP | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| Defer optional analytics/cookies | No optional collection | Passes fail-closed default; no consent UI needed until purpose approved | Partial repository evidence | Withheld | Current fail-closed default |

Capability-specific evidence:

- policy version and immutable decision;
- grant, deny, withdrawal, re-consent, and regional behavior;
- cookie/script blocking before consent where required;
- accessible preference center;
- server-side evidence and account export/deletion;
- no reinterpretation of terms/privacy acceptance.

---

## 4. Transactional-email scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| Postmark | External email processor | Pending DPA, domain, callback, suppression, retention, sandbox, cost review | Not assessed | Withheld | No selection |
| Resend | External email processor | Pending DPA, domain, callback, suppression, retention, sandbox, cost review | Not assessed | Withheld | No selection |
| Amazon SES | Cloud email service | Pending account/region, deliverability, callback, operational, DPA, cost review | Not assessed | Withheld | No selection |
| Another reviewed service | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| In-app only/defer email | No Phase 20 email provider | Preserves in-app fallback; user/commercial needs unreviewed | Partial repository evidence | Withheld | Current Phase 20 default |

Capability-specific evidence:

- verified sending domain and destination;
- bounce/complaint/suppression/unsubscribe handling;
- signed callbacks;
- template/content classification;
- no private body by default;
- sandbox or sink testing;
- separation from Supabase Auth SMTP, which remains a Phase 22 identity gate.

---

## 5. Outbound-webhook scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| First-party Phase 17 worker adapter | Application-owned | Pending SSRF/DNS/signature/retry/monitoring/cost implementation review | Not assessed | Withheld | No selection |
| Svix | External delivery processor | Pending DPA, payload retention, endpoint verification, signing, export/exit, cost review | Not assessed | Withheld | No selection |
| Hookdeck | External delivery/operations processor | Pending role, DPA, payload retention, replay, export/exit, cost review | Not assessed | Withheld | No selection |
| Another reviewed service | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| Defer webhooks | No external webhook channel | Passes fail-closed default; customer need unreviewed | Partial repository evidence | Withheld | Current default |

Capability-specific evidence:

- endpoint ownership verification;
- HTTPS, DNS rebinding/private IP, redirect, timeout, response-size controls;
- versioned signature/timestamp/replay protection;
- idempotent retry/dead-letter;
- payload/content retention and tenant isolation;
- signing-key rotation and exit.

---

## 6. Messaging scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| Telegram Bot API | External messaging processor | Pending account-linking, privacy, regional-control, abuse-control and quota reviews | Not assessed | Withheld | No selection |
| Reviewed multi-channel provider | External processor | Pending exact vendor and full ADR | Not assessed | Withheld | No selection |
| Defer messaging | No messaging channel | Passes data-minimization/fail-closed default | Partial repository evidence | Withheld | Current default |

Capability-specific evidence:

- authenticated user-initiated destination linking;
- revocation and account deletion;
- bot credential rotation;
- minimal content and authenticated links;
- provider rate/abuse behavior;
- delivery evidence without storing chat content.

---

## 7. Billing scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| Stripe Billing | Payment processor platform | Pending markets, tax/MoR, DPA, lifecycle, webhook, sandbox, fees, exit review | Not assessed | Withheld | No selection |
| Paddle | Merchant-of-record/platform candidate | Pending markets, tax/MoR, DPA, lifecycle, webhook, sandbox, fees, exit review | Not assessed | Withheld | No selection |
| Lemon Squeezy | Merchant-of-record/platform candidate | Pending markets, tax/MoR, DPA, lifecycle, webhook, sandbox, fees, exit review | Not assessed | Withheld | No selection |
| Another reviewed provider | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| Remain unpaid | No billing provider/live payments | Passes no-payment default; commercial goal trade-off unreviewed | Partial repository evidence | Withheld | Current default |

Capability-specific evidence:

- supported legal entity/markets/currencies;
- processor versus merchant-of-record responsibilities;
- tax/VAT, invoices, refunds, disputes, trials, cancellation, grace;
- hosted checkout/portal and no card data in application;
- signature, receipt, idempotency, stale/reordered events, authoritative fetch;
- product/price export and migration;
- sandbox distinct from production;
- support/escalation and cost ceiling.

No live payment is eligible in Phase 20. Phase 20G is sandbox-only.

---

## 8. Status-page scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| Atlassian Statuspage | External status processor | Pending DPA/subscribers, API, access, retention, independence, cost review | Not assessed | Withheld | No selection |
| Better Stack/Better Uptime | External monitoring/status processor | Pending DPA/subscribers, incident API, access, retention, cost review | Not assessed | Withheld | No selection |
| Instatus | External status processor | Pending DPA/subscribers, API, access, retention, cost review | Not assessed | Withheld | No selection |
| First-party static status | Application/independent static host | Pending independence, operator workflow, availability, accessibility review | Not assessed | Withheld | No selection |
| Defer subscription integration | Public support/status copy only | Does not satisfy final status-process gate | Partial evidence | Withheld | Interim only |

Capability-specific evidence:

- independence from primary application failure;
- component/incident model and operator authorization;
- subscriber privacy/consent;
- accessible public page and custom domain;
- incident API/fallback;
- retention/export/deletion and cost.

---

## 9. Customer-support scorecard

| Alternative | Model | Hard gates | Evidence completeness | Weighted score | Decision |
| --- | --- | --- | --- | --- | --- |
| First-party bounded intake | Application-owned | Pending workflow, privacy, staffing, retention, abuse, export/deletion review | Not assessed | Withheld | No selection |
| Help Scout | External support processor | Pending DPA, roles, email, export/deletion, audit, SLA, cost review | Not assessed | Withheld | No selection |
| Zendesk | External support processor | Pending DPA, roles, export/deletion, audit, attachments, cost/exit review | Not assessed | Withheld | No selection |
| Freshdesk | External support processor | Pending DPA, roles, export/deletion, audit, attachments, cost/exit review | Not assessed | Withheld | No selection |
| Another reviewed system | Undetermined | Pending full ADR | Not assessed | Withheld | No selection |
| Defer external support provider | Static contact/help only | Does not satisfy final request-tracking gate | Partial evidence | Withheld | Interim only |

Capability-specific evidence:

- private requester/tenant isolation;
- public-safe anti-enumeration intake;
- role/audit and no support impersonation;
- bounded text, no automatic LLM/analytics/log forwarding;
- attachment malware controls before attachments exist;
- privacy-request orchestration with existing export/deletion authority;
- export/deletion, retention, SLA/escalation, and exit.

---

## 10. Approval record

No capability has an approved score or provider.

| Capability | Decision owner | Required reviewers | Status | Next action |
| --- | --- | --- | --- | --- |
| Analytics | Product | Security, privacy/legal, engineering | **Blocked** | Approve purpose first, then collect current provider evidence |
| Consent management | Privacy/product | Security, privacy/legal, accessibility/engineering | **Blocked** | Decide whether optional analytics exists and what regions apply |
| Email | Product/operations | Security, privacy/legal, operations | **Blocked** | Approve notification classes and separate Auth SMTP boundary |
| Webhooks | Product/engineering | Security, privacy/legal, operations | **Blocked** | Approve external content and Phase 19 prerequisites |
| Messaging | Product | Security, privacy/legal, operations | **Blocked** | Decide whether channel is needed |
| Billing | Finance/commercial | Product, engineering, security, privacy/legal/tax | **Blocked** | Define entity/markets/tax/refund/plan semantics |
| Status | Operations | Security, privacy/legal, product | **Blocked** | Define status ownership and Phase 19 alert relationship |
| Support | Support/product | Security, privacy/legal, operations | **Blocked** | Define staffing, SLAs, request types, and retention |

Scores may be entered only in capability-specific ADR copies after evidence is
reviewed. The scorecard and an ADR together do not authorize production;
focused implementation, sandbox validation, rollout approval, and Phase 22
launch evidence still apply.

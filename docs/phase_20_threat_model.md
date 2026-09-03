# Phase 20 Threat Model

Status: **Phase 20 Complete — Portfolio Profile.** Phase 20B controls are
complete; production privacy/legal activation approval remains blocked.

This threat model covers the planned Phase 20 product analytics, schedules,
notifications, metering, entitlements, billing sandbox, organization
commercial workflows, and customer operations. Phase 20B adds a default-off,
authenticated, first-party PostgreSQL analytics path without a provider,
credential, browser SDK, payment, notification, or production activation.

Authority:

- [`future_phase_contracts.md`](future_phase_contracts.md), Phase 20;
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md);
- [`architecture.md`](architecture.md);
- [`phase_19_threat_model.md`](phase_19_threat_model.md);
- [`phase_20_event_privacy_matrix.md`](phase_20_event_privacy_matrix.md);
- [`phase_20_data_model_review.md`](phase_20_data_model_review.md).

The Phase 15–19 threat boundaries remain in force. In particular, actor and
tenant scope is server-derived, heavy work uses Phase 17 durable jobs, JSON RAG
remains the production fallback, `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`,
`VAST_DRY_RUN=true`, and `VAST_REAL_RENTALS_ENABLED=false`.

---

## 1. Assets and trust boundaries

Protected assets:

- authenticated identity, anonymous-session state, organization membership,
  platform role, and server-owned plan state;
- consent and preference evidence, including policy version and withdrawal;
- analytics taxonomy, bounded metadata, pseudonymous identifiers, and
  retention state;
- schedule definitions, due-run claims, job lineage, and monitoring results;
- notification preferences, destinations, verification state, signatures, and
  delivery records;
- product quota counters, billable usage evidence, plan versions,
  entitlements, and assignments;
- billing customer/subscription mappings, verified receipts, normalized state,
  and reconciliation evidence;
- organization invitations, seats, ownership, billing contacts, exports, and
  deletion state;
- support, feedback, abuse, privacy-request, status, and audit records;
- provider credentials, callback secrets, signing keys, and operational
  evidence.

Trust boundaries:

```text
Browser
  -> exact Next.js BFF route
  -> FastAPI authentication and server-derived actor
  -> domain authorization and purpose/entitlement gate
  -> PostgreSQL

Operator scheduler
  -> due-row claim
  -> Phase 17 durable job
  -> scoped trusted worker

External provider
  -> exact callback endpoint
  -> measured body and signature/replay checks
  -> immutable receipt
  -> normalized reconciliation

Application
  -> approved outbound adapter
  -> verified destination
  -> bounded signed/minimal payload
```

No browser, JWT plan claim, provider event, destination, resource ID, or
organization ID establishes authorization or entitlement by itself.

---

## 2. Threat register

| ID | Boundary | Threat and impact | Required control before runtime | Phase 20A evidence | Residual owner/gate |
| --- | --- | --- | --- | --- | --- |
| `T20-01` | Analytics event entry | A browser forges identity, organization, event name, quantity, or plan metadata; events become a tenant side channel or billing input | Code-owned registry; server-owned trigger and scope; per-event metadata allowlist; event payload never authorizes access or billing | Phase 20B registry, server emitters and negative tests | New review for any taxonomy expansion |
| `T20-02` | Event metadata | Strategy text, protocol/source content, report identifiers, email, IP, URL, user agent, tokens, or free-form values leak into analytics | Denylist plus bounded typed allowlists; no arbitrary browser metadata; redaction and negative tests | Exact enum registry, safe export and prohibited-field tests | Qualified review before production activation |
| `T20-03` | Pseudonymization | Stable anonymous or user identifiers enable re-identification, cross-purpose joining, or irreversible pepper rotation | Anonymous analytics absent; relational owner used only for consent/lifecycle; source boundary one-way hashed and not exported | Authenticated-only schema/API and export tests | New design required before any anonymous path |
| `T20-04` | Consent evidence | Mutable checkbox state, stale policy version, duplicate concurrent decisions, or missing withdrawal makes consent unverifiable | Immutable decision ledger plus current projection; idempotency; policy and purpose version; previous-decision linkage; audit; export and deletion hooks | Migration `0023`, row locks, re-consent and PostgreSQL concurrency tests | Qualified review before production activation |
| `T20-05` | Legal-document consent | A new analytics model replaces or corrupts Phase 16 terms/privacy acceptance records | Keep `consent_records` authoritative for terms/privacy; Phase 20 records only granular preferences not represented there; no duplicate account lifecycle | Data-model review | Architecture and privacy/legal approval |
| `T20-06` | Retention/export/deletion | New rows are absent from export, survive deletion, are deleted despite legal hold, or create a second lifecycle authority | Extend existing account lifecycle through registered projections/hooks; fixed retention; dry-run cleanup; Phase 19 recovery guard | Safe export, immediate disposal, 30-day evidence and cleanup tests | Legal-hold policy remains a later qualified decision |
| `T20-07` | Analytics versus telemetry | Analytics opt-out suppresses security/reliability evidence, or operational telemetry becomes unconsented product tracking | Separate stores, purposes, access, retention, and emitters; analytics preference affects only optional analytics | Separate service/table and non-critical-emitter tests | Continue permanent regression coverage |
| `T20-08` | Durable scheduler | Browser/web-process timers lose or duplicate work; DST, missed runs, or concurrent claims create unexpected cost | Operator scheduler; PostgreSQL one-winner claim; unique scheduled occurrence; Phase 17 job idempotency; cadence, quota, cost, pause, cancellation, recovery controls | Execution plan and proposed `0024` review | 20C implementation and PostgreSQL evidence |
| `T20-09` | Schedule authorization | Removed user/member or disabled organization continues to schedule or execute tenant work | Server-derived target; authorization at create, dispatch, and execution; authorization revocation follows Phase 17 active-job rules | Threat and data-model reviews | 20C implementation evidence |
| `T20-10` | Notification preferences | Required security/billing notices are incorrectly optional, or marketing/product notices bypass consent and unsubscribe | Versioned category registry; legal-delivery class; explicit channel preference; verified destination; unsubscribe/revocation; purpose separation | Notification classification | Product and privacy/legal approval |
| `T20-11` | Notification content | Private report/source/support content leaks through email, webhook, Telegram, logs, or provider dashboards | Minimal metadata or authenticated links; content class restrictions; no private body by default; bounded templates and provider retention review | Notification classification and provider ADR template | Security/privacy approval before 20E |
| `T20-12` | Outbound webhook | SSRF, DNS rebinding, redirects, response amplification, replay, or tenant destination collision | HTTPS policy; verification; DNS/IP checks at verification and send; private/reserved IP denial; no redirects; bounded reads/timeouts; versioned signatures; per-destination limits | Provider ADR template and notification classification | Phase 19 provider prerequisites and 20E tests |
| `T20-13` | External delivery | Provider outage or retry creates duplicates, alert storms, cost growth, or silent loss | Phase 17 job idempotency; provider idempotency key; bounded retries/backoff; dead letter; digest/rate limits; in-app fallback; aggregate monitoring | Proposed `0025` review | Provider ADR and 20E sandbox evidence |
| `T20-14` | Entitlement resolution | Browser/JWT/provider payload grants a plan, hidden admin exemption bypasses audit, or stale assignment persists | Immutable server-owned plan versions; effective assignments; database-owned actor state; explicit audited exemption; verified reconciliation only | Usage/entitlement registry | Product/security/finance approval and 20F tests |
| `T20-15` | Quota and usage | Network limits, product quota counters, billable usage, and entitlements are conflated, enabling denial, overage, or billing errors | Separate services/tables/identifiers; documented meter point; immutable usage with reversal; atomic quota admission; no analytics-derived billing | Usage/entitlement registry | Product/finance approval and 20F reconciliation |
| `T20-16` | Durable job metering | Job retry, lease expiry, cancellation, or duplicate completion double-counts usage | Meter only documented server-owned outcome; unique source lineage/idempotency; reversal/supersession; reconciliation against terminal job/report state | Usage-unit registry | 20F PostgreSQL and worker-loss evidence |
| `T20-17` | Billing callback | Forged, replayed, stale, reordered, or concurrent callbacks regress subscription/entitlement state | Exact callback; measured body; signature before processing; persist receipt first; unique provider event; authoritative state fetch when ordering uncertain | Provider ADR template and proposed `0027` review | Billing ADR, finance/legal approval, 20G sandbox |
| `T20-18` | Billing data | Card data, full provider payloads, tax data, portal URLs, or secrets enter application rows, logs, export, or browser storage | Hosted provider handling; normalized allowlist only; no payment details/full payload; short-lived authorized portal URL; strict redaction and retention | Data-model review | Billing provider/security/privacy approval |
| `T20-19` | Organization commercial state | Seat/invitation race, token theft, final-owner loss, billing-owner confusion, or stale membership grants access | Hashed one-time expiring invite; atomic seats; existing Phase 16 membership/final-owner locks; explicit billing contact role; audit; server-derived scope | Proposed `0028` review | 20H PostgreSQL and authorization evidence |
| `T20-20` | Support/privacy intake | Free text causes XSS, log/analytics leakage, prompt injection, account enumeration, or excessive sensitive-data collection | Bounded escaped text; no automatic LLM/analytics/log forwarding; generic public response; recent-auth privacy operations; attachment scanning before any future attachment | Proposed `0029` review | Support/status ADR where applicable; 20I tests |
| `T20-21` | Administration | Platform admin, support, finance, or organization roles overreach; support impersonation hides actions | Least privilege; no support impersonation; explicit commercial permissions; MFA where configured; immutable audit; no private organization bypass | Threat model and ADR template | Security/product approval and role tests |
| `T20-22` | Provider/supply chain | SDK or processor collects undeclared data, changes subprocessors, exposes secrets, becomes unavailable, or blocks exit | ADR with data flow/DPA/subprocessors/location/SDK review; server-side adapter preference; sandbox isolation; secret owner/rotation; export and exit plan; lockfile/scanner controls | ADR template and scorecards | Human approvals plus Phase 19 external gates |
| `T20-23` | Public demo | Analytics, entitlements, schedules, or commercial UI regress bounded anonymous demo or expose private state | Anonymous analytics disabled; existing public limits retained; no authenticated resource path made public; feature flags disabled by default in later slices | Execution plan and current-state boundary | Permanent regression suite |
| `T20-24` | Knowledge and model paths | Commercial activation broadens tenant RAG scope, removes JSON fallback, or enables real GPU rentals | No Phase 20 dependency changes retrieval/provider flags; server-derived tenant filters and JSON fallback remain; real Vast rentals fail closed | Phase 20A scope audit | Phase 22 controlled validation |

---

## 3. Privacy misuse cases

Phase 20 implementation must reject:

- event fields or dimension maps not declared by the exact event schema;
- raw report, thesis, strategy, prompt, source, support, or notification body in
  analytics;
- raw email, IP, access/refresh token, cookie, auth subject, anonymous-session
  token, provider customer ID, storage key, or signed URL in analytics;
- client-provided actor, organization, plan, entitlement, usage quantity, or
  billing status as authoritative;
- joining optional analytics to security, audit, billing, or support data for a
  new purpose without a new approved purpose and policy version;
- keeping optional events after their deletion/retention state permits removal;
- treating a terms/privacy acceptance as granular analytics consent;
- treating analytics withdrawal as withdrawal of required terms, security,
  audit, billing, or operational processing;
- organization administrators granting personal analytics consent for members;
- support agents impersonating users.

---

## 4. Required security test themes

Later subphases must add:

- event-name, field, size, type, and purpose allowlist negatives;
- actor and organization spoofing negatives;
- consent grant, withdrawal, re-consent, policy transition, and concurrency;
- anonymous analytics disabled/default behavior;
- export, deletion, retention, legal-hold, and dry-run cleanup integration;
- schedule claim, membership revocation, queue saturation, and worker-loss
  tests;
- notification content classification, destination verification, SSRF,
  signature, replay, retry, dead-letter, digest, and unsubscribe tests;
- entitlement forgery, effective-date, quota parity, meter idempotency,
  reversal, retry, and reconciliation tests;
- billing signature, persisted receipt, duplicate, stale, reordered,
  concurrent, authoritative-fetch, portal authorization, and redaction tests;
- invitation/seat/final-owner/billing-contact contention and authorization;
- support free-text, enumeration, body bounds, redaction, and no-LLM forwarding;
- regression for public demo, tenant isolation, JSON fallback, worker control
  plane, and disabled real Vast.ai rentals.

---

## 5. Human approval blockers

No approval is inferred from this document.

| Decision | Required approvers | Status |
| --- | --- | --- |
| Phase 20B purpose, explicit opt-in, anonymous policy, retention, export, and deletion for implementation/private validation | Project owner for product, engineering and project-level security | **Approved in `decisions/phase_20b_analytics_approval.md`** |
| Phase 20B production jurisdictions, legal basis, notice/copy, consent and retention | Qualified privacy/legal | **Blocked** |
| Consent evidence design and relationship to `consent_records` | Project owner/security/architecture | **Approved and implemented for 20B** |
| Usage units, meter points, entitlements, quota semantics, reversals, and commercial meaning | Product, finance/commercial, engineering, security | **Blocked** |
| Notification categories, required-versus-optional treatment, external content, destinations, and retention | Product, privacy/legal, security | **Blocked** |
| Provider selection, DPA/subprocessors/location, sandbox, secrets, cost, and exit plan | Capability owner, security, privacy/legal, finance where applicable | **Blocked** |
| Retention periods, legal holds, billing evidence, tax/refund/trial/grace rules, and public copy | Privacy/legal and finance/commercial | **Blocked** |

Review this model before each later Phase 20 schema/runtime change and before
each provider ADR is accepted. Store no credentials, customer content, or
private operational evidence in this file.

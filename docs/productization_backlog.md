# Productization Backlog

Status: **Deferred from the completed Phase 20 portfolio profile; no item
becomes complete through the 20J closeout**

This document preserves the work intentionally deferred while the repository is developed as a portfolio anchor.

Nothing here is considered complete merely because the portfolio architecture exposes an interface, fake adapter, synthetic state machine, disabled feature flag, or local test path.

The goal is to make future productization incremental and evidence-driven rather than requiring an architectural rewrite.

---

## 1. Productization trigger

Re-enter product mode only after deciding to operate the project as a real customer-facing service with ongoing ownership for providers, legal/privacy obligations, support, security operations, payments, and production incidents.

At that point:

1. record the target legal entity and operating jurisdictions;
2. choose the intended commercial model and target users;
3. reopen the relevant provider ADRs with current evidence;
4. obtain qualified legal/privacy/tax/commercial review;
5. complete Phase 19 external operational evidence;
6. validate provider sandboxes and controlled deployment;
7. update terms, privacy, retention, support, billing and public claims;
8. complete the product-launch form of Phase 22 before enabling paid or external-provider features.

---

## 2. Production analytics activation

The Phase 20B first-party analytics implementation may remain complete in the portfolio while production collection stays disabled.

Before activation:

- qualified privacy/legal review by intended jurisdiction;
- approved privacy notice and consent wording;
- confirmation of legal basis and explicit opt-in policy;
- retention and post-deletion evidence review;
- deployed migration and rollback evidence;
- controlled test-account validation;
- monitoring and incident ownership;
- explicit activation of a new approved policy version when required;
- fresh affirmative consent for that approved version;
- Phase 22 launch approval.

Until then:

`PRODUCT_ANALYTICS_ENABLED=false`

---

## 3. External notification providers

Portfolio completion does not require a real email, webhook-delivery, Telegram, or messaging provider.

Before a real channel is activated:

- approve its user/product purpose;
- complete a current provider ADR;
- review DPA, subprocessors, data location, retention and exit terms;
- approve content classification and destination-verification behavior;
- verify domain/destination ownership where applicable;
- configure server/worker-only secrets and rotation;
- test bounce/suppression/revocation or equivalent lifecycle behavior;
- test retries, dead letter, idempotency and outage fallback;
- satisfy relevant Phase 19 outbound, monitoring and secret-management gates;
- run sandbox evidence before customer delivery.

Candidate provider research remains documented in `phase_20_provider_scorecards.md` but no old score may be treated as current without refreshing provider evidence.

Telegram remains deferred unless a concrete user need justifies the privacy, linking, abuse and operational complexity.

---

## 4. Live billing and paid plans

Real payment handling is outside the portfolio-required roadmap.

Before live billing:

- decide legal entity and supported countries;
- decide processor versus merchant-of-record model;
- define currencies, taxes/VAT, invoices and customer tax responsibilities;
- define real plan names, prices and allowances;
- define trials, cancellation, grace, refunds, disputes and support ownership;
- complete a current billing ADR;
- select and contract the provider;
- configure isolated sandbox and production credentials;
- map provider products/prices to immutable server-owned plan versions;
- validate signature verification and immutable receipt persistence;
- prove stale, duplicate, reordered and concurrent callbacks cannot regress normalized subscription state;
- fetch authoritative provider state when event ordering is uncertain;
- derive entitlements only from reconciled normalized state;
- validate checkout/portal authorization and return-origin restrictions;
- complete tax/legal/privacy review and product-launch approval.

Potential providers currently documented for future evaluation include Stripe Billing, Paddle, Lemon Squeezy and a deliberate no-provider alternative.

No portfolio usage event creates a payment obligation.

---

## 5. Commercial organization behavior

The portfolio may demonstrate seats, invitations, ownership and versioned entitlements without commercial subscriptions.

Before paid organizations:

- define real seat pricing and plan rules;
- decide whether pending invitations are billable/reserved commercially;
- define upgrades, downgrades, proration and over-limit behavior;
- define billing-owner responsibilities;
- map reconciled subscription state to organization assignments;
- define tax/invoice contact handling;
- validate organization export/deletion with retained billing evidence;
- review customer-visible commercial copy.

Synthetic portfolio seat limits must not be silently converted into real paid terms.

---

## 6. Support and status operations

The portfolio may use first-party bounded request tracking and a simple public-safe status process.

Before operating as a customer service:

- assign actual support ownership and escalation coverage;
- define supported contact channels and response commitments;
- obtain legal/privacy review of request retention;
- define security/abuse escalation procedures;
- decide whether attachments are accepted and add malware/content controls first;
- decide whether an external helpdesk is justified;
- complete provider ADR/DPA/role/export/deletion review for any external support system;
- operate an independent status process with named incident ownership;
- review subscriber privacy before collecting status-subscription contacts.

Operational response targets used in portfolio tests are engineering examples, not contractual SLAs.

---

## 7. Production private knowledge and RAG

The portfolio preserves Phase 18 private-storage and pgvector architecture behind feature gates.

Before production cutover:

- complete private bucket/storage policy review;
- validate RLS/tenant access using controlled deployed accounts;
- validate worker-only storage access;
- complete backup/restore evidence for private objects and vectors;
- validate deletion/tombstone propagation and stale-cache prevention;
- run retrieval/citation evaluation on deployed infrastructure;
- define storage retention and legal policy;
- perform controlled cutover with JSON RAG fallback and rollback evidence;
- obtain Phase 22 approval.

`KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` remains the safe default until those gates pass.

---

## 8. Real GPU/provider execution

The repository may continue to demonstrate Vast.ai/provider orchestration in dry-run or synthetic form.

Before real automated rentals or paid inference:

- approve provider/account ownership;
- confirm current pricing and cost ceilings;
- validate image/model provenance;
- test secret storage and rotation;
- validate reconciliation after uncertain provider state;
- verify auto-destroy and orphan cleanup;
- monitor spend and runaway-cost alerts;
- test provider outage/failure paths;
- record controlled deployment evidence.

Keep:

`VAST_DRY_RUN=true`

`VAST_REAL_RENTALS_ENABLED=false`

until explicitly productized.

---

## 9. Phase 19 external operational gates

Repository foundations do not replace deployed operational evidence.

Before a commercial launch, complete the outstanding Phase 19 evidence for:

- centralized logs, errors and traces;
- real alert delivery and escalation ownership;
- provider/storage restore drills;
- production secret rotation;
- protected-branch and required-check enforcement;
- controlled deployment evidence;
- production backup/restore validation;
- incident communication ownership;
- deployed synthetic checks and queue/worker monitoring.

These remain launch gates even when the corresponding code foundation is implemented.

---

## 10. Qualified legal, privacy and commercial review

Before real paid/public product launch, obtain qualified review of:

- terms of service;
- privacy policy;
- analytics/cookie consent;
- subprocessors and data transfers;
- retention/deletion/legal hold;
- acceptable use;
- financial-research disclaimers;
- jurisdiction/dispute terms;
- billing/refund/cancellation terms;
- tax/VAT responsibilities;
- data-processing agreements where applicable;
- public claims about capabilities, security and availability.

Internal architecture documents and project-owner decisions are not legal certification.

---

## 11. Product-mode Phase 22

The active portfolio profile may use Phase 22 to validate the public portfolio deployment.

A future commercial launch must run an expanded product-mode Phase 22 that includes:

- production provider configuration;
- deployed identity and email flows;
- two-user/organization isolation with disposable real accounts;
- production environment/cookie/origin validation;
- migrations and rollback/backup evidence;
- provider sandbox-to-production handoff evidence;
- legal/privacy/commercial sign-off;
- support/status ownership;
- release-owner approval;
- explicit enablement of paid or external capabilities.

No deferred productization item becomes complete simply because the portfolio release is complete.

---

## 12. Architectural preservation rules

Future productization should reuse the portfolio architecture instead of replacing it.

Preserve these interfaces and invariants:

- provider-neutral adapters;
- server-owned authorization and tenant scope;
- immutable/versioned plan and usage authorities;
- reconciliation before entitlement changes;
- strict callback and outbound security;
- Phase 16 export/deletion authority;
- Phase 17 durable jobs and recovery;
- Phase 18 JSON fallback;
- Phase 19 security boundaries;
- deterministic risk values as authoritative;
- disabled-by-default activation flags;
- migration and rollback evidence.

If a future provider requires weakening one of these controls, the provider or design must be reconsidered rather than silently bypassing the architecture.

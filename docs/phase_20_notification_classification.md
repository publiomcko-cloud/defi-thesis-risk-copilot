# Phase 20 Notification Category and Destination Classification

Status: **Implemented Foundation — proposed categories and fail-closed channel
rules; human approvals remain blocked**

This Phase 20A artifact classifies future notification intent, content, user
control, and destinations. It does not create a preference, notification,
destination, send, provider integration, or environment variable.

---

## 1. Permanent rules

- A notification never authorizes access to its linked resource.
- Tenant and organization scope is re-derived when creating and reading it.
- Every channel requires an explicit category/channel rule.
- External destinations are disabled until verified.
- External content contains minimal metadata or an authenticated link, not
  private report, source, thesis, strategy, document, support, or billing body.
- Quiet hours, digest, and user opt-out do not suppress an approved mandatory
  security/legal notice; human reviewers must classify those notices.
- Auth-provider verification/recovery/MFA email remains a separate Phase
  16/22 identity channel, not silently migrated into Phase 20 email.
- External delivery retries through Phase 17 jobs and uses idempotency,
  bounded backoff, dead letter, rate limits, and aggregate monitoring.
- No notification contains trading instructions or executes an action.

---

## 2. Content classes

| Class | Allowed content | External channels | Prohibited content |
| --- | --- | --- | --- |
| `N0_PUBLIC` | Public status component and incident title already approved for publication | Status page, in-app public surface | Tenant state, identity, internal incident/evidence details |
| `N1_ACCOUNT_MINIMAL` | Generic account action type, time bucket, support link | Verified email, in-app | Tokens/codes except through existing auth provider flow, IP/device details, raw audit data |
| `N2_RESOURCE_LINK` | Generic result/alert type plus authenticated application link | In-app; approved verified email/webhook/Telegram only | Resource body/title if sensitive, report rating/protocol, strategy/source content, signed URL |
| `N3_COMMERCIAL_MINIMAL` | Normalized plan/subscription state and authenticated billing link | In-app and verified billing email after approval | Card/payment details, invoice body, provider payload, tax identifiers, portal URL in durable storage |
| `N4_SUPPORT_PRIVATE` | Support/privacy request status visible in authenticated application | In-app only by default | Request description, attachments, identity evidence, internal notes in external notification |
| `N5_RESTRICTED` | Internal-only security, fraud, legal hold, provider reconciliation, or incident evidence | None | Any external/user notification payload |

---

## 3. Category registry

All categories are candidates. `Required` means a human decision is needed; it
does not claim legal necessity.

| Category key | Examples | Content class | Default/channel proposal | Quiet hours/digest | Preference/legal status | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| `account.security` | Password/MFA/account-security change notice | `N1_ACCOUNT_MINIMAL` | In-app; verified email only through approved identity/transactional boundary | No digest; quiet-hour bypass only if approved | Candidate mandatory security notice; separate from auth codes | **Blocked**: security, privacy/legal |
| `account.lifecycle` | Export ready, deletion requested/completed, privacy request status | `N1_ACCOUNT_MINIMAL` or `N4_SUPPORT_PRIVATE` | In-app; verified email candidate | No digest for deletion/privacy deadlines | Required/optional treatment unresolved | **Blocked** |
| `job.status` | Durable analysis/ingestion completed, failed, cancelled, dead-lettered | `N2_RESOURCE_LINK` | In-app default off until user preference; external candidate | Quiet hours and digest allowed except approved critical failures | Optional product notification | **Blocked**: product |
| `monitoring.risk_alert` | Existing watchlist or scheduled evaluation triggers | `N2_RESOURCE_LINK` | In-app; approved external channels after verification | User severity filter, quiet hours, digest, rate limits | Explicit preference required | **Blocked**: product, privacy/legal |
| `schedule.status` | Schedule paused, missed, quota denied, disabled target | `N2_RESOURCE_LINK` | In-app; external candidate | Digest/rate limit allowed | Explicit preference required | **Blocked** |
| `knowledge.status` | Upload/ingestion/embedding completed or failed | `N2_RESOURCE_LINK` | In-app; verified email candidate | Digest/rate limit allowed | Explicit preference required | **Blocked** |
| `organization.membership` | Invitation, role change, removal, ownership transfer | `N1_ACCOUNT_MINIMAL` or `N2_RESOURCE_LINK` | In-app; verified invitation email only after approved channel | Invitation expiry may bypass digest; quiet-hour behavior unresolved | Some notices may be required; invitation consent/anti-abuse review needed | **Blocked** |
| `organization.commercial` | Seat threshold, billing contact, plan state | `N3_COMMERCIAL_MINIMAL` | Billing owner/contact in-app; verified email candidate | Digest for thresholds; critical state rules unresolved | Role and legal notice rules unresolved | **Blocked** |
| `billing.subscription` | Trial, active, past due, grace, cancel, refund status | `N3_COMMERCIAL_MINIMAL` | In-app; verified billing email after 20G approval | Required notice/digest rules provider/jurisdiction-specific | Billing/legal classification unresolved | **Blocked**: finance/legal |
| `support.request` | Support/feedback/abuse case status | `N4_SUPPORT_PRIVATE` | In-app; generic verified email candidate | Quiet hours allowed except approved response deadline | Explicit contact preference; privacy request rules separate | **Blocked** |
| `system.status` | Public incident/maintenance | `N0_PUBLIC` | Public status; optional in-app/subscription | Digest and severity filters | Subscriber privacy/consent unresolved | **Blocked** |
| `product.update` | Release note or optional education | `N0_PUBLIC` or `N1_ACCOUNT_MINIMAL` | Off by default; explicit opt-in for external | Quiet hours/digest/unsubscribe required | Marketing/electronic communication review required | **Blocked**: privacy/legal/product |

No category is enabled in Phase 20A.

---

## 4. Destination classification

| Destination type | Verification | Secret/identifier storage | Delivery boundary | Rollback | Eligibility |
| --- | --- | --- | --- | --- | --- |
| `in_app` | Existing authenticated actor and server-derived ownership | Notification owner/org only; no destination secret | Application database and authorized UI | Disable intent creation; preserve readable rows through retention | 20D after category approval |
| `verified_email` | Existing verified account email or destination challenge; identity email remains separate | Normalized address reference or user link as approved; no provider credential | Server/worker adapter; minimal template; suppression/unsubscribe | Disable channel, revoke provider credential, retain in-app | 20E after email ADR |
| `https_webhook` | Challenge-response or signed verification plus operator confirmation | Encrypted/secret-managed signing material; bounded normalized URL; no browser return of secret | Phase 17 worker with SSRF/DNS/replay/redirect controls | Disable destination/submission, revoke key, retain in-app | 20E after webhook ADR and Phase 19 gates |
| `telegram_chat` | Bot-mediated one-time linking initiated by authenticated user | Opaque chat reference; bot credential server-only; no username as authority | Phase 17 worker; minimal content; provider limits | Revoke link/credential, disable channel, retain in-app | Optional 20E after messaging ADR |
| `status_subscription` | Provider-defined verified subscriber process | Prefer provider-owned subscriber data; application stores minimal reference only if needed | Independent status provider or static status process | Publish public status fallback; remove integration | 20I after status ADR |
| `support_contact` | Existing authenticated account or generic public-safe intake | Contact preference only; no destination secret in notification table | Support domain, not general notification destination | First-party request status fallback | 20I after support decision |

Destination rules:

- destination ownership never grants resource access;
- verification expires and is revoked on account/organization deletion,
  destination change, compromise, or user request;
- one destination cannot be silently shared across tenants;
- organization webhook/email administration requires an approved role and
  active membership;
- destination values, challenges, signing secrets, bot credentials, and
  provider response bodies are excluded from browser logs, analytics, audit
  metadata, and account exports;
- export may include channel type, verified/revoked state, safe masked label,
  and timestamps only;
- external callback and outbound provider configuration requires an approved
  ADR.

---

## 5. Preference dimensions

The planned preference key is:

```text
subject + category + channel
```

Candidate preference fields:

- enabled;
- minimum severity;
- timezone;
- quiet-hours start/end;
- digest mode/frequency;
- verified destination reference;
- policy/template version;
- effective timestamp;
- latest immutable decision/audit reference.

Required invariants:

- category and channel come from code-owned registries;
- user/organization subject is server-derived;
- organization preferences do not override individual security/privacy rights;
- channel enablement requires destination verification and entitlement when
  plan-controlled;
- entitlement cannot override an opt-out;
- opt-in cannot override an unavailable/unsafe channel;
- quiet hours use validated IANA timezones;
- rate limits and digest are separate from product quotas and billable usage;
- preference updates are idempotent and auditable;
- removal/downgrade immediately affects queued work according to Phase 17
  authorization-revocation rules.

---

## 6. Delivery lifecycle

```text
approved domain outcome
  -> idempotent notification intent
  -> tenant authorization
  -> category/severity rule
  -> user preference
  -> destination verification
  -> entitlement when applicable
  -> quiet-hours/digest/rate gate
  -> in-app record
  -> optional Phase 17 external-delivery job
  -> accepted/failed/dead-lettered safe status
```

Cancellation/deletion:

- account or organization deletion cancels pending deliveries, revokes
  destinations, and delegates data disposition to the existing lifecycle;
- membership removal prevents new organization delivery and requests
  cancellation for active work;
- disabling a channel stops new jobs without deleting required audit/delivery
  evidence;
- retries never broaden content or destination scope;
- provider uncertainty remains a safe normalized status, not success.

---

## 7. Approval record

No category, channel, template, destination, retention period, or mandatory
notice classification is approved.

| Decision | Required approvers | Status |
| --- | --- | --- |
| Category purpose and required/optional treatment | Product, privacy/legal, security | **Blocked** |
| External content and authenticated-link policy | Security, privacy/legal, product | **Blocked** |
| Quiet hours, severity, digest, unsubscribe, and rate rules | Product, privacy/legal | **Blocked** |
| Email, webhook, Telegram, status, or support provider | Capability owner, security, privacy/legal, finance where applicable | **Blocked** |
| Destination verification, secret rotation, and incident response | Security, operations | **Blocked** |
| Retention, export, deletion, and legal notices | Privacy/legal, product, finance where applicable | **Blocked** |

20D requires approved notification definitions. 20E additionally requires an
approved provider ADR, relevant Phase 19 external prerequisites, and sandbox
evidence.

# Phase 20I — Reduced Support, Privacy, and Status Approval

Date: 2026-08-28

Status: **Approved for implementation on the portfolio profile**

Base merge: `54329c6911fa1fada2160cc98ac0a57a3aaa5acc` (Phase 20H)

Implementation branch: `agent/v1-phase-20i-support-privacy-status`

## Owner decision

Proceed with Phase 20I only as the reduced first-party portfolio slice. This approval does not authorize Phase 20G, commercial support operations, external helpdesk/status providers, subscriber-email collection, external delivery, production commercial activation, or any new legal/finance retention claim.

## Approved request taxonomy

The initial request types are exactly:

- `support`
- `feedback`
- `abuse_report`
- `privacy_access_export`
- `privacy_deletion`

No attachment support is approved for this slice.

Request input is bounded to:

- subject: maximum 120 characters;
- description: maximum 4,000 characters.

Free-form request text must not be copied into product analytics, normal logs, notification bodies, audit metadata, automatic LLM prompts, embeddings, RAG, or external-provider payloads.

## Authority boundaries

Phase 20I may track first-party intake, ownership, verification state, workflow state, timestamps/deadlines, and bounded communication/status metadata.

Existing Phase 16 account export/deletion services remain the authority that performs account export and account deletion. Phase 20I must not create a second export or deletion engine.

Organization scope must remain server-derived and tenant-safe. No platform-admin shortcut may expose another tenant's request text.

Privacy requests must be authenticated and owned by the requesting user. Any organization-related request must use existing organization membership/role policies rather than client-supplied authority.

## Data-model approval

Migration `0029` is approved for this reduced slice only, provided the implementation first confirms that the repository migration head is Phase 20H `20260824_0028` and that no conflicting `0029` exists.

Preferred implementation is one bounded `customer_requests` table unless materially different lifecycle semantics require a split.

Approved durable fields may include:

- id;
- request type;
- owner user id;
- optional organization id where server-authorized;
- bounded subject and description;
- workflow state;
- verification state where required;
- created/updated/closed timestamps;
- optional due timestamp only when derived from a code-owned portfolio policy;
- bounded code-owned status/communication metadata;
- safe audit lineage.

Do not add attachments, private-person assignee identifiers, external helpdesk IDs that imply a real provider, payment/billing fields, arbitrary metadata blobs, LLM output, embeddings, or RAG linkage.

No new legal-hold mechanism or post-deletion legal/finance retention period is approved. Do not invent statutory deadlines or retention durations. If the existing repository has no approved retention value for these rows, keep lifecycle handling explicit and conservative and document the unresolved production/legal retention question rather than guessing.

## Status surface

A simple public-safe status surface/process is sufficient. It may expose only code-owned service health/availability information already safe to publish. Do not expose private request content, customer identifiers, internal incidents, stack traces, provider secrets, or operational security details.

No external status-page provider is required.

## Privacy and logging

Request text is private application content. Logs and audit events must record only bounded identifiers, action/state codes, request type, and safe counts/statuses where needed. Never log description/subject verbatim unless the repository already has a specifically approved private-content logging mechanism; this approval does not create one.

No automatic LLM processing of support/privacy request text is approved.

## Lifecycle

Integrate with existing account and organization lifecycle authorities. Account deletion must not leave a normal-product-accessible orphaned request row. Organization deletion must not create cross-tenant visibility. Export projections may include the user's own safe request metadata/content where consistent with the existing account export authority, but must not expose internal audit/security data.

## Completion gate

Phase 20I is complete only after migration rollback evidence, tenant isolation, authorization, privacy-text non-leakage, lifecycle/export/deletion integration, browser accessibility, PostgreSQL tests, regression suites, and hosted CI pass for the exact implementation head.

Phase 20G remains **DEFERRED**. Phase 20J is next after Phase 20I completion.

# V1 Phase 16 — Production Identity, Ownership, and Quotas

Status: **In progress**

Branch under active development: `agent/v1-phase-16-identity-ownership`

This document is the authoritative implementation contract for V1 Phase 16. It defines the required behavior, security invariants, test evidence, completion gates, and known gaps. Future implementation prompts should reference this document instead of restating the full phase.

Related documents:

- [`development_plan.md`](development_plan.md) — roadmap and phase ordering
- [`current_state.md`](current_state.md) — what is actually implemented now
- [`architecture.md`](architecture.md) — system-wide architecture
- [`deployment.md`](deployment.md) — environment and deployment rules
- [`testing.md`](testing.md) — validation commands and test matrix
- [`future_phase_contracts.md`](future_phase_contracts.md) — Phases 17–21
- [`agent_execution_guide.md`](agent_execution_guide.md) — short-prompt workflow

---

## 1. Goal

Move the application from a shared portfolio demo into a secure multi-user product foundation while preserving the Phase 15 public-safe demo.

The same product architecture must support:

- anonymous public-demo visitors;
- authenticated individual users;
- organization members;
- organization owners and administrators;
- platform administrators.

Phase 16 establishes identity, authorization, ownership, account lifecycle, consent, and quota boundaries. It does not implement background workers, durable tenant vector storage, billing, wallets, transaction signing, custody, or trade execution.

---

## 2. Non-negotiable security principles

1. Browser JavaScript never receives or stores access or refresh tokens.
2. Tokens are never stored in `localStorage` or `sessionStorage`.
3. The Next.js server is the browser-facing authentication boundary.
4. FastAPI independently verifies every managed-identity access token.
5. Supabase claims establish identity only; application roles and plans come from the application database.
6. Client input never controls `owner_user_id`, platform role, quota counters, or anonymous session ID.
7. Resource IDs alone never grant access.
8. Unauthorized private resources return a safe `404` where existence disclosure is unnecessary.
9. Public mode must not silently grant administrator access.
10. Public-demo restrictions are based on the actor and operation, not only a global deployment flag.
11. Organization access requires an active organization and an active permitted membership.
12. `private`, `organization`, and `public_demo` visibility have mutually exclusive authorization semantics.
13. Provider credentials, service-role keys, refresh tokens, private audit metadata, and encryption material never reach the browser or logs.
14. Phase 15 deterministic risk, source provenance, missing-data visibility, and public safety rules must not regress.

---

## 3. Required architecture

```text
Browser
  -> Vercel Next.js application
     -> same-origin auth route handlers
     -> same-origin backend BFF routes
     -> HttpOnly access, refresh, expiry, and anonymous-session cookies
  -> Render FastAPI API
     -> Supabase JWKS token verification
     -> application user synchronization
     -> centralized authorization policies
     -> PostgreSQL ownership and quota persistence
  -> Supabase PostgreSQL
```

### Browser rule

Browser components call same-origin Next.js paths such as:

```text
/api/auth/*
/api/backend/*
```

They do not call authenticated Render endpoints directly.

### BFF rule

The BFF must:

- forward only explicitly approved backend route families;
- reject arbitrary destinations, schemes, hosts, ports, and path traversal;
- attach a validated or refreshed access token as `Authorization: Bearer ...`;
- preserve only cookies intentionally required by the backend, such as the anonymous-session cookie;
- never forward Supabase refresh tokens or unrelated frontend cookies to Render;
- copy only safe response headers;
- preserve safe backend status codes and JSON bodies;
- propagate anonymous-session `Set-Cookie` responses to the browser;
- clear authentication cookies after failed refresh;
- use server-only `BACKEND_API_BASE_URL`.

A prefix list containing `/` is not an allowlist because every absolute path begins with `/`. The allowlist must enumerate approved route families or use route-specific proxy handlers.

---

## 4. Authentication and session contract

### 4.1 Supabase login

Login exchanges email and password with Supabase from a Next.js server route. A successful session stores:

- access token in an HttpOnly cookie;
- refresh token in a separate HttpOnly cookie;
- explicit access-token expiration metadata;
- secure cookie attributes appropriate to the environment.

Cookie requirements:

```text
HttpOnly=true
Secure=true in production
SameSite=Lax or stricter when compatible
Path=/
explicit Max-Age
```

### 4.2 Refresh rotation

Before a BFF request forwards authentication:

1. read access-token expiration;
2. use the access token when it remains valid beyond the safety window;
3. otherwise exchange the refresh token with Supabase;
4. replace both cookies when Supabase rotates the session;
5. clear all session cookies if refresh fails;
6. return an unauthenticated response without exposing provider internals.

### 4.3 Logout

Logout clears:

- access-token cookie;
- refresh-token cookie;
- expiration cookie;
- local anonymous cookie when the user explicitly resets the anonymous session.

Server-side Supabase sign-out may be added where it materially revokes provider sessions, but local cookie removal is always required.

### 4.4 Email verification

When `REQUIRE_VERIFIED_EMAIL=true`, authenticated product access requires verified email claims synchronized into the local user record.

### 4.5 Password recovery

The complete recovery flow is:

```text
recovery request
  -> generic success response
  -> Supabase recovery email
  -> controlled callback route
  -> code/token exchange on the server
  -> temporary recovery session in HttpOnly cookies
  -> password update
  -> recovery session cleared or replaced
```

The recovery callback must:

- validate provider parameters;
- validate redirect targets against an allowlist;
- reject expired or reused recovery sessions;
- avoid putting recovery tokens in browser storage;
- avoid account enumeration.

A reset form that only expects an already-existing normal session is not a complete recovery implementation.

---

## 5. Backend JWT verification contract

FastAPI verifies managed tokens independently.

Required checks:

- JWT has exactly three segments;
- header and payload decode safely;
- accepted algorithm is explicit;
- `kid` is present;
- signing key is loaded from the configured Supabase JWKS endpoint;
- signature is valid;
- `exp` is present and in the future;
- issuer matches configuration;
- audience matches configuration;
- subject is present;
- normalized email is present;
- key rotation is handled through bounded JWKS caching and refresh;
- provider/JWKS failures become controlled authentication errors;
- token contents are never logged.

Production configuration fails closed when managed authentication is enabled without the required issuer and JWKS settings.

`legacy_local` authentication is permitted only in explicit development mode and is rejected in production.

---

## 6. Application user synchronization

The application user is the authorization source of truth.

Required fields include:

```text
id
auth_provider
auth_subject
email
email_verified_at
platform_role
account_status
plan
is_active
last_login_at
deleted_at
created_at
updated_at
```

Rules:

- `auth_subject` is unique;
- email is normalized;
- platform role is database-owned;
- JWT user metadata cannot assign administrator access;
- inactive and deleted users cannot authenticate;
- identity synchronization is idempotent;
- an existing privileged or legacy account cannot be claimed merely by registering the same email;
- an existing pending invitation may be linked only after successful provider authentication and email verification;
- deleted identities have an explicit reactivation or rejection policy;
- email changes are handled without creating cross-account ownership.

### Platform roles

```text
user
admin
```

Platform administrator status is distinct from organization roles.

---

## 7. Administrator MFA contract

When `ADMIN_MFA_REQUIRED=true`, platform-admin routes require Supabase assurance level `aal2` or the currently supported equivalent.

Requirements:

- enforcement occurs in backend authentication or admin dependency code;
- frontend-provided MFA status is never trusted;
- ordinary users are not blocked from normal user routes when MFA is optional;
- administrator enrollment, TOTP verification, challenge, unenrollment, and recovery use supported Supabase APIs;
- enrollment secrets and QR material are never logged;
- enrollment and security-sensitive changes are audited;
- deployed Supabase MFA configuration is manually verified before Phase 16 completion.

An informational account-security page plus an `aal2` check is only a partial implementation until enrollment and challenge paths are usable.

---

## 8. Actor model

Authorization decisions use an explicit actor classification.

### Anonymous visitor

May:

- read public seeded demo data;
- run bounded analysis, simulation, options, and market-data requests;
- read only anonymous resources associated with the same server-generated session.

May not:

- create durable theses or watchlists;
- run monitoring, discovery, evaluation, review, RAG ingestion, document ingestion, credentials, audit, or Vast operations;
- select an arbitrary anonymous session ID.

### Authenticated user

May:

- create and access owned private resources;
- use permitted product compute within quota;
- manage their account, consent, export, and deletion;
- create organizations and manage resources according to membership role.

### Organization roles

```text
owner
admin
member
viewer
```

Suggested permissions:

| Capability | owner | admin | member | viewer |
|---|---:|---:|---:|---:|
| Read organization resources | yes | yes | yes | yes |
| Create ordinary organization resources | yes | yes | yes | no |
| Update ordinary organization resources | yes | yes | yes, when policy permits | no |
| Manage organization settings | yes | yes | no | no |
| Manage memberships | yes | yes | no | no |
| Delete organization | yes | configurable | no | no |
| Remove final owner | no | no | no | no |

### Platform administrator

May use explicitly protected platform operations. Platform-admin access is not a general bypass for private user content unless a documented support, security, or compliance operation requires it and is audited.

---

## 9. Organization lifecycle contract

Organization fields:

```text
id
name
slug
status
created_by_user_id
created_at
updated_at
deleted_at
```

Membership fields:

```text
id
organization_id
user_id
role
status
created_at
updated_at
```

Membership status supports at least:

```text
pending
active
removed
```

Rules:

- slug is unique;
- creator becomes the first active owner;
- an organization always retains at least one active owner;
- users may belong to multiple organizations;
- membership is unique per user and organization;
- unknown email additions create a pending invitation foundation, not an active verified user;
- removed membership loses access immediately;
- disabled or deleted organization loses access immediately;
- organization authorization checks both organization state and membership state;
- organization deletion and membership administration are audited;
- repeated deletion is idempotent or returns a controlled result.

---

## 10. Resource ownership and visibility

Supported visibility values:

```text
private
organization
public_demo
```

### 10.1 Private

```text
visibility=private
```

Access:

- owner may read and update;
- organization membership does not grant access;
- stale `organization_id` must be ignored or cleared;
- other users receive `404`.

### 10.2 Organization

```text
visibility=organization
organization_id=<active organization>
```

Access requires:

- active, non-deleted organization;
- active membership;
- permitted role for the requested action.

### 10.3 Public demo

```text
visibility=public_demo
```

Public seeded data may be read globally. It cannot be mutated through public endpoints.

### 10.4 Anonymous private resources

```text
visibility=private
anonymous_session_id=<server-generated session>
expires_at=<required timestamp>
```

Only the matching active anonymous session may read the resource.

### 10.5 Required fields

Scoped resources use the relevant subset of:

```text
owner_user_id
organization_id
visibility
anonymous_session_id
expires_at
deleted_at
```

The authorization policy must test visibility before considering organization membership. A non-null `organization_id` must not make a `private` resource organization-readable.

When visibility changes:

- organization -> private clears `organization_id`;
- private -> organization validates active membership and sets `organization_id`;
- no client may directly set the owner;
- ownership transfer requires a separate privileged operation and audit event.

Resources covered by Phase 16 include:

- analysis requests;
- reports and exports;
- saved theses;
- watchlists;
- alerts through the parent watchlist;
- organization knowledge metadata where implemented;
- user-visible audit/export records where applicable.

---

## 11. Anonymous-session isolation

Anonymous session IDs are:

- generated server-side with cryptographic entropy;
- stored in HttpOnly cookies;
- never logged;
- never accepted from request bodies or query parameters;
- persisted with active status and expiration;
- renewed or replaced according to a documented policy.

Required integration behavior:

```text
browser A creates analysis
  -> browser A receives/retains anonymous cookie
  -> browser A reads generated report
  -> browser B receives 404
  -> expired browser A session receives 404
```

Anonymous analysis requests and reports receive `expires_at` when created. Cleanup removes expired records without deleting seeded public reports.

---

## 12. Route authorization matrix

The route dependency must match the operation even when `PUBLIC_DEMO_MODE=false`.

| Route family | Anonymous | Authenticated user | Org role | Platform admin |
|---|---|---|---|---|
| health/readiness/deployment-safe metadata | read | read | read | read |
| public seeded reports/protocols/demo | read | read | read | read |
| analysis/simulation/options/market data | bounded + anonymous quota | user quota | user/org context where applicable | configurable exemption |
| owned reports/theses/watchlists/alerts | own anonymous only where supported | own | permitted org scope | only documented audited access |
| organizations | no | create/list own memberships | role-based | platform support/admin routes only |
| monitoring/discovery/evaluation | no | no | no unless explicitly tenant-scoped | required |
| review and global RAG ingestion | read only when intentionally public | no mutation | org-specific policy only | required |
| document ingestion | no | no global ingestion | owner/admin for org corpus | required for global corpus |
| credentials/audit/Vast | no | no | no | required |

A global dependency that blocks every mutation whenever `PUBLIC_DEMO_MODE=true` prevents authenticated users from coexisting with the public demo. The final implementation must evaluate the actor and route capability instead.

---

## 13. Quota contract

### Daily usage quotas

Actions include:

```text
analysis
simulation
options_analysis
market_data_fetch
```

Quota identity:

- anonymous session for anonymous actors;
- application user for authenticated actors;
- plan and platform-role rules from the database/configuration.

Required behavior:

- explicit UTC period boundaries;
- transaction-safe check and increment;
- PostgreSQL-safe concurrent first use;
- no unhandled unique-constraint errors;
- exact limit succeeds;
- next request returns controlled `429`;
- remaining-limit headers or response metadata are safe;
- admin exemption is configurable;
- frontend never supplies counters or plan.

The first-use path must use an atomic upsert/update or a controlled retry around the unique quota-period constraint. `SELECT ... FOR UPDATE` alone does not protect a row that does not yet exist.

### Resource-count quotas

Resources include:

```text
saved_theses
watchlists
```

Rules:

- count active, non-deleted owned resources;
- deletion releases capacity;
- anonymous actors cannot create durable resources;
- organization-owned resource quota policy is explicit;
- count and creation are transactionally protected where concurrency matters.

Billing is not part of Phase 16.

---

## 14. Saved theses and personal resources

Saved thesis fields include:

```text
id
owner_user_id
organization_id
title
strategy_text
protocols
assumptions_json
visibility
created_at
updated_at
expires_at
deleted_at
```

User workflow:

- list visible theses;
- create private thesis;
- create organization thesis with valid membership;
- open and edit;
- delete/soft-delete;
- start analysis from thesis content;
- receive clear loading, empty, authorization, and quota states.

Frontend forms never expose editable ownership fields.

---

## 15. Knowledge-base boundary

Phase 16 defines authorization and metadata boundaries only. Phase 18 supplies durable object/vector storage.

Phase 16 requirements:

- public curated demo knowledge remains public;
- global discovery/review/ingestion remains platform-admin controlled;
- organization knowledge metadata is scoped to an active organization;
- organization ingestion requires owner/admin authorization;
- retrieval cannot select another tenant by changing request input;
- deleted/disabled organization sources are unavailable;
- source provenance and human approval remain mandatory;
- documentation must not claim tenant-specific RAG if retrieval is still global/local JSON.

---

## 16. Account, consent, export, and deletion

### Account export

A bounded synchronous export may include:

- user profile;
- active and historical memberships as appropriate;
- saved theses;
- owned reports;
- watchlists and alerts;
- consent records;
- user-visible audit events.

It excludes:

- password or token hashes;
- refresh/access tokens;
- provider secrets;
- encryption keys;
- other users' data;
- internal sensitive audit metadata.

### Account deletion

Deletion requires exact confirmation and recent authentication where supported.

Immediate effects:

- account becomes inactive/deleted;
- access stops immediately;
- sessions are cleared/revoked;
- final organization ownership prevents deletion until transferred or organization deleted;
- active memberships are removed or disabled;
- provider identity deletion is completed or explicitly queued/deferred.

Retention effects:

- personal identifiers are deleted or anonymized after configured retention;
- `auth_subject` and token hashes are cleared according to policy;
- private resources are deleted, anonymized, or reassigned explicitly;
- redacted audit records may remain when operationally required;
- dry-run performs no mutations;
- cleanup is idempotent.

### Consent

Terms and privacy versions are server-owned configuration values.

Rules:

- signup requires explicit acceptance;
- client cannot choose arbitrary accepted versions;
- versions are persisted after identity synchronization;
- repeated synchronization is idempotent;
- policy changes can require renewed consent;
- consent withdrawal behavior is documented;
- legal copy is marked for qualified review before commercial launch.

---

## 17. Database and migration contract

Alembic migrations must upgrade the Phase 15 database without reset.

Requirements:

- preserve public seeded records;
- backfill existing reports/watchlists/analysis requests to safe visibility;
- add ownership indexes;
- add uniqueness constraints for identity, membership, slug, and quota period;
- use foreign keys for ownership and organization references where practical;
- choose `RESTRICT`, `SET NULL`, or controlled application deletion intentionally;
- support downgrade/upgrade validation;
- test PostgreSQL, not only SQLite;
- test existing Phase 15 data.

Useful compound indexes include:

```text
owner_user_id + deleted_at
organization_id + visibility + deleted_at
anonymous_session_id + expires_at
subject_id + action + period_start
```

The implemented Phase 16C migration is `20260721_0010`. It uses `SET NULL` for nullable resource owner, organization, and anonymous-session links so a hard cleanup cannot leave a dangling identifier; resource visibility is unchanged when an invalid legacy nullable link is detached. It uses `RESTRICT` for saved-thesis owner and consent user links because silently detaching either would alter the record's ownership or legal meaning. The migration fails with a clear diagnostic when either required legacy reference is invalid.

The following references intentionally remain without a direct foreign key:

- `usage_quotas.subject_id`, because it is a polymorphic user-or-anonymous-session subject; the `(subject_type, subject_id, action, period_end)` index supports its access path instead;
- `access_audit_events.actor_user_id`, because audit history must remain available after a user is soft-deleted or later purged by a controlled retention process;
- resource `visibility`, because its valid transitions and organization membership checks are enforced by centralized application policy rather than a static database check constraint.

---

## 18. Frontend completion contract

Required routes/workflows:

```text
/login
/signup
/verify-email
/forgot-password
/reset-password
/account
/account/security
/theses
/organizations
/organizations/[id]
/organizations/[id]/members
/terms
/privacy
```

Required behavior:

- authentication-aware header;
- no private-content flash before session resolution;
- validated post-login redirect;
- logout;
- session-expiration handling;
- account profile, usage, export, deletion, consent, and MFA state;
- functional thesis CRUD and analyze-from-thesis;
- functional organization and membership management;
- accessible labels, errors, loading states, and keyboard focus;
- all authenticated backend access through the BFF.

Placeholder informational pages do not satisfy completion gates.

---

## 19. Required tests

### Authentication

- valid managed token;
- malformed token;
- unsupported algorithm;
- missing key ID;
- invalid signature;
- expired token;
- wrong issuer;
- wrong audience;
- missing subject/email;
- unverified email;
- inactive/deleted user;
- identity collision with existing admin/common/deleted accounts;
- pending-invitation linking;
- JWKS failure and rotation;
- refresh success and failure;
- logout;
- admin MFA `aal2` enforcement.

### Ownership

- User A cannot read/update User B private resources;
- private resource remains private even with stale organization ID;
- organization member reads permitted organization resource;
- viewer cannot mutate;
- removed member loses access;
- disabled/deleted organization loses access;
- final owner cannot be removed;
- arbitrary owner/organization assignment is rejected;
- public seeded resource remains public.

### Anonymous

- same browser creates and reads anonymous report;
- second browser receives `404`;
- expired session loses access;
- expired resources are cleaned;
- public seeded resources remain.

### Quotas

- exact limit;
- exceeded limit;
- period reset;
- anonymous/user/admin differences;
- saved-resource limit and deletion release;
- concurrent first-use PostgreSQL behavior.

### Account lifecycle

- export contains only caller data;
- export excludes secrets;
- deletion blocks access;
- final-owner deletion is blocked;
- retention anonymizes/deletes as documented;
- dry-run is mutation-free.

### Browser integration

- public anonymous analysis/report flow;
- login -> BFF -> FastAPI flow;
- access-token refresh;
- logout;
- organization workflow;
- thesis workflow;
- recovery callback and reset;
- consent persistence;
- admin MFA denial/allow.

---

## 20. Current branch audit

Reviewed correction commit: `bf1b9ddc6153e02f2018c4a43ba20bb634e82709`.

### Present in the branch

- Supabase RS256/JWKS verification with issuer, audience, expiration, signature, subject, and email checks;
- production rejection of legacy local authentication;
- Next.js same-origin backend BFF foundation;
- BFF explicit route-family allowlist without the former catch-all `/` prefix;
- BFF forwarding of only the anonymous backend cookie rather than the full frontend cookie header;
- HttpOnly access/refresh/expiry cookies and refresh rotation foundation;
- application users, platform roles, organizations, memberships, saved theses, quota, consent, and anonymous-session models;
- pending-invitation user foundation;
- email-collision protection for non-pending local accounts;
- administrator `aal2` enforcement foundation;
- functional same-origin Supabase TOTP enrollment, challenge/verification, factor listing, and unenrollment workflow;
- HttpOnly access/refresh cookie rotation after MFA verification with sanitized provider responses;
- organization active/deleted checks in membership-role lookup;
- strict private/organization visibility checks before organization membership is considered;
- organization-owned, human-approved source metadata with `metadata_only` storage status and active-membership authorization;
- server-derived retrieval scope that keeps the shared local JSON index public-curated only and rejects organization-tagged chunks;
- actor-based durable mutation dependencies that preserve public anonymous restrictions while allowing authenticated users/admins in hybrid mode;
- anonymous report expiration foundation;
- resource-count quotas for saved theses/watchlists;
- controlled quota first-use retry and per-user resource-count lock rows for PostgreSQL-safe limit checks;
- server-owned terms/privacy version recording for signup and consent renewal;
- controlled Supabase recovery callback/code-exchange foundation in the Next.js auth boundary;
- account export/deletion and retention cleanup foundations;
- Phase 16C ownership/organization/anonymous-session/saved-thesis/consent foreign keys and compound authorization/quota indexes, with Phase 15 data preservation and PostgreSQL migration-cycle evidence;
- Phase 16D lifecycle/security audit events with bounded redacted metadata, administrator-only audit access, user-visible export projections, and a server-only BFF MFA audit channel;
- Phase 16E PostgreSQL first-use quota races, resource-count serialization, exact-limit/deletion-release behavior, and migrated Phase 15 public API regression coverage;
- expanded JWT, anonymous isolation, quota, and cleanup tests;
- account, thesis, organization, dynamic organization-detail/member routes, and authentication-aware header frontend components;
- production-like Chromium browser E2E with local mocked Supabase/FastAPI upstreams, including anonymous isolation/expiry, BFF login/refresh/logout and cookie rotation, recovery/reset, account consent/export/deletion confirmation, thesis CRUD/analyze, organization owner protection/member removal, MFA, no-private-content flash, and mobile keyboard/layout smoke. Failure screenshots/traces are available locally and uploaded by CI.

### Remaining blockers before Phase 16 can be marked complete

1. Deployed Supabase email verification, recovery, MFA, and cross-domain behavior remain unverified; 16A is locally complete, while live-provider verification remains a 16G gate.
2. Legal review of terms/privacy remains external.

The documentation and roadmap must retain `Phase 16 — In Progress` until these blockers and the completion gates below are resolved.

---

## 21. Completion gates

Phase 16 is complete only when all are true:

- same-origin BFF uses an effective explicit allowlist;
- BFF forwards only necessary cookies and headers;
- access-token refresh and rotation work in browser tests;
- public anonymous and authenticated users coexist in one deployment;
- privileged routes use explicit actor/role dependencies;
- strict private/organization/public visibility semantics pass tests;
- organization deletion and membership removal revoke access immediately;
- anonymous reports remain retrievable only by their session and expire;
- quota increments and resource limits are concurrency-safe in PostgreSQL;
- recovery callback and password reset work;
- consent versions are server-owned and persisted;
- admin MFA is enforceable and enrollment/challenge flow is usable;
- account export/deletion/retention match the documented policy;
- thesis and organization frontend workflows are functional;
- organization knowledge metadata is correctly scoped without overstating Phase 18 storage;
- Phase 15 regression suite passes;
- Alembic upgrade/downgrade/upgrade passes on PostgreSQL with Phase 15 data;
- backend, frontend, Compose, and browser tests pass;
- deployed Supabase flows are manually verified;
- legal/privacy limitations are explicit;
- documentation matches implementation.

---

## 22. Out of scope

Phase 16 does not include:

- durable job queue or workers;
- object-storage artifact pipeline;
- pgvector or tenant vector index;
- distributed rate limiting;
- full observability/WAF/incident operations;
- billing or payment processing;
- scheduled notifications;
- autonomous research/model expansion;
- wallets, private keys, custody, signing, trade execution, or capital allocation.

These belong to later phase contracts.

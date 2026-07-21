# Phase 16G Deployed Verification Record

Status: **Blocked externally**

Date recorded: 2026-07-21

This record distinguishes the intentionally deployed Phase 15 public demo from the not-yet-deployed Phase 16 managed-identity target. It contains no credentials, tokens, account identifiers, or mailbox contents.

## Current Live Evidence

| Target | Result | Interpretation |
| --- | --- | --- |
| `https://defi-thesis-risk-copilot.vercel.app/` | `200` | Current public Phase 15 frontend is live. |
| `https://defi-thesis-risk-copilot.vercel.app/login` | `404` | The Phase 16 identity frontend has not been deployed to this domain. |
| `https://defi-thesis-risk-copilot.vercel.app/api/auth/session` | `404` | The deployed frontend has no Phase 16 BFF session handler. |
| `https://defi-thesis-risk-copilot.onrender.com/health` | `200` | Backend is live and healthy. |
| `https://defi-thesis-risk-copilot.onrender.com/ready` | `200` with database and RAG ready | The Phase 15 backend startup path is healthy. |
| `https://defi-thesis-risk-copilot.onrender.com/api/deployment/status` | `portfolio_demo`, `public_demo_mode=true`, `auth_enabled=false` | Render is intentionally serving the Phase 15 public-safe configuration, not Phase 16 hybrid authentication. |
| Public POST probes for document ingestion, credentials, and watchlists | controlled `403` responses | Existing Phase 15 privileged-mutation protections remain active. |

The live status payload exposed no provider key, access token, refresh token, or session material. The current Vercel response also rendered the public-demo badge, consistent with the Phase 15 baseline.

## Blocker

No local deployment credential or configured provider access is available for the required external systems. At the time of this record, `VERCEL_TOKEN`, `RENDER_API_KEY`, `SUPABASE_ACCESS_TOKEN`, Supabase Auth configuration values, and `BFF_AUDIT_SECRET` were unavailable in the local environment.

The committed Render manifest intentionally retains `AUTH_ENABLED=false` for the public portfolio deployment. Enabling authentication without the required Supabase/JWKS configuration and server-only audit secret would fail closed in production and would not create valid evidence. Do not replace the current public demo deployment with a partially configured Phase 16 deployment.

## Required External Setup

Create a controlled Phase 16 preview or staged deployment from `agent/v1-phase-16-identity-ownership` before testing. Keep the existing `main` public demo unchanged until the contract gates pass.

Configure Render with:

```text
APP_ENV=production
PUBLIC_DEMO_MODE=true
AUTH_ENABLED=true
AUTH_PROVIDER=supabase
REQUIRE_VERIFIED_EMAIL=true
FRONTEND_ORIGIN=<exact Vercel preview origin>
SUPABASE_URL=<project URL>
SUPABASE_JWKS_URL=<project JWKS URL>
SUPABASE_JWT_ISSUER=<project Auth issuer>
SUPABASE_JWT_AUDIENCE=authenticated
BFF_AUDIT_SECRET=<new long random server-only value>
DATABASE_URL=<Supabase PostgreSQL URL with sslmode=require>
```

Configure the Vercel preview server runtime with:

```text
BACKEND_API_BASE_URL=<exact Render preview origin>
SUPABASE_URL=<project URL>
SUPABASE_ANON_KEY=<public anon key>
NEXT_PUBLIC_SUPABASE_URL=<project URL>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<public anon key>
SESSION_COOKIE_NAME=defi_copilot_session
ANONYMOUS_SESSION_COOKIE_NAME=defi_copilot_anon
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
BFF_AUDIT_SECRET=<same server-only value>
```

Configure Supabase Auth with the exact Vercel preview origin as Site URL and redirect allowlist entries for:

```text
<preview-origin>/verify-email
<preview-origin>/api/auth/recovery-callback
<preview-origin>/reset-password
```

Enable TOTP only after a test administrator and recovery path are available. Platform-admin authorization remains database-owned; Supabase user metadata alone must not assign administrator authority.

## Manual Verification Matrix

Run each case in a clean browser profile against the paired Vercel and Render preview origins. Record the date, preview URLs, result, and any safe request IDs below before moving to 16H.

| Case | Required result | Status |
| --- | --- | --- |
| Signup and email verification | Email arrives; verified user can sign in; unverified user is denied | Pending external setup |
| Login and BFF session | HttpOnly cookies created; no token in browser storage; BFF reaches Render | Pending external setup |
| Refresh and logout | Expired access token rotates; logout clears session; private routes deny afterward | Pending external setup |
| Anonymous/public coexistence | Public analysis remains session-isolated; authenticated user can mutate only owned resources | Pending external setup |
| Private and organization access | Cross-user denial, member removal, organization disable/delete, and final-owner protection match the contract | Pending external setup |
| Recovery | Email, callback exchange, reset, and expired/reused-link behavior work without URL or storage token leakage | Pending external setup |
| Consent/export/deletion | Server-owned consent versions persist; export remains bounded; typed deletion confirmation and final-owner block work | Pending external setup |
| Admin MFA | `aal1` admin denial; enrollment/challenge reach `aal2`; audited allow state; ordinary user remains usable | Pending external setup |
| CORS and secrets | Vercel-to-Render requests use the BFF; no token/secret appears in browser, status, or logs | Pending external setup |

## Local Evidence

[`phase_16_execution_plan.md`](phase_16_execution_plan.md) records the completed local 16F Chromium suite. That suite uses mocked providers and does not replace this deployed provider verification.

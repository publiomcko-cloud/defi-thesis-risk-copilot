# Phase 16G Deployed Verification Record

Status: **In Progress -- hosted configuration and automated checks complete; interactive identity checks remain**

Date updated: 2026-07-22

This record distinguishes the intentionally deployed Phase 15 public demo from the configured Phase 16 preview. It contains no credentials, tokens, account identifiers, database URLs, or mailbox contents.

## Deployment Targets

| Target | Result | Interpretation |
| --- | --- | --- |
| `https://defi-thesis-risk-copilot.vercel.app/` | Phase 15 public production remains unchanged | Safe public baseline. |
| `https://defi-thesis-risk-copilot-dn7w7mtvq-publio1.vercel.app/` | Phase 16 branch preview, Vercel protected | Phase 16 identity frontend and same-origin BFF are deployed. |
| `https://defi-thesis-risk-copilot-api-phase16.onrender.com/ready` | `200` | Phase 16 backend database and runtime are ready. |
| `https://defi-thesis-risk-copilot-api-phase16.onrender.com/api/deployment/status` | `production`, `public_demo_mode=true`, `auth_enabled=true` | Phase 16 hybrid public-demo plus Supabase-auth configuration is live. |

The Vercel preview uses standard Vercel Authentication protection. Automated checks used Vercel's protected-preview bypass rather than weakening preview protection. The backend status payload exposed no credential, token, password, database URL, or secret key.

## Hosted Configuration Applied

The isolated preview is configured with:

- Render `APP_ENV=production`, `PUBLIC_DEMO_MODE=true`, `AUTH_ENABLED=true`, `AUTH_PROVIDER=supabase`, verified-email enforcement, Supabase URL/JWKS/issuer/audience, strict preview `FRONTEND_ORIGIN`, and a server-only BFF audit secret;
- Vercel branch-scoped preview variables for the Render preview, Supabase public browser key, HttpOnly-cookie policy, and the same server-only BFF audit secret;
- Supabase email confirmation, no unverified sign-in, TOTP enrollment and verification, the production site URL, and exact production/preview/local redirect allowlist entries.

The original working Render database configuration was retained. A Supabase Management API pooler response must not be copied as a replacement database credential without independently verifying its password.

## Automated Hosted Evidence

The following checks passed against the paired Phase 16 Vercel and Render previews:

- Render `/health`, `/ready`, and deployment status returned `200`; the status reports `auth_enabled=true` and database connectivity;
- unauthenticated BFF session request returned `authenticated:false`;
- public protocol data was retrieved through `/api/backend/*`;
- an unauthenticated private thesis request returned controlled `401`;
- a real anonymous analysis created a report that was readable with its originating anonymous cookie (`200`) and denied to a distinct anonymous cookie (`404`);
- direct backend preflight returned the exact Vercel preview origin and credentialed CORS policy;
- deployment-status field names contained no token, secret, password, or key material.

## Manual Verification Matrix

Run each case in a clean browser profile against the paired Vercel and Render preview origins. Record the date, preview URLs, result, and any safe request IDs below before moving to 16H.

| Case | Required result | Status |
| --- | --- | --- |
| Signup and email verification | Email arrives; verified user can sign in; unverified user is denied | Pending interactive inbox test |
| Login and BFF session | HttpOnly cookies created; no token in browser storage; BFF reaches Render | BFF routing verified; pending authenticated-browser test |
| Refresh and logout | Expired access token rotates; logout clears session; private routes deny afterward | Pending authenticated-browser test |
| Anonymous/public coexistence | Public analysis remains session-isolated; authenticated user can mutate only owned resources | Anonymous isolation verified; pending authenticated-user mutation test |
| Private and organization access | Cross-user denial, member removal, organization disable/delete, and final-owner protection match the contract | Pending authenticated-browser test |
| Recovery | Email, callback exchange, reset, and expired/reused-link behavior work without URL or storage token leakage | Pending interactive inbox test |
| Consent/export/deletion | Server-owned consent versions persist; export remains bounded; typed deletion confirmation and final-owner block work | Pending authenticated-browser test |
| Admin MFA | `aal1` admin denial; enrollment/challenge reach `aal2`; audited allow state; ordinary user remains usable | Pending test administrator, recovery path, and authenticator test |
| CORS and secrets | Vercel-to-Render requests use the BFF; no token/secret appears in browser, status, or logs | Automated server checks passed; pending authenticated-browser storage/network inspection |

## Local Evidence

[`phase_16_execution_plan.md`](phase_16_execution_plan.md) records the completed local 16F Chromium suite. That suite uses mocked providers and does not replace this deployed provider verification.

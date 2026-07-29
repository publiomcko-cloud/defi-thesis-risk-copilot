# Phase 19E Secret Inventory and Rotation Runbook

Status: **inventory template and local lifecycle evidence.** This document lists
identifiers, owner roles, and rotation procedures only. It must never contain a
secret value, token prefix, encrypted blob, provider URL with credentials, or a
customer identifier.

## Inventory

| Identifier | Owner role | Approved location | Rotation / emergency action | Current evidence |
| --- | --- | --- | --- | --- |
| Supabase database and service credentials | Platform owner | Provider/platform secret store | Provider-native rotation; update server secret; validate isolated restore | External evidence required |
| Supabase JWT/JWKS configuration | Platform owner | Server configuration | Follow provider rotation; validate login and MFA | External evidence required |
| `CREDENTIAL_ENCRYPTION_KEY` | Security owner | Backend server secret store | Dual-read/re-encrypt migration required before replacement | Migration not implemented |
| `WORKER_TOKEN_PEPPER` | Worker owner | Worker/backend secret stores | Issue scoped replacement, deploy, revoke predecessor | Phase 17 tested locally |
| Worker credential token | Worker owner | Trusted worker secret store | Rotate through platform-admin API; plaintext is returned once | Phase 17 tested locally |
| Provider credential secret | Provider owner | Encrypted backend database record | Update/rotate in private admin UI, validate, disable on exposure | Phase 19E tested locally |
| `RATE_LIMIT_KEY_PEPPER` | Security owner | Backend server secret store | Stage shadow limiter after replacement | Deployment evidence required |
| Supabase private-storage credential | Storage owner | Backend server secret store | Provider-native rotation; run isolated storage probe | Phase 18/22 evidence required |
| Optional LLM/provider keys | Provider owner | Server secret store or encrypted admin record | Rotate with provider; validate deterministic fallback | Provider validation required |

The named human owner, backup owner, evidence reference, and next rotation date
belong in the approved operations system, not this repository.

## Worker rotation

1. Confirm the scoped worker and permitted job types.
2. Issue a replacement credential from the platform-admin API and place the
   plaintext only in the trusted worker secret store.
3. Deploy the worker with the replacement, confirm a synthetic
   claim/heartbeat, then revoke the predecessor.
4. Confirm the revoked credential cannot claim or heartbeat. Preserve audit
   events, never token values.

## Provider rotation and emergency revocation

1. Add a replacement only through the private administrator interface or an
   approved server-side secret process.
2. Validate with a bounded, non-production-safe provider operation.
3. Disable the prior provider credential immediately after cutover or on
   suspected exposure.
4. For an incident, disable affected workers, pause provider jobs if needed,
   rotate the backing provider/platform secret, invalidate sessions where
   applicable, then reissue least-privilege replacements.
5. Record identifiers, owner, time, result, and evidence reference only.

## Encryption-key migration gap

Current encrypted provider credentials use one active
`CREDENTIAL_ENCRYPTION_KEY`. Safe rotation needs dual-read support,
transactional re-encryption, verification, rollback, and retirement of the
predecessor. That capability is not implemented in Phase 19E; do not rotate
this key by simply replacing its value. It remains a Phase 19E completion
blocker until an approved migration is implemented and exercised.

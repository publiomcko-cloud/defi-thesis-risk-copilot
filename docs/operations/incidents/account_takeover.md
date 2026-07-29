# Account Takeover — `identity.account-takeover`

Owner roles: identity owner (primary), security owner (backup). Communication
authority: assigned incident communications authority. Use `SEV1` when a
privileged account or multiple users may be affected; otherwise start at
`SEV2`.

## Detection

Triggers include a credible user report, recovery/MFA anomaly, impossible
session pattern from approved audit evidence, or authentication-provider notice.
Capture account references only in the private incident system.

## Immediate containment

Invalidate affected sessions through the approved identity-provider path, pause
recovery changes for the affected account where supported, and prevent
privileged actions until identity is re-verified. Do not disclose account
existence to an unverified requester.

## Eradication and scope

Review approved authentication, MFA, recovery, organization-membership, and
audit references for the relevant window. Determine whether a provider issue,
phishing, device compromise, or application defect is credible. Preserve
tenant boundaries while investigating.

## Recovery and rollback

Require the approved recovery and MFA re-enrollment flow, rotate sessions, and
verify owner/member roles through server-derived authorization. Restore access
only after the identity owner records the result. Rollback reverses only a
temporary account restriction after verification.

## Communications

The communications authority coordinates contact with the verified account
holder and any privacy/legal reviewer. Avoid sensitive authentication detail
in email, browser messages, or public channels.

## Evidence

Record incident timestamps, safe audit references, containment/recovery
decisions, affected role scope, and communication approvals. Exclude cookies,
tokens, recovery links, IP addresses, and raw user content.

## Retrospective

Review MFA/recovery controls, session lifetime, audit quality, support
verification, and any tenant/organization authorization regression tests.

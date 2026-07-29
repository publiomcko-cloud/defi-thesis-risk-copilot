# CI/CD and Supply-Chain Security Runbook

Status: **Phase 19F repository controls implemented locally; GitHub protection and deployed-scanner evidence remain external gates.**

This runbook covers repository and build-pipeline integrity. It contains no
credential values, deployment URLs with embedded secrets, customer data, or
private source content.

## Controls in the repository

The `Supply Chain Security` workflow runs on `main` pushes, pull requests,
weekly schedule, and manual dispatch. It uses a read-only default token and
does not use `pull_request_target`, deployment credentials, or preview secrets.

| Control | Current behavior | Merge policy |
| --- | --- | --- |
| Workflow policy | `scripts/supply_chain.py check-workflows` rejects mutable action references, `pull_request_target`, `write-all`, and checkout credentials persisted by default. | Blocking now. |
| Lockfile policy | Python requirements must be exact pins; npm must use a v3 lockfile with registry URLs and integrity digests. | Blocking now. |
| SBOM | A CycloneDX 1.5 source-lockfile SBOM is generated as a 30-day CI artifact. It excludes environment values, credentials, source content, and image layers. | Evidence now; use a release artifact for deployment attestation later. |
| Dependency review | GitHub reviews pull-request dependency changes, rejecting new high-severity advisories and GPL-3.0/AGPL-3.0 dependencies when the repository dependency graph is enabled. It is non-blocking until that administrator prerequisite exists. | Make blocking after dependency-graph activation and first successful evidence. |
| Secret scan | Gitleaks scans committed history and changed content with a read-only token. | Blocking after GitHub required-check configuration. |
| Dependency audit | `pip-audit` and `npm audit --omit=dev` generate baseline artifacts. | Informational until an owner has triaged each scanner/provider baseline. |
| Container scan | Trivy scans repository configuration and locally built backend/frontend images without deployment secrets. | Informational during the first baseline; high/critical findings require triage. |
| Static analysis | CodeQL scans Python and JavaScript/TypeScript without a build step. | Upload/evidence now; require after repository security-event permissions are verified. |
| Dependency updates | Dependabot proposes bounded weekly updates for pip, npm, and GitHub Actions. | Review through normal PR checks. |

All third-party actions in `.github/workflows/` are pinned to full commit SHAs.
Comments retain the reviewed release family. Renovation of an action pin occurs
only through a reviewed Dependabot pull request or a documented emergency fix.

`.gitleaksignore` contains only reviewed fingerprints for historical,
deterministic test/document fixtures. It does not ignore a file, rule, current
source, or commit history. Any new match remains a failure until it is
investigated.

## Baseline and findings process

1. Review generated artifacts and GitHub Security/Dependabot alerts without
   copying them into public tickets when they reveal a private path or finding.
2. Classify each finding as fixed, false positive, accepted risk, or awaiting a
   vendor fix. Record the scanner, identifier, affected component, severity,
   owner, decision, evidence link, and expiry in the approved private tracking
   system. Never place tokens, customer data, or exploit payloads there.
3. Critical and high findings affecting a deployed reachable path block release
   unless the accountable owner records a bounded exception and a compensating
   control. Exceptions expire and must be revisited before release.
4. Rotate or revoke exposed credentials through the Phase 19E secret inventory
   procedure. Do not paste a replacement credential into a pull request,
   workflow, artifact, log, or issue.
5. Re-run the relevant scan after remediation and retain only its safe evidence.

At the Phase 19F implementation checkpoint, the pinned application manifests
return zero known findings from `pip-audit` and `npm audit --omit=dev`. Trivy,
Gitleaks, Dependency Review, and CodeQL still need their first GitHub-hosted
baseline run and triage evidence before their outcomes can be promoted to
required release checks.

## GitHub administrator rollout

An administrator must configure a `main` ruleset or branch-protection rule after
the workflows have completed at least once:

1. Require pull requests, at least one approving review, and dismissal of stale
   approvals after new commits.
2. Require the existing `Backend and PostgreSQL`, `Frontend`, and `Docker
   Compose Config` checks.
3. After first-run triage, require `Workflow Policy and SBOM`, `Dependency
   Review`, `Secret Scan`, and the relevant CodeQL checks. Add the audited
   dependency/container baseline as a required check only once its false
   positive/exception process is operating.
4. Restrict direct pushes, force pushes, branch deletion, and bypasses. Apply
   the rule to administrators where the plan supports it.
5. Enable GitHub dependency graph, Dependabot alerts/security updates, secret
   scanning and push protection, and code scanning where the repository plan
   supports them. Verify external-contributor pull requests receive no secrets.
6. Record the rule URL, enabled checks, approver, date, and rollback owner in
   approved operational evidence, not this repository.

GitHub protection cannot be created or verified merely by committing workflow
files. Until those settings and first-run evidence exist, Phase 19F is locally
implemented but not deployment-complete.

## Rollback and emergency response

A failing new scanner may be disabled only through a reviewed pull request that
records the owner, reason, compensating control, and expiry. Do not remove the
functional CI, secret-scan, or workflow-policy checks as a workaround. For a
suspected credential leak, immediately revoke the affected credential, inspect
access/audit evidence, rotate dependent credentials, assess affected tenants,
and follow the Phase 19G incident procedure when it is available.

The repository can roll back this slice by reverting its focused commits. This
does not roll back a deployed image, revoke a leaked credential, or replace the
provider backup/restore process.

## Local verification

```bash
python3 scripts/supply_chain.py check-workflows
python3 scripts/supply_chain.py check-lockfiles
python3 scripts/supply_chain.py generate-sbom --output /tmp/defi-sbom.cdx.json

cd backend
source .venv/bin/activate
pip-audit -r requirements.txt

cd ../frontend
npm audit --omit=dev
```

Run the normal backend, PostgreSQL, frontend, browser, worker, recovery,
cleanup, and Docker checks from [`../testing.md`](../testing.md) before merging.

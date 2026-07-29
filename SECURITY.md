# Security Policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability and do not include
credentials, customer data, tokens, or private source material in a report.
Use GitHub's private security-advisory reporting flow for this repository. If
that flow is unavailable, contact the repository owner through a private GitHub
channel and include only a minimal reproduction.

The repository owner acknowledges the report, assigns a severity and owner,
records an approved remediation or time-bounded exception, and coordinates a
private fix before public disclosure. The detailed supply-chain triage and
emergency-revocation procedure is in
[`docs/operations/supply_chain_security.md`](docs/operations/supply_chain_security.md).

## Supported deployment boundary

Only the current `main` deployment configuration is supported. The product is a
research and risk-analysis application: it never accepts wallets, private keys,
custody, signing authority, or trade-execution authority. Real Vast.ai rentals
remain disabled.

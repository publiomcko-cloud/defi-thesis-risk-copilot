# Changelog

All notable changes to DeFi Thesis & Risk Copilot are documented here.

## Unreleased — V1 Product Hardening

### Phase 16 Identity, Ownership, and Quotas

- Added Supabase Auth JWT validation through JWKS with issuer, audience, expiration, subject, and signature checks.
- Added local user synchronization, explicit platform roles, account status, verified-email enforcement, and production fail-closed auth configuration.
- Added organization and membership models with owner/admin/member/viewer roles and final-owner protection.
- Added central authorization policies for private, organization, public-demo, anonymous, deleted, and expired resources.
- Added ownership fields for analysis requests, reports, and watchlists plus private report/watchlist filtering.
- Added saved theses, account export/deletion, consent records, anonymous sessions, durable quotas, and retention cleanup.
- Added frontend auth, account, security, terms, privacy, and theses pages with HttpOnly-cookie auth route foundations.

### Security

- Public hosted visitors now receive a common read-only identity instead of an implicit administrator identity.
- Public discovery, monitoring, evaluation, review, RAG, document, watchlist, credential, audit, and Vast.ai mutations are blocked.
- Public compute endpoints use bounded request schemas and per-client rate limiting.
- Analysis, simulation, options, market-data, and document schemas enforce size and numeric limits.
- Provider secrets remain server-side and public credential metadata is denied.

### Backend

- Added API root, process liveness, and database/RAG readiness endpoints.
- Added request IDs, request-duration logging, and safe exception logging.
- Added deterministic demo seeding and RAG-index generation during hosted startup.
- Updated Render to use `/ready` for health checks.
- Enforced market-cache expiration and update-in-place behavior.
- Added PostgreSQL migration/test coverage in CI.
- Added public-demo security tests.

### Frontend

- Made the live demo the primary product entry point.
- Added public-aware navigation, footer, active/focus/hover states, badges, loading feedback, responsive behavior, and reduced-motion support.
- Added free-tier cold-start retry and readiness flows.
- Added shared-public-database privacy guidance.
- Converted review and watchlist workflows to read-only hosted demonstrations.
- Protected direct credential, audit, and Vast.ai pages in public mode.
- Clarified APY, LTV, LLTV, volatility, USD, and basis-point units.
- Added progressive disclosure for advanced controls.
- Replaced raw JSON and snake-case values with readable labels.
- Added clickable report sources and Markdown copy/download.
- Removed duplicate report sections.

### Documentation

- Replaced fragmented planning documents with `docs/development_plan.md` as the authoritative phase history and roadmap.
- Preserved completed phases through Final Phase 14.
- Added V1 Phases 15-21 for hardening, identity, hybrid workers, durable RAG, operations/security, commercial readiness, and research intelligence.
- Updated README, current state, architecture, deployment, testing, and demo walkthrough with actual live URLs and the public endpoint policy.

## 0.1.0 — Technical MVP and Portfolio Expansion

### Added

- FastAPI and Next.js full-stack MVP.
- SQLAlchemy/Alembic persistence and Docker Compose.
- Curated RAG, market-data adapters, deterministic scoring, structured reports, and Markdown export.
- Optional LLM synthesis with deterministic fallback.
- Discovery, evaluation, review, human-approved RAG ingestion, simulation, watchlists, alerts, options, ML groundwork, and HPC templates.
- Admin/common access-control foundation, encrypted provider credentials, audit logs, and Vast.ai dry-run/manual warm-up.
- Deterministic demo data, example reports, and Vercel/Render/Supabase deployment preparation.

# Changelog

All notable changes to DeFi Thesis & Risk Copilot are documented here.

## Unreleased — V1 Product Hardening

### Phase 16 Identity, Ownership, and Quotas

- Added Supabase Auth JWT validation through JWKS with issuer, audience, expiration, subject, email, and signature checks.
- Added local user synchronization, explicit platform roles, account status, verified-email enforcement, and production fail-closed authentication configuration.
- Added Next.js same-origin BFF and HttpOnly access/refresh/expiration cookie foundations.
- Added organization and membership models with owner/admin/member/viewer roles, pending invitations, and final-owner protection.
- Added centralized authorization policies for private, organization, public-demo, anonymous, deleted, and expired resources.
- Added ownership fields for analysis requests, reports, and watchlists plus saved theses.
- Added account export/deletion, consent records, anonymous sessions, daily quotas, saved-resource limits, and retention cleanup.
- Added administrator MFA assurance checking foundation.
- Added account, thesis, and organization frontend foundations.
- Expanded JWT, anonymous isolation, quota, organization, and cleanup tests.
- Hardened the Phase 16 BFF allowlist and cookie forwarding so browser calls use same-origin route handlers without forwarding Supabase refresh/session cookies to FastAPI.
- Replaced deployment-only public mutation blocking with actor-aware dependencies for durable user mutations and platform-admin routes.
- Tightened private versus organization resource policy semantics, added server-owned consent versions, and added a recovery callback/code-exchange foundation.
- Completed the local Phase 16A TOTP workflow with same-origin Supabase enrollment, challenge/verification, factor management, HttpOnly session rotation, and mocked provider/route tests.
- Added Phase 16B organization knowledge-source metadata, human-approval provenance, active-membership authorization, and a server-derived public-only RAG retrieval boundary pending Phase 18 tenant storage.

Phase 16 remains **In Progress**. The complete blocker and completion-gate list is maintained in `docs/phase_16_identity_ownership_contract.md`.

### Security

- Public hosted visitors receive a common/anonymous restricted identity instead of implicit administrator access.
- Public discovery, monitoring, evaluation, review, RAG, document, watchlist, credential, audit, and Vast.ai mutations remain restricted.
- Public compute endpoints use bounded request schemas and per-client limiting.
- Provider and session secrets remain server-side.
- Phase 16 documentation now explicitly requires effective BFF route allowlisting, cookie filtering, actor-based hybrid authorization, strict visibility semantics, concurrency-safe quotas, complete recovery, server-owned consent versions, usable MFA, and tenant knowledge boundaries.

### Backend

- Added API root, process liveness, and database/RAG readiness endpoints.
- Added request IDs, request-duration logging, and safe exception logging.
- Added deterministic demo seeding and RAG-index generation during hosted startup.
- Updated Render to use `/ready` for health checks.
- Enforced market-cache expiration and update-in-place behavior.
- Added PostgreSQL migration/test foundations in CI.

### Frontend

- Made the live demo the primary product entry point.
- Added public-aware navigation, footer, states, badges, responsive behavior, and reduced-motion support.
- Added cold-start retry/readiness flows and shared-demo privacy guidance.
- Converted review and watchlist workflows to read-only hosted demonstrations.
- Protected direct credential, audit, and Vast.ai pages in public mode.
- Clarified financial units and advanced controls.
- Added clickable sources and Markdown copy/download.
- Added Phase 16 authentication/account/thesis/organization foundations.

### Documentation

- Added `docs/phase_16_identity_ownership_contract.md` as the complete Phase 16 implementation and security contract.
- Added `docs/future_phase_contracts.md` with detailed contracts for Phases 17–21.
- Added `docs/agent_execution_guide.md` so future work can use short prompts safely.
- Rebuilt the authoritative development plan around phase contracts and dependency gates.
- Updated current state to separate deployed `main` from branch-only Phase 16 work.
- Revised architecture, deployment, testing, and README to match the contracts and current implementation audit.
- Recorded the remaining Phase 16 blockers instead of presenting foundations as completed production behavior.

## 0.1.0 — Technical MVP and Portfolio Expansion

### Added

- FastAPI and Next.js full-stack MVP.
- SQLAlchemy/Alembic persistence and Docker Compose.
- Curated RAG, market-data adapters, deterministic scoring, structured reports, and Markdown export.
- Optional LLM synthesis with deterministic fallback.
- Discovery, evaluation, review, human-approved RAG ingestion, simulation, watchlists, alerts, options, ML groundwork, and HPC templates.
- Admin/common access-control foundation, encrypted provider credentials, audit logs, and Vast.ai dry-run/manual warm-up.
- Deterministic demo data, example reports, and Vercel/Render/Supabase deployment preparation.

# V1 Phase 18 Execution Plan — Production RAG and Knowledge Storage

Status: **Implemented Foundation (18A–18F complete locally)**

Branch: `agent/v1-phase-18-production-rag`

Base: `main` after completed Phases 16 and 17

This plan is the implementation authority for Phase 18 together with
[`future_phase_contracts.md`](future_phase_contracts.md). It preserves the
Phase 15 public JSON retrieval path until the durable corpus has passed
tenant-isolation, citation, deletion, rollback, and quality gates.

Phase 18 is not complete when its schema exists. Completion requires durable
private objects, worker ingestion, pgvector retrieval, lineage, lifecycle
operations, evaluation, frontend workflows, deployment evidence, and rollback.

---

## 1. Goals and boundaries

Phase 18 will:

- store originals in a private Supabase Storage bucket;
- store source, document, immutable version, chunk, embedding, retrieval, and
  citation metadata in Supabase PostgreSQL;
- use pgvector for durable embeddings and server-filtered ranking;
- run extraction, normalization, chunking, and embedding through Phase 17
  `document.ingest` jobs;
- preserve approval, trust, ownership, organization, version, and deletion
  lineage;
- support private, organization, and approved-public retrieval without
  client-selected tenant filters;
- retain the current local JSON index as a public-demo fallback and rollback
  path until cutover gates pass.

Phase 18 will not:

- auto-approve discovered sources;
- expose storage service-role credentials, private object keys, or public
  bucket URLs;
- accept arbitrary organization scope from a worker or browser;
- run heavy ingestion in the web process;
- train on private tenant content;
- enable real Vast.ai rentals, wallets, signing, custody, or trades.

---

## 2. Starting evidence and compatibility constraints

The current repository has:

- public curated Markdown and `backend/.rag_index.json`;
- `document_sources` for current public-index metadata;
- `organization_knowledge_sources` for Phase 16 metadata-only approved
  organization sources;
- server-derived active organization membership scope;
- Phase 17 jobs, workers, artifacts, idempotency, cancellation, retention,
  and tenant authorization;
- a private BFF boundary that excludes worker-internal APIs.

Compatibility rules:

- do not rename, repurpose, backfill, or delete `document_sources` or
  `organization_knowledge_sources` in the first slices;
- new durable knowledge tables are additive;
- old public retrieval remains authoritative until the Phase 18 shadow and
  cutover gates pass;
- no migration writes production objects or rebuilds embeddings;
- all existing reports, jobs, artifacts, public demo records, and organization
  metadata survive upgrade and downgrade rehearsal.

---

## 3. Target architecture

```text
Browser or approved discovery item
  -> authenticated source/document API
  -> server-derived user or organization scope
  -> private Supabase Storage original
  -> immutable document-version metadata
  -> Phase 17 document.ingest.v1 job
  -> trusted outbound worker
  -> private object read
  -> extraction and normalization
  -> versioned chunks
  -> versioned pgvector embeddings
  -> transactional version activation

Analysis request
  -> server-derived retrieval scope
  -> public approved + owner private + active organization sources
  -> SQL tenant/deletion/current-version filters
  -> pgvector ranking
  -> citation lineage validation
  -> deterministic report

Public demo / rollback
  -> existing curated Markdown and local JSON index
```

The FastAPI control plane owns authorization, state transitions, object-key
derivation, job submission, version activation, and result persistence.
Workers receive scoped job envelopes and runtime credentials, never user
bearer tokens.

---

## 4. Durable data model

### 4.1 `knowledge_sources`

Required fields:

```text
id
owner_user_id
organization_id
visibility
source_type
source_uri
canonical_uri
title
protocol
chain
status
trust_state
approved_by_user_id
approved_at
created_by_user_id
created_at
updated_at
deleted_at
```

Visibility is `public`, `private`, or `organization`.

Rules:

- private creation derives `owner_user_id` from the actor;
- organization creation requires an active owner/admin membership and derives
  `organization_id` server-side;
- public creation and approval require a platform administrator;
- platform administrators do not gain an organization-content bypass;
- only `approved_for_rag` sources may enter trusted retrieval;
- deletion immediately excludes the source and all descendants from
  retrieval.

### 4.2 `knowledge_documents`

Required fields:

```text
id
knowledge_source_id
current_version_id
filename
media_type
status
created_at
updated_at
deleted_at
```

The source owns tenant scope. `current_version_id` is changed only by the
version activation service after ingestion and validation. The first migration
keeps the pointer application-validated to avoid a circular cross-dialect
foreign-key migration; a PostgreSQL constraint may be added after activation
behavior is proven.

### 4.3 `knowledge_document_versions`

Required fields:

```text
id
document_id
version_number
storage_key
checksum
size_bytes
parser_version
chunker_version
embedding_model
embedding_dimensions
active_embedding_profile_id
active_embedding_generation_id
status
created_by_job_id
created_at
superseded_at
deleted_at
```

Versions are immutable after ingestion begins. Re-ingestion creates a new
version. Object keys are opaque, server-derived, and private.

### 4.4 `knowledge_chunks`

Required fields:

```text
id
document_version_id
chunk_index
heading_path
content
content_checksum
token_count
metadata_json
created_at
deleted_at
```

Chunk indexes are unique within a version. Content is not logged or included
in ordinary account exports. Deleted or non-current version chunks cannot be
retrieved.

### 4.5 `knowledge_chunk_embeddings`

Added when the embedding contract is implemented:

```text
id
chunk_id
embedding_profile_id
embedding_generation_id
dimensions
embedding vector
status
created_by_job_id
created_at
deleted_at
```

An embedding is unique by chunk and immutable generation. Multiple completed
generations may use the same model/profile for one version; the document version
stores the exact active generation pointer used by retrieval. pgvector is enabled in
Supabase PostgreSQL. SQLite tests use contract fakes rather than pretending a
JSON value is a production vector.

### 4.6 Retrieval and citation lineage

`knowledge_retrieval_events` store bounded, privacy-safe metadata:

```text
id
request_id
user_id
organization_id
query_hash
filters_json
retrieved_chunk_ids
scores_json
latency_ms
retriever_version
created_at
```

Raw private queries and chunk content are excluded by default.

Report citations persist or embed stable references to:

```text
source_id
document_id
document_version_id
chunk_id
content_checksum
retrieval_event_id
```

Citation validation rejects deleted, superseded, cross-tenant, or checksum-
mismatched lineage before a report is finalized.

---

## 5. Private object storage

The production backend uses a private Supabase Storage bucket. The bucket is
not public and is not addressed directly from browser input.

The storage abstraction must provide:

- create-only upload with explicit content type and size;
- bounded streaming download for workers;
- metadata/head;
- idempotent delete;
- short-lived signed download only after application authorization;
- deterministic error categories;
- dependency injection for tests;
- no secret or private object key in logs.

Server-owned object keys use:

```text
knowledge/{scope_kind}/{scope_id}/sources/{source_id}/documents/{document_id}/versions/{version_id}/original
```

The scope component is derived from the authorized actor and durable source,
never from an arbitrary browser path. Bucket creation and policies are a
deployment operation; Alembic does not mutate Supabase's managed `storage`
schema.

Configuration:

```text
KNOWLEDGE_STORAGE_ENABLED=false
SUPABASE_STORAGE_BUCKET=private-knowledge
SUPABASE_STORAGE_TIMEOUT_SECONDS=20
SUPABASE_URL=<server configuration>
SUPABASE_SERVICE_ROLE_KEY=<server only>
```

Production fails closed when storage is enabled without the required private
bucket configuration and service credential.

---

## 6. Trust and authorization

Source trust states:

```text
discovered
needs_review
approved_for_rag
rejected
archived
```

Operational states:

```text
registered
upload_pending
ingestion_pending
ingesting
ingested
ingestion_failed
deletion_pending
deleted
```

Authorization matrix:

| Scope | Create/manage | Read/retrieve |
| --- | --- | --- |
| Public | platform administrator | all actors, only approved and active |
| Private | owning authenticated user | owning authenticated user |
| Organization | active owner/admin | active owner/admin/member/viewer |

The list and detail paths apply the same scope predicate. An unknown,
unauthorized, deleted, or cross-tenant identifier returns safe `404`.

Worker completion revalidates source/document authorization state. Membership
removal or organization disablement follows the Phase 17 active-job revocation
rules and cannot make completed private content public.

---

## 7. `document.ingest.v1` job contract

Phase 18 registers:

```text
job_type: document.ingest
input_schema_version: document.ingest.v1
result_schema_version: document.ingest.v1
```

Client-visible request input contains only:

```json
{
  "document_version_id": "kver_..."
}
```

The control plane derives owner, organization, visibility, source, document,
storage key, parser, chunker, embedding profile, and result resource context.
The worker cannot replace them.

Result fields are bounded and deterministic:

```json
{
  "document_version_id": "kver_...",
  "content_checksum": "...",
  "chunk_count": 0,
  "embedding_count": 0,
  "parser_version": "...",
  "chunker_version": "...",
  "embedding_model": "..."
}
```

Idempotency is scoped to the immutable document version. Retry must replace or
reconcile the same incomplete version output, never create a second logical
version. Cancellation and terminal failure leave the version honestly marked
and schedule partial chunk/vector cleanup.

The first slice registers and validates this exact contract but keeps
submission and execution disabled. A later slice adds the server-owned
submission path and allowlisted executor.

---

## 8. Ingestion pipeline

The worker pipeline is ordered:

1. claim and revalidate version state;
2. read the authorized private object;
3. verify size, media type, and checksum;
4. extract with an allowlisted parser;
5. normalize text deterministically;
6. detect empty, encrypted, unsupported, or suspicious input;
7. chunk with recorded chunker version;
8. persist chunks for the immutable version;
9. embed with recorded model/version/dimensions;
10. persist vectors beside any previous embedding generation;
11. validate counts, checksums, and tenant lineage;
12. complete through the Phase 17 control plane;
13. atomically activate the validated version.

Initial parser allowlist:

- UTF-8 text and Markdown;
- PDF with bounded page/text extraction;
- HTML with scripts/styles removed and canonical text normalization.

Office formats, OCR, archives, and arbitrary binaries remain unsupported until
separately bounded and tested.

---

## 9. Retrieval and pgvector cutover

Durable retrieval must filter before ranking:

- source not deleted;
- source operational state `ingested`;
- trust state `approved_for_rag`;
- document not deleted;
- version equals document current version;
- chunk and embedding not deleted;
- scope equals approved public, caller private, or caller's active
  organizations;
- embedding model/version equals the active server profile.

The client may request protocol and chain filters, but may not provide owner or
organization authorization filters.

Rollout modes:

```text
local_json
shadow_pgvector
pgvector_primary_with_json_public_fallback
```

Shadow mode records comparison metrics but does not change report context.
Cutover requires zero tenant leakage, citation integrity, deletion behavior,
and quality thresholds.

---

## 10. Re-ingestion, rollback, and re-embedding

Re-ingestion:

- creates the next version number under a document lock;
- uploads a new immutable original;
- runs a new ingestion job;
- leaves the current version active until validation succeeds.

Rollback:

- validates the target version belongs to the same active source/document;
- atomically moves `current_version_id`;
- invalidates retrieval caches;
- records an audit event;
- does not rewrite historical citations.

Re-embedding:

- writes a new embedding generation beside the old;
- supports bounded partial backfill;
- evaluates both generations;
- changes the active embedding profile atomically;
- retains the previous generation for a rollback window;
- deletes obsolete vectors only after approval.

---

## 11. Deletion, tombstones, and retention

Deletion is two-stage:

1. transactionally set source/document/version tombstones and exclude all
   descendants from retrieval;
2. submit bounded cleanup for objects, chunks, vectors, and generated artifacts.

Cleanup is idempotent. Failure remains visible as `deletion_pending` and is
retryable. Audit/citation identifiers and checksums may remain for required
lineage, but deleted content and object keys are not served.

Account and organization deletion integrate with the existing Phase 16/17
lifecycle. Retention dry runs report counts without deleting database rows or
objects.

---

## 12. Migration from local JSON

The public JSON corpus migrates through an explicit, repeatable importer:

1. enumerate committed curated Markdown;
2. create approved public durable sources and documents;
3. upload originals to the private bucket;
4. submit one ingestion job per immutable version;
5. compare durable chunks/citations with the current JSON index;
6. run public retrieval evaluation in shadow mode;
7. enable pgvector primary for approved public data;
8. retain JSON fallback for a defined rollback window;
9. remove runtime authority only after Phase 18 completion gates pass.

The importer uses stable source/document identities and idempotency keys. It
does not silently import discovered, rejected, organization, or private data.

---

## 13. Evaluation and observability

Datasets:

- public protocol questions;
- private owner isolation;
- active/removed organization membership;
- known citations;
- negative/no-answer questions;
- superseded version questions;
- deletion/tombstone questions;
- adversarial organization/filter metadata;
- duplicate/near-duplicate chunks.

Metrics:

- recall@k;
- precision@k;
- citation accuracy and completeness;
- source coverage/diversity;
- no-answer correctness;
- empty retrieval rate;
- duplicate rate;
- stale/superseded retrieval rate;
- tenant leakage rate, required to be zero;
- p50/p95 latency;
- embedding and storage cost.

Evaluation runs with synthetic or curated fixtures, never production customer
content.

---

## 14. API and frontend plan

Planned authenticated APIs:

```text
POST   /api/knowledge/sources
GET    /api/knowledge/sources
GET    /api/knowledge/sources/{source_id}
PATCH  /api/knowledge/sources/{source_id}
DELETE /api/knowledge/sources/{source_id}

POST   /api/knowledge/sources/{source_id}/documents
GET    /api/knowledge/documents/{document_id}
POST   /api/knowledge/documents/{document_id}/versions
POST   /api/knowledge/document-versions/{version_id}/ingest
POST   /api/knowledge/documents/{document_id}/rollback
DELETE /api/knowledge/documents/{document_id}
```

Uploads are size- and media-type bounded and stream to private storage. The
frontend never receives a service-role key or unrestricted object URL.

Frontend workspace:

- source list with scope, trust, status, protocol, and current version;
- upload/version workflow;
- ingestion job progress and failure guidance;
- approval controls only for authorized actors;
- version history and rollback;
- deletion confirmation;
- citation lineage from report to source/version/chunk;
- no private-content flash or cross-tenant counts.

---

## 15. Ordered implementation slices

### Phase 18A — Schema, storage, scope, and job contract

Dependencies: completed Phases 16 and 17.

Implementation: **Complete on the Phase 18 branch.**

Completion gate: **Passed.** Phase 18B may add authenticated API/upload handling
without enabling ingestion, vector retrieval, or a production storage bucket by
default.

Deliver:

- additive source/document/version/chunk models;
- reversible Alembic migration;
- private object-storage protocol, server-owned key builder, in-memory test
  backend, and fail-closed Supabase adapter/configuration;
- server-derived public/private/organization scope services;
- visible-source query and manage checks;
- disabled-by-default `document.ingest.v1` registry contract;
- ownership, organization isolation, configuration, schema, and migration
  tests.

Gate:

- existing Phase 17 data survives upgrade/downgrade/upgrade;
- unauthorized users and non-member platform admins cannot read organization
  sources;
- public source management is admin-only;
- storage keys cannot be caller-selected;
- no upload, executor, vector retrieval, or cutover is enabled.

### Phase 18B — Source/document API and private upload

Dependencies: 18A.

Status: **Complete on the Phase 18 branch.**

Deliver:

- authenticated source/document/version schemas and APIs;
- bounded streaming uploads to the private bucket;
- media-type, size, filename, and checksum validation;
- source approval transitions and audit events;
- object compensation on database failure;
- account/organization lifecycle hooks.

Gate:

- authenticated API isolation tests pass; the existing Phase 16 browser/BFF
  boundary remains unchanged;
- no public bucket/object URL exists;
- failed upload leaves no trusted version;
- only approved sources can become ingestion-pending.

Implementation notes:

- `POST /api/knowledge/sources/{source_id}/documents` and document-version
  uploads read multipart input in bounded chunks, accept only text, Markdown,
  HTML, and PDF media types with matching filenames, validate optional SHA-256
  checksums, and never accept a caller-selected object key;
- uploads return metadata only: no service credential, storage key, public
  object URL, or signed URL reaches a browser response;
- object creation is create-only. A failed database commit triggers a best-effort
  object delete and leaves no document/version record; storage-disabled or
  storage-failed uploads return a sanitized failure before trusted/ingestion
  state can be reached;
- source approval changes and uploads create sanitized audit events. Account
  and organization deletion tombstone their durable knowledge descendants;
  object retention/physical disposal remains the Phase 18G responsibility;
- source approval does not enable ingestion. The exact `document.ingest.v1`
  job contract and executor remain disabled until Phase 18C.

### Phase 18C — Durable ingestion executor

Dependencies: 18B and a trusted worker data/storage access profile.

Status: **Complete locally on the Phase 18 branch.**

Deliver:

- enabled server-owned submission path;
- `document.ingest` executor;
- text/Markdown, PDF, and HTML parser adapters;
- normalization/chunking with explicit versions;
- checksum and idempotent retry behavior;
- cancellation and partial-output cleanup;
- transactional version activation.

Gate:

- ingestion survives worker/API restart;
- retry creates no duplicate version or chunks;
- cancellation/failure never activates partial content;
- web requests do not perform heavy extraction.

Implementation notes:

- only `POST /api/knowledge/document-versions/{version_id}/ingest` may submit
  the exact `document.ingest.v1` job. Generic `/api/jobs` submission remains
  blocked for this job type; source scope, version lineage, result resource,
  and idempotency are derived by the server;
- `DOCUMENT_INGEST_ENABLED=false` remains the default and additionally
  requires jobs, worker API, and private storage to be enabled. The API only
  queues work; extraction always runs through a Phase 17 worker;
- the executor performs bounded private-object verification, UTF-8 text/
  Markdown, HTML-without-script/style, and bounded PDF extraction; it records
  deterministic parser/chunker versions and persists incomplete chunks before
  control-plane completion validates and atomically activates a version;
- retries delete partial chunks and reuse the same immutable version. Failure,
  cancellation, authorization revocation, and lease recovery remove partial
  chunks and never activate them. Embeddings remain zero and explicitly marked
  as not configured until Phase 18D.

### Phase 18D — pgvector embeddings

Dependencies: 18C and selected embedding model/dimensions.

Status: **Complete locally on the Phase 18 branch.**

Deliver:

- PostgreSQL `vector` extension migration;
- embedding generation records and indexes;
- versioned embedding provider contract;
- partial backfill and re-embedding jobs;
- active embedding profile configuration.

Implementation notes:

- `20260727_0018` verifies the PostgreSQL `vector` extension is already
  installed, then adds profile,
  generation, and chunk-embedding records, preserves a portable JSON vector
  representation for SQLite tests, and creates a partial HNSW cosine index on
  PostgreSQL. Downgrade removes only Phase 18D objects and retains the shared
  extension for other database consumers;
- `20260728_0021` adds the exact active-generation pointer and generation-scoped
  embedding uniqueness. Its downgrade deliberately fails closed once multiple
  generations exist for a version/profile; after live activation, feature flags
  return reports to JSON without discarding generation history;
- the only supported provider is `local_deterministic` / `local-hash-384-v1`
  at 384 dimensions. It runs inside the trusted worker and is the only provider
  configuration accepted by settings, so private text is never sent to an
  unapproved external embedding service;
- only the source-scoped `/embed` endpoint can queue `document.embed.v1`.
  Generation output is validated and activated by the Phase 17 control plane;
  incomplete vectors are removed on cancellation, failure, authorization
  revocation, or lease recovery. Old profile rows/generations remain in place
  for a later explicit re-embedding promotion/rollback workflow.

Gate:

- PostgreSQL similarity/index tests pass;
- dimension/model mismatch fails safely;
- same-profile generations remain rollback-capable through an exact active
  generation pointer;
- no private content is sent to an unapproved provider.

### Phase 18E — Tenant-safe durable retrieval and citations

Dependencies: 18D.

Deliver:

- pre-ranking tenant/deletion/current-version SQL filters;
- shadow retriever;
- privacy-safe retrieval events;
- citation lineage and integrity validation;
- report citation rendering.

Gate:

- tenant leakage is zero across adversarial tests;
- removed members and tombstoned data return no chunks;
- citations resolve to the exact checksum/version used;
- JSON remains the report-producing path in shadow mode.

Implementation: **Complete locally on the Phase 18 branch.**

Implementation notes:

- `20260727_0019` adds privacy-safe `knowledge_retrieval_events`; events retain
  a query hash, derived filter summary, returned chunk identifiers, scores,
  latency, and retriever version, but never raw query text or chunk content;
- authenticated `POST /api/knowledge/shadow-retrieval` is disabled by default
  through `KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED=false`. It accepts no
  organization identifier. The backend derives active organization membership
  from the authenticated actor and filters source visibility, approval, source
  status, document/version/chunk tombstones, and the document current-version
  pointer in SQL before pgvector ranking;
- every returned citation carries immutable source/document/version/chunk IDs
  and the exact version and chunk checksums. Invalid lineage is excluded rather
  than rendered. When `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=true`, authenticated
  analysis derives public, caller-owned private, and active-organization scope
  from the server actor before ranking; anonymous analysis is public-only.
  Empty or unavailable durable retrieval falls back to the curated JSON path.

Gate: **Passed locally.** SQLite coverage proves owner/organization/public
isolation, membership removal, tombstone/current-version exclusion, event
privacy, and checksum lineage. PostgreSQL integration exercises the pgvector
ordering path and tenant predicates. Phase 18F may begin; Phase 18 remains
incomplete until all later slices and cutover evidence are complete.

### Phase 18F — Lifecycle operations

Dependencies: 18E.

Deliver:

- re-ingestion;
- version rollback;
- re-embedding promotion/rollback;
- deletion/tombstones;
- object/vector cleanup and retry;
- retention/account/organization integration.

Gate:

- rollback is atomic;
- delete revokes retrieval before external cleanup;
- cleanup dry-run is side-effect free;
- historical citation identifiers remain safe and non-serving.

Implementation: **Complete locally on the Phase 18 branch.**

Implementation notes:

- re-ingestion remains immutable: the existing upload-version endpoint creates
  a new version under a document lock and Phase 18C activation leaves the old
  current version intact until validation succeeds;
- `POST /api/knowledge/documents/{document_id}/rollback` atomically selects a
  ready or superseded version owned by the same managed document, supersedes
  the prior current version, records an audit event, and never rewrites
  historical version identifiers or checksums;
- completed embedding generations can be selected through the manager-only
  promotion endpoint. A prior completed generation remains available for an
  explicit rollback; version-level active-profile metadata keeps the shadow
  retriever bound to the promoted generation rather than a browser-supplied
  profile;
- deletion immediately tombstones source/document/version state and queues one
  idempotent cleanup task per version. `scripts/cleanup_knowledge_tombstones.py`
  supports bounded dry-run and retryable physical removal of private originals,
  chunks, embeddings, and generation outputs. It does no work when storage is
  disabled; failed provider deletes remain retryable and no object key is put
  in the task record.

Gate: **Passed locally.** Lifecycle tests prove atomic rollback, promotion and
rollback of completed generations, retrieval revocation before cleanup,
side-effect-free dry run, idempotent physical cleanup, and retained historical
retrieval-event identifiers. Phase 18G may begin; Phase 18 remains incomplete
until public migration, evaluation, frontend, and cutover gates pass.

### Phase 18G — Public corpus migration and cutover

Dependencies: 18F.

Deliver:

- idempotent curated-Markdown importer;
- shadow comparison against local JSON;
- evaluation datasets and CI/scheduled metrics;
- pgvector-primary feature flag with JSON public fallback;
- deployment and rollback runbook.

Gate:

- quality thresholds pass;
- public reports retain citation coverage;
- no discovered/unapproved source is imported;
- rollback to JSON is tested.

Implementation: **Complete locally on the Phase 18 branch.**

Implementation notes:

- `scripts/import_public_corpus.py` is an explicit operator command. Its dry
  run is side-effect free; `--apply` requires
  `KNOWLEDGE_PUBLIC_CORPUS_IMPORT_ENABLED=true` and private storage. It accepts
  only repository `knowledge_base/**/*.md`, creates stable `ksrc_pub_`,
  `kdoc_pub_`, `kver_pub_`, chunk, and embedding lineage, and repairs/re-activates
  deterministic partial state on rerun, including `A -> B -> A`. It verifies
  Supabase objects by bounded authenticated read when HEAD has no checksum, and
  compensates every object created by a failed whole-corpus transaction. An ID
  collision is repairable only for the expected ownerless public curated lineage;
  private, organization, discovered, mismatched-type, and mismatched-path rows
  fail closed. Discovery, private, and organization sources are not inputs.
- `scripts/evaluate_public_corpus.py` uses the existing curated evaluation
  dataset to compare JSON fallback with an in-transaction durable public
  bootstrap. The bootstrap rolls back and uses in-memory objects, so evaluation
  does not mutate a deployed corpus. Cases define immutable relevant source and
  chunk IDs, include an irrelevant expected-empty query, and do not turn the
  expected protocol into a retrieval filter unless the case explicitly requests
  one. CI runs the top-1 gate and a weekly workflow stores comparison evidence.
- `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` is the default. It requires shadow
  retrieval to be configured. Authenticated analysis queries only approved/current
  public, caller-owned private, and active-organization durable rows; anonymous
  analysis is public-only. It returns to JSON automatically on an empty or
  unavailable durable result. Disabling the flag is an immediate report-path rollback.

Gate: **Passed locally.** The seven checked-in cases, including one expected-empty
query, pass at top-1 with 100% item precision@1, 100% recall, zero citation
issues, and zero tenant leakage in PostgreSQL coverage. This is local quality
evidence, not a production cutover claim. Phase 18H may begin; Phase
18 remains incomplete until frontend, deployment, and production-readiness
gates are complete.

### Phase 18H — Frontend, operations, and completion

Dependencies: 18G.

Deliver:

- complete source/document/version UI;
- report citation lineage UI;
- storage/vector readiness checks and safe metrics;
- production bucket/policy verification;
- full backend, PostgreSQL, frontend, browser, worker, migration, and Compose
  validation;
- documentation truth pass.

Gate:

- every Phase 18 contract completion gate passes;
- runtime filesystem is no longer authoritative for production retrieval;
- public JSON fallback remains available for the documented rollback window;
- Phase 18 may then be marked `Complete`.

Implementation: **Complete locally on the Phase 18 branch.**

Implementation notes:

- `/knowledge` is an authenticated workspace for server-scoped source creation,
  document upload, immutable version upload, ingestion/embedding submission,
  version restore, deletion, and trust-state review. It traverses the existing
  BFF and receives no storage key, signed URL, or credential.
- Reports retain exact durable citation lineage when the guarded public durable
  retriever produced the source. The report UI exposes document-version, chunk,
  and heading identifiers without exposing a private object path.
- `GET /api/knowledge/readiness` is administrator-only and returns safe feature
  flags and aggregate counts. `scripts/check_knowledge_readiness.py` performs a
  non-mutating state check by default; its explicit `--probe-storage` synthetic
  round trip also verifies that the object cannot be served through the public
  bucket route.
- The documented deployment runbook preserves disabled-by-default flags and
  requires deployed private-bucket policy, synthetic two-user, worker, and
  pgvector/cutover evidence before any live activation.

Gate: **Passed locally; external deployment evidence remains pending.** Full
local backend, PostgreSQL, migration, frontend/browser, worker, Compose,
retrieval, cleanup, and recovery checks are required before merging. The code
path can make runtime filesystem retrieval non-authoritative when the guarded
production flag is enabled, while JSON remains available for rollback. Live
Supabase policy and production cutover execution remain Phase 22 validation;
therefore Phase 18 must not be represented as deployed-complete yet.

---

## 16. Migration and rollout safety

Every schema slice runs:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

PostgreSQL validation starts from a Phase 17 schema with representative public,
private, organization, job, artifact, and report records. Migrations are
additive until durable retrieval is proven. No migration performs network I/O,
object deletion, embedding generation, or corpus import.

Rollout order:

1. a database administrator installs `vector`, then `python -m
   scripts.preflight_pgvector` confirms it before application-role migrations;
2. schema with all Phase 18 feature flags disabled;
3. private bucket and policies;
4. upload/source API for a synthetic test tenant;
5. ingestion worker;
6. pgvector shadow retrieval;
7. lifecycle and evaluation;
8. approved public corpus migration;
9. primary retrieval cutover.

Rollback disables durable submission/retrieval flags first, keeps database and
objects intact for diagnosis, and returns analysis to the local JSON public
path.

---

## 17. Validation commands

Backend baseline:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
python -m scripts.cleanup_expired_data --dry-run
python -m scripts.recover_durable_jobs --dry-run
```

PostgreSQL:

```bash
RUN_POSTGRES_INTEGRATION=true python -m pytest -q -m postgres_integration
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run test:bff
npm run test:mfa
npm run test:mfa:routes
npm run build
npm run test:e2e
```

Compose:

```bash
docker compose config
docker compose --profile worker config
docker compose -f docker-compose.production.yml config
```

Slice-specific storage, parser, ingestion, vector, citation, deletion,
evaluation, and browser tests are added before their respective gates close.
No check requires production customer data, a real paid model, or a Vast.ai
rental.

---

## 18. Phase status rule

After Phases 18A–18F, report:

```text
Phase 18 — Implemented Foundation
```

Do not report Phase 18 complete until 18A–18H and all contract completion gates
pass. Phase 22 continues to own custom SMTP, deployed two-user/MFA, legal,
backup/restore, and final launch approval.

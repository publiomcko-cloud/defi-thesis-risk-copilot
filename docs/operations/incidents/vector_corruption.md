# Vector or Retrieval Integrity Failure — `retrieval.vector-corruption`

Owner roles: knowledge owner (primary), platform owner (backup). Communication
authority: assigned incident communications authority. Begin at `SEV2`; raise
to `SEV1` for suspected cross-tenant retrieval or active source corruption.

## Detection

Triggers include retrieval latency/empty-rate alerts, citation integrity
failure, stale generation selection, vector dimension/index mismatch, corrupted
chunk metadata, or evaluation regression. Keep query/source details private.

## Immediate containment

Disable durable primary or shadow retrieval for the affected scope, preserve
the public JSON fallback, halt embedding promotion/re-ingestion, and prevent
the suspect generation from serving new reports. Anonymous analysis stays
public-only.

## Eradication and scope

Validate approved source trust, active document version, chunk content checksum
and heading metadata, embedding dimensions/vector/checksum, active-generation
pointer, and server-derived tenant filters. Do not inspect another tenant's
content to diagnose ranking.

## Recovery and rollback

Rebuild corrupt derived chunks/vectors from the immutable approved version,
then run retrieval/citation and PostgreSQL tenant-isolation checks. Promote only
the verified generation. Rollback selects a previous completed generation or
the JSON fallback; it never reactivates a deleted/superseded source.

## Communications

The communications authority decides whether a report correction is required
after verifying affected citations/outputs. Do not disclose source content,
query text, embedding values, or tenant identity.

## Evidence

Record source/version/generation identifiers, integrity/evaluation result
references, feature-flag decision, safe aggregate impact, and verification
result. Exclude vectors, chunks, object keys, signed URLs, and report text.

## Retrospective

Review importer repair, embedding profile/versioning, rollback path, retrieval
metrics, source approval, and the controlled Phase 18 cutover gate.

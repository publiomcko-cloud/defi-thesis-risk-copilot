from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PHASE17_HEAD = "20260724_0016"


def _alembic(database_path: Path, command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_phase18_upgrade_downgrade_preserves_phase17_and_json_rag_metadata(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "phase18.sqlite"
    _alembic(database_path, "upgrade", PHASE17_HEAD)

    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO document_sources (
            id, protocol, source_type, title, source_url, content_hash,
            ingested_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "source_phase17_preserved",
            "aave",
            "documentation",
            "Existing JSON RAG metadata",
            "https://docs.example.test/aave",
            "a" * 64,
            datetime.now(UTC).isoformat(),
            json.dumps({"index": "local-json"}),
        ),
    )
    connection.commit()
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    tables = _tables(connection)
    assert {
        "knowledge_sources",
        "knowledge_documents",
        "knowledge_document_versions",
        "knowledge_chunks",
        "knowledge_embedding_profiles",
        "knowledge_embedding_generations",
        "knowledge_chunk_embeddings",
    }.issubset(tables)
    assert connection.execute(
        "SELECT title FROM document_sources WHERE id = ?",
        ("source_phase17_preserved",),
    ).fetchone() == ("Existing JSON RAG metadata",)
    assert _indexes(connection, "knowledge_sources") >= {
        "ix_knowledge_sources_owner_visibility_deleted",
        "ix_knowledge_sources_org_visibility_deleted",
        "ix_knowledge_sources_trust_status_deleted",
    }
    assert _indexes(connection, "knowledge_documents") >= {
        "ix_knowledge_documents_source_status_deleted",
    }
    assert frozenset({"document_id", "version_number"}) in _unique_column_sets(
        connection,
        "knowledge_document_versions",
    )
    assert frozenset({"document_version_id", "chunk_index"}) in _unique_column_sets(
        connection,
        "knowledge_chunks",
    )
    assert connection.execute(
        "SELECT model, dimensions FROM knowledge_embedding_profiles WHERE id = ?",
        ("kembprof_local_hash_384_v1",),
    ).fetchone() == ("local-hash-384-v1", 384)
    assert frozenset({"document_version_id", "embedding_profile_id"}) in _unique_column_sets(
        connection,
        "knowledge_embedding_generations",
    )
    assert frozenset({"knowledge_chunk_id", "embedding_profile_id"}) in _unique_column_sets(
        connection,
        "knowledge_chunk_embeddings",
    )
    connection.close()

    _alembic(database_path, "downgrade", PHASE17_HEAD)
    connection = sqlite3.connect(database_path)
    assert not {
        "knowledge_sources",
        "knowledge_documents",
        "knowledge_document_versions",
        "knowledge_chunks",
        "knowledge_embedding_profiles",
        "knowledge_embedding_generations",
        "knowledge_chunk_embeddings",
    } & _tables(connection)
    assert connection.execute(
        "SELECT title FROM document_sources WHERE id = ?",
        ("source_phase17_preserved",),
    ).fetchone() == ("Existing JSON RAG metadata",)
    assert "jobs" in _tables(connection)
    connection.close()

    _alembic(database_path, "upgrade", "head")
    connection = sqlite3.connect(database_path)
    assert "knowledge_sources" in _tables(connection)
    assert connection.execute(
        "SELECT COUNT(*) FROM document_sources WHERE id = ?",
        ("source_phase17_preserved",),
    ).fetchone() == (1,)
    connection.close()


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _unique_column_sets(connection: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    return {
        frozenset(
            row[2]
            for row in connection.execute(f"PRAGMA index_info('{index_name}')")
        )
        for _, index_name, unique, *_ in connection.execute(f"PRAGMA index_list({table})")
        if unique
    }

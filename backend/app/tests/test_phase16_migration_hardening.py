from __future__ import annotations

import os
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


BACKEND_DIR = Path(__file__).resolve().parents[2]


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


def _table_indexes(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def _foreign_keys(connection: sqlite3.Connection, table: str) -> dict[str, tuple[str, str]]:
    return {row[3]: (row[2], row[6]) for row in connection.execute(f"PRAGMA foreign_key_list({table})")}


def test_phase15_seeded_public_resources_survive_identity_hardening(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "phase15.sqlite"
    _alembic(database_path, "upgrade", "20260714_0007")

    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO analysis_requests
        (id, strategy_description, protocols, market_url, manual_inputs_json, analysis_depth, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("analysis_phase15", "Seeded public analysis", "[]", None, "{}", "standard", "2026-07-01"),
    )
    connection.execute(
        """
        INSERT INTO reports
        (id, analysis_request_id, title, risk_rating, summary, report_markdown, report_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "report_phase15",
            "analysis_phase15",
            "Seeded report",
            "Moderate",
            "Seeded summary",
            "# Seeded report",
            json.dumps(
                {
                    "report_id": "report_phase15",
                    "risk_rating": "Moderate",
                    "executive_summary": "Seeded summary",
                    "strategy_description": "Seeded public analysis",
                    "protocols": [],
                    "assumptions": [],
                    "missing_data": [],
                    "sections": [],
                    "sources": [],
                }
            ),
            "2026-07-01",
        ),
    )
    connection.execute(
        """
        INSERT INTO watchlist_items
        (id, item_type, title, protocol, market_identifier, source_url, rules_json, snapshot_json,
         enabled, created_at, last_evaluated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "watch_phase15",
            "protocol",
            "Seeded watchlist",
            "aave",
            None,
            None,
            "{}",
            "{}",
            1,
            "2026-07-01",
            None,
        ),
    )
    connection.commit()
    connection.close()

    _alembic(database_path, "upgrade", "head")

    connection = sqlite3.connect(database_path)
    assert connection.execute(
        "SELECT visibility FROM analysis_requests WHERE id = 'analysis_phase15'"
    ).fetchone() == ("public_demo",)
    assert connection.execute(
        "SELECT title, visibility FROM reports WHERE id = 'report_phase15'"
    ).fetchone() == ("Seeded report", "public_demo")
    assert connection.execute(
        "SELECT title, visibility FROM watchlist_items WHERE id = 'watch_phase15'"
    ).fetchone() == ("Seeded watchlist", "public_demo")

    for table in ("analysis_requests", "reports", "watchlist_items"):
        foreign_keys = _foreign_keys(connection, table)
        assert foreign_keys["owner_user_id"] == ("users", "SET NULL")
        assert foreign_keys["organization_id"] == ("organizations", "SET NULL")
        assert foreign_keys["anonymous_session_id"] == ("anonymous_sessions", "SET NULL")
        assert {
            f"ix_{table}_owner_deleted",
            f"ix_{table}_org_visibility_deleted",
            f"ix_{table}_anonymous_expires",
        }.issubset(_table_indexes(connection, table))

    assert _foreign_keys(connection, "saved_theses")["owner_user_id"] == ("users", "RESTRICT")
    assert _foreign_keys(connection, "consent_records")["user_id"] == ("users", "RESTRICT")
    assert "ix_usage_quotas_subject_action_period_end" in _table_indexes(connection, "usage_quotas")
    assert "ix_organization_memberships_user_org_status" in _table_indexes(
        connection, "organization_memberships"
    )
    connection.close()

    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            report = client.get("/api/reports/report_phase15")
            watchlists = client.get("/api/watchlist/items")
            mutation = client.post(
                "/api/watchlist/items",
                json={"item_type": "market", "title": "Blocked public mutation"},
            )
        assert report.status_code == 200
        assert report.json()["report_id"] == "report_phase15"
        assert watchlists.status_code == 200
        assert [item["id"] for item in watchlists.json()["items"]] == ["watch_phase15"]
        assert mutation.status_code == 403
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    _alembic(database_path, "downgrade", "20260721_0009")
    _alembic(database_path, "upgrade", "head")

    connection = sqlite3.connect(database_path)
    assert connection.execute(
        "SELECT title FROM reports WHERE id = 'report_phase15'"
    ).fetchone() == ("Seeded report",)
    assert connection.execute(
        "SELECT title FROM watchlist_items WHERE id = 'watch_phase15'"
    ).fetchone() == ("Seeded watchlist",)
    connection.close()


def test_identity_hardening_detaches_invalid_nullable_links_without_changing_visibility(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "identity-links.sqlite"
    _alembic(database_path, "upgrade", "20260721_0009")

    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        INSERT INTO analysis_requests
        (id, strategy_description, protocols, market_url, manual_inputs_json, analysis_depth,
         owner_user_id, organization_id, visibility, anonymous_session_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "analysis_orphaned_links",
            "Private legacy analysis",
            "[]",
            None,
            "{}",
            "standard",
            "missing-user",
            "missing-org",
            "private",
            "missing-session",
            "2026-07-01",
        ),
    )
    connection.commit()
    connection.close()

    _alembic(database_path, "upgrade", "head")

    connection = sqlite3.connect(database_path)
    assert connection.execute(
        """
        SELECT owner_user_id, organization_id, visibility, anonymous_session_id
        FROM analysis_requests WHERE id = 'analysis_orphaned_links'
        """
    ).fetchone() == (None, None, "private", None)
    connection.close()

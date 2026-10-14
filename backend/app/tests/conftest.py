from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine as application_engine
from app.db.session import init_db


ISOLATED_TEST_DATABASE = "defi_copilot_test"
ISOLATED_TEST_DATABASE_MARKER = "phase22-pgvector-isolated-test-v1"
CONNECTION_OVERRIDE_PARAMETERS = {
    "database",
    "dbname",
    "host",
    "hostaddr",
    "port",
    "service",
    "servicefile",
    "user",
}
LIBPQ_TARGET_OVERRIDE_ENV = {
    "PGHOST",
    "PGHOSTADDR",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGSERVICE",
    "PGSERVICEFILE",
    "PGOPTIONS",
    "PGLOADBALANCEHOSTS",
    "PGTARGETSESSIONATTRS",
}


def verify_test_database_target() -> None:
    """Fail closed before any test-startup Alembic migration can run."""
    settings = get_settings()
    if settings.app_env.strip().lower() == "production":
        raise RuntimeError("refusing test database migration while APP_ENV=production")

    url = application_engine.url
    if application_engine.dialect.name != "postgresql":
        # Existing local SQLite test workflows, including in-memory tests,
        # remain available. PostgreSQL is the only supported remote backend.
        if application_engine.dialect.name != "sqlite":
            raise RuntimeError("refusing tests against an unsupported or non-isolated database target")
        return

    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("refusing PostgreSQL tests unless DATABASE_URL targets loopback")
    if url.database != ISOLATED_TEST_DATABASE:
        raise RuntimeError("refusing PostgreSQL tests unless DATABASE_URL targets the dedicated test database")
    if CONNECTION_OVERRIDE_PARAMETERS.intersection(url.query):
        raise RuntimeError("refusing PostgreSQL tests with connection overrides")
    if LIBPQ_TARGET_OVERRIDE_ENV.intersection(os.environ):
        raise RuntimeError("refusing PostgreSQL tests with libpq target overrides")
    if os.getenv("PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN") != "true":
        raise RuntimeError("refusing PostgreSQL test migrations without explicit isolated-admin authorization")

    try:
        with application_engine.connect() as connection:
            identity = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "shobj_description(d.oid, 'pg_database') AS isolation_marker, "
                    "r.rolsuper AS is_superuser "
                    "FROM pg_database d CROSS JOIN pg_roles r "
                    "WHERE d.datname = current_database() AND r.rolname = current_user"
                )
            ).one_or_none()
    except Exception:
        # SQLAlchemy/driver exceptions may include a secret-bearing URL.
        raise RuntimeError("refusing PostgreSQL tests because isolated database identity could not be verified") from None

    if (
        identity is None
        or identity.database_name != ISOLATED_TEST_DATABASE
        or identity.isolation_marker != ISOLATED_TEST_DATABASE_MARKER
        or not identity.is_superuser
    ):
        raise RuntimeError("refusing PostgreSQL tests because the connected database is not the authorized isolated test target")


# conftest is imported before collection and before session fixtures, so this
# protects every pytest selection, including a single unrelated test module.
verify_test_database_target()


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    init_db()

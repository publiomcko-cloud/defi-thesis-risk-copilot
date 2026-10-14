from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine as application_engine
from app.db.session import init_db


POSTGRES_TEST_PROFILES = {
    "phase22-pgvector": {
        "authorization": "PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN",
        "app_env": "test",
        "database": "defi_copilot_test",
        "marker": "phase22-pgvector-isolated-test-v1",
    },
    "phase19-exercises": {
        "authorization": "PHASE19_FAILURE_EXERCISE_TEST_ADMIN",
        "app_env": "exercise",
        "database": "defi_copilot_exercises",
        "marker": "phase19-isolated-exercise-test-v1",
    },
}
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

    selected_profiles = [
        (name, profile)
        for name, profile in POSTGRES_TEST_PROFILES.items()
        if os.getenv(profile["authorization"]) == "true"
    ]
    if len(selected_profiles) != 1:
        raise RuntimeError("refusing PostgreSQL tests without exactly one explicit isolated-test profile")
    profile_name, profile = selected_profiles[0]
    if settings.app_env.strip().lower() != profile["app_env"]:
        raise RuntimeError("refusing PostgreSQL tests because APP_ENV does not match the selected isolated-test profile")

    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("refusing PostgreSQL tests unless DATABASE_URL targets loopback")
    if url.database != profile["database"]:
        raise RuntimeError("refusing PostgreSQL tests unless DATABASE_URL targets the database named by its isolated-test profile")
    if CONNECTION_OVERRIDE_PARAMETERS.intersection(url.query):
        raise RuntimeError("refusing PostgreSQL tests with connection overrides")
    if LIBPQ_TARGET_OVERRIDE_ENV.intersection(os.environ):
        raise RuntimeError("refusing PostgreSQL tests with libpq target overrides")
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
        or identity.database_name != profile["database"]
        or identity.isolation_marker != profile["marker"]
        or not identity.is_superuser
    ):
        raise RuntimeError(
            f"refusing PostgreSQL tests because the connected database is not the authorized {profile_name} target"
        )


# conftest is imported before collection and before session fixtures, so this
# protects every pytest selection, including a single unrelated test module.
verify_test_database_target()


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    init_db()

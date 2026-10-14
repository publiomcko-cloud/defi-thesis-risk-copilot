from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from app.db.session import engine as application_engine

pytestmark = pytest.mark.postgres_integration

BACKEND_DIR = Path(__file__).resolve().parents[2]
ISOLATED_TEST_DATABASE = "defi_copilot_test"
ISOLATED_TEST_DATABASE_MARKER = "phase22-pgvector-isolated-test-v1"


def _run_guard_subprocess(
    database_url: str | None = None,
    *,
    app_env: str = "test",
    admin: bool = True,
    phase19_admin: bool = False,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update({"APP_ENV": app_env})
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    environment.pop("PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN", None)
    environment.pop("PHASE19_FAILURE_EXERCISE_TEST_ADMIN", None)
    if admin:
        environment["PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN"] = "true"
    if phase19_admin:
        environment["PHASE19_FAILURE_EXERCISE_TEST_ADMIN"] = "true"
    environment.update(extra_environment or {})
    return subprocess.run(
        [sys.executable, "-c", "from app.tests.conftest import verify_test_database_target; verify_test_database_target()"],
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("database_url", "admin", "message"),
    [
        ("postgresql+psycopg://user:guard-secret@db.example.invalid:5432/defi_copilot_test", True, "loopback"),
        ("postgresql+psycopg://user:guard-secret@127.0.0.1:5432/production", True, "database named by its isolated-test profile"),
        (
            "postgresql+psycopg://user:guard-secret@127.0.0.1:5432/defi_copilot_test?hostaddr=203.0.113.10",
            True,
            "connection overrides",
        ),
        (
            "postgresql+psycopg://user:guard-secret@127.0.0.1:5432/defi_copilot_test?dbname=production",
            True,
            "connection overrides",
        ),
        ("postgresql+psycopg://user:guard-secret@127.0.0.1:5432/defi_copilot_test", False, "exactly one explicit isolated-test profile"),
    ],
)
def test_central_database_guard_rejects_unsafe_postgres_targets_without_leaking_urls(
    database_url: str, admin: bool, message: str
) -> None:
    result = _run_guard_subprocess(database_url, admin=admin)
    assert result.returncode != 0
    assert message in result.stderr
    assert "guard-secret" not in result.stdout + result.stderr


def test_central_database_guard_rejects_libpq_environment_target_override() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql+psycopg://user:guard-secret@127.0.0.1:5432/defi_copilot_test",
            "PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN": "true",
            "PGHOSTADDR": "203.0.113.10",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "from app.tests.conftest import verify_test_database_target; verify_test_database_target()"],
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "libpq target overrides" in result.stderr
    assert "guard-secret" not in result.stdout + result.stderr


def test_phase19_profile_accepts_only_the_marked_exercise_database() -> None:
    database_url = os.getenv("PHASE19_GUARD_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CI must provision the dedicated marked Phase 19 guard test database")
    result = _run_guard_subprocess(
        database_url,
        app_env="exercise",
        admin=False,
        phase19_admin=True,
    )
    assert result.returncode == 0, result.stderr
    assert "guard-secret" not in result.stdout + result.stderr


def test_phase19_profile_rejects_unmarked_database_before_pytest_can_migrate() -> None:
    database_url = os.getenv("PHASE19_GUARD_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CI must provision the dedicated Phase 19 guard test database")

    exercise_engine = create_engine(make_url(database_url))
    admin_engine = create_engine(
        make_url(os.environ["DATABASE_URL"]).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    marker_before = "phase19-isolated-exercise-test-v1"
    revision_before: str | None = None
    try:
        with exercise_engine.connect() as connection:
            identity = connection.execute(
                text(
                    "SELECT current_database(), shobj_description(oid, 'pg_database') "
                    "FROM pg_database WHERE datname = current_database()"
                )
            ).one()
            assert identity == ("defi_copilot_exercises", marker_before)
            migration_state_before = connection.execute(
                text("SELECT to_regclass('alembic_version')")
            ).scalar_one_or_none()
            if migration_state_before is not None:
                revision_before = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()

        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                "COMMENT ON DATABASE defi_copilot_exercises "
                "IS 'phase19-test-marker-must-not-authorize'"
            )
        environment = os.environ.copy()
        environment.update(
            {
                "APP_ENV": "exercise",
                "DATABASE_URL": database_url,
                "PHASE19_FAILURE_EXERCISE_TEST_ADMIN": "true",
            }
        )
        environment.pop("PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN", None)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "app/tests/test_access_control.py"],
            cwd=BACKEND_DIR,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "not the authorized phase19-exercises target" in result.stderr
        assert "guard-secret" not in result.stdout + result.stderr
        with exercise_engine.connect() as connection:
            migration_state_after = connection.execute(
                text("SELECT to_regclass('alembic_version')")
            ).scalar_one_or_none()
            assert migration_state_after == migration_state_before
            if migration_state_before is not None:
                revision_after = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                assert revision_after == revision_before
    finally:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                "COMMENT ON DATABASE defi_copilot_exercises "
                "IS 'phase19-isolated-exercise-test-v1'"
            )
        exercise_engine.dispose()
        admin_engine.dispose()


@pytest.mark.parametrize(
    ("database_url", "app_env", "phase19_admin", "extra_environment", "message"),
    [
        (
            "postgresql+psycopg://postgres:guard-secret@127.0.0.1:5432/defi_copilot_test",
            "exercise",
            True,
            {},
            "database named by its isolated-test profile",
        ),
        (
            None,
            "production",
            True,
            {},
            "APP_ENV=production",
        ),
        (
            None,
            "exercise",
            True,
            {"PGHOSTADDR": "203.0.113.10"},
            "libpq target overrides",
        ),
    ],
)
def test_phase19_profile_rejects_wrong_database_production_and_forwarded_targets(
    database_url: str | None,
    app_env: str,
    phase19_admin: bool,
    extra_environment: dict[str, str],
    message: str,
) -> None:
    target = database_url or os.getenv("PHASE19_GUARD_TEST_DATABASE_URL")
    if target is None:
        pytest.skip("CI must provision the dedicated Phase 19 guard test database")
    result = _run_guard_subprocess(
        target,
        app_env=app_env,
        admin=False,
        phase19_admin=phase19_admin,
        extra_environment=extra_environment,
    )
    assert result.returncode != 0
    assert message in result.stderr
    assert "guard-secret" not in result.stdout + result.stderr


def test_postgres_guard_rejects_both_test_profiles_enabled() -> None:
    result = _run_guard_subprocess(
        "postgresql+psycopg://user:guard-secret@127.0.0.1:5432/defi_copilot_test",
        admin=True,
        phase19_admin=True,
    )
    assert result.returncode != 0
    assert "exactly one explicit isolated-test profile" in result.stderr
    assert "guard-secret" not in result.stdout + result.stderr


def test_unrelated_pytest_selection_rejects_production_before_database_creation(tmp_path: Path) -> None:
    database_path = tmp_path / "must-not-be-created.sqlite"
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "production",
            "DATABASE_URL": f"sqlite:///{database_path}",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "app/tests/test_access_control.py"],
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "APP_ENV=production" in result.stderr
    assert not database_path.exists()


@pytest.mark.skipif(application_engine.dialect.name != "postgresql", reason="requires the isolated PostgreSQL test database")
def test_wrong_database_marker_rejects_unrelated_selection_without_migration_side_effects() -> None:
    with application_engine.connect() as connection:
        revision_before = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        connection.exec_driver_sql("COMMENT ON DATABASE defi_copilot_test IS 'not-the-authorized-test-database'")
        connection.commit()
    try:
        environment = os.environ.copy()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "app/tests/test_access_control.py"],
            cwd=BACKEND_DIR,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "not the authorized phase22-pgvector target" in result.stderr
        with application_engine.connect() as connection:
            revision_after = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision_after == revision_before
    finally:
        with application_engine.connect() as connection:
            connection.exec_driver_sql(
                "COMMENT ON DATABASE defi_copilot_test IS 'phase22-pgvector-isolated-test-v1'"
            )
            connection.commit()


@pytest.fixture
def migration_sandbox(request: pytest.FixtureRequest) -> dict[str, object]:
    """Create a disposable local database and a non-superuser migration role."""
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 22 pgvector migration tests require RUN_POSTGRES_INTEGRATION=true")
    if os.getenv("PHASE22_PGVECTOR_MIGRATION_TEST_ADMIN") != "true":
        pytest.skip("Phase 22 migration-role tests require the explicit isolated-admin opt-in")

    configured_url = os.getenv("DATABASE_URL", "")
    if not configured_url:
        pytest.skip("Phase 22 pgvector migration tests require an isolated PostgreSQL DATABASE_URL")
    admin_url = make_url(configured_url).set(drivername="postgresql+psycopg")
    if admin_url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.skip("Phase 22 pgvector migration tests only create databases on loopback PostgreSQL")

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    suffix = uuid4().hex[:12]
    role_name = f"p22_vector_{suffix}"
    database_name = f"p22_vector_{suffix}"
    role_password = uuid4().hex
    admin_role = None
    role_created = False
    database_created = False
    target_admin_engine = None
    migrator_engine = None
    try:
        with admin_engine.connect() as connection:
            database_facts = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "shobj_description(d.oid, 'pg_database') AS isolation_marker "
                    "FROM pg_database d WHERE d.datname = current_database()"
                )
            ).one()
        assert database_facts.database_name == ISOLATED_TEST_DATABASE, (
            "refusing to mutate a database other than the dedicated Phase 22 test database"
        )
        assert database_facts.isolation_marker == ISOLATED_TEST_DATABASE_MARKER, (
            "refusing to mutate a PostgreSQL cluster without the explicit isolated-test marker"
        )

        with admin_engine.connect() as connection:
            admin_role = connection.execute(
                text(
                    "SELECT current_user, r.rolsuper "
                    "FROM pg_roles r WHERE r.rolname = current_user"
                )
            ).one()
        if not admin_role.rolsuper:
            pytest.skip("The isolated loopback PostgreSQL fixture must provide a superuser administrator")

        quote_identifier = admin_engine.dialect.identifier_preparer.quote_identifier
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                f"CREATE ROLE {quote_identifier(role_name)} LOGIN "
                f"PASSWORD '{role_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
            )
            role_created = True
            connection.exec_driver_sql(
                f"CREATE DATABASE {quote_identifier(database_name)} "
                f"OWNER {quote_identifier(admin_role.current_user)} TEMPLATE template0"
            )
            database_created = True

        target_admin_url = admin_url.set(database=database_name)
        target_admin_engine = create_engine(target_admin_url, isolation_level="AUTOCOMMIT")
        case = getattr(request, "param", "extensions")
        extension_schema = {
            "public": "public",
            "extensions": "extensions",
            "extensions_without_usage": "extensions",
            "extensions_without_type_usage": "extensions",
            "quoted_schema": 'vector schema "quoted',
            "missing": None,
            "missing_btree_gist": "public",
            "schema_conflict": "public",
        }[case]
        target_quote = target_admin_engine.dialect.identifier_preparer.quote_identifier
        with target_admin_engine.connect() as connection:
            connection.exec_driver_sql(
                f"CREATE SCHEMA app AUTHORIZATION {quote_identifier(role_name)}"
            )
            connection.exec_driver_sql(
                f"ALTER ROLE {quote_identifier(role_name)} IN DATABASE "
                f"{quote_identifier(database_name)} SET search_path TO app"
            )
            connection.exec_driver_sql(
                f"GRANT CONNECT ON DATABASE {quote_identifier(database_name)} "
                f"TO {quote_identifier(role_name)}"
            )
            # Migration 20260821_0026 contains CREATE EXTENSION IF NOT EXISTS
            # btree_gist. Provision that separate prerequisite as the fixture
            # administrator so the migration role remains unable to install extensions.
            if case != "missing_btree_gist":
                connection.exec_driver_sql("CREATE EXTENSION btree_gist")
            if extension_schema is not None:
                if extension_schema != "public":
                    connection.exec_driver_sql(
                        f"CREATE SCHEMA {target_quote(extension_schema)}"
                    )
                connection.exec_driver_sql(
                    f"CREATE EXTENSION vector WITH SCHEMA {target_quote(extension_schema)}"
                )
                if case != "extensions_without_usage":
                    connection.exec_driver_sql(
                        f"GRANT USAGE ON SCHEMA {target_quote(extension_schema)} "
                        f"TO {quote_identifier(role_name)}"
                    )
                if case == "extensions_without_type_usage":
                    connection.exec_driver_sql(
                        f"REVOKE USAGE ON TYPE {target_quote(extension_schema)}.vector "
                        f"FROM PUBLIC, {quote_identifier(role_name)}"
                    )

        migrator_url: URL = admin_url.set(
            username=role_name,
            password=role_password,
            database=database_name,
        )
        migrator_engine = create_engine(migrator_url)
        with migrator_engine.connect() as connection:
            role_facts = connection.execute(
                text(
                    "SELECT current_setting('search_path') AS search_path, "
                    "r.rolsuper, r.rolcreatedb, (d.datdba = r.oid) AS database_owner "
                    "FROM pg_roles r CROSS JOIN pg_database d "
                    "WHERE r.rolname = current_user AND d.datname = current_database()"
                )
            ).one()
        assert role_facts.search_path == "app"
        assert not role_facts.rolsuper
        assert not role_facts.rolcreatedb
        assert not role_facts.database_owner

        sandbox = {
            "case": case,
            "database": database_name,
            "extension_schema": extension_schema,
            "migrator_engine": migrator_engine,
            "migrator_url": migrator_url,
        }
        base_revision = _upgrade(sandbox, "20260727_0017")
        assert base_revision.returncode == 0, "\n".join(
            line
            for line in base_revision.stderr.splitlines()
            if "Running upgrade" in line
        )
        yield sandbox
    finally:
        if migrator_engine is not None:
            migrator_engine.dispose()
        if target_admin_engine is not None:
            target_admin_engine.dispose()
        if database_created:
            with admin_engine.connect() as connection:
                connection.exec_driver_sql(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (database_name,),
                )
                connection.exec_driver_sql(
                    f"DROP DATABASE IF EXISTS "
                    f"{admin_engine.dialect.identifier_preparer.quote_identifier(database_name)}"
                )
        if role_created:
            with admin_engine.connect() as connection:
                connection.exec_driver_sql(
                    f"DROP ROLE IF EXISTS "
                    f"{admin_engine.dialect.identifier_preparer.quote_identifier(role_name)}"
                )
        admin_engine.dispose()


def _upgrade(sandbox: dict[str, object], revision: str = "head") -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": sandbox["migrator_url"].render_as_string(hide_password=False),
            "APP_ENV": "test",
            "RUN_POSTGRES_INTEGRATION": "true",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_failed_migration_left_no_phase18_artifacts(
    sandbox: dict[str, object],
) -> None:
    engine = sandbox["migrator_engine"]
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM app.alembic_version")
        ).scalar_one()
        artifacts = connection.execute(
            text(
                "SELECT to_regclass('app.knowledge_embedding_profiles'), "
                "to_regclass('app.knowledge_embedding_generations'), "
                "to_regclass('app.knowledge_chunk_embeddings')"
            )
        ).one()
    assert version == "20260727_0017"
    assert artifacts == (None, None, None)


@pytest.mark.parametrize(
    "migration_sandbox",
    ["public", "extensions", "quoted_schema"],
    indirect=True,
)
def test_pgvector_schema_layout_migrates_to_head_and_hnsw_is_usable(
    migration_sandbox: dict[str, object],
) -> None:
    result = _upgrade(migration_sandbox)
    assert result.returncode == 0, "\n".join(
        line for line in result.stderr.splitlines() if "Running upgrade" in line
    )

    engine = migration_sandbox["migrator_engine"]
    extension_schema = migration_sandbox["extension_schema"]
    expected_head = ScriptDirectory.from_config(
        Config(str(BACKEND_DIR / "alembic.ini"))
    ).get_current_head()
    with engine.connect() as connection:
        assert connection.execute(text("SHOW search_path")).scalar_one() == "app"
        assert connection.execute(
            text("SELECT version_num FROM app.alembic_version")
        ).scalar_one() == expected_head

        vector_type = connection.execute(
            text(
                "SELECT typ.typname, typns.nspname, att.atttypmod "
                "FROM pg_attribute att "
                "JOIN pg_class tbl ON tbl.oid = att.attrelid "
                "JOIN pg_namespace tblns ON tblns.oid = tbl.relnamespace "
                "JOIN pg_type typ ON typ.oid = att.atttypid "
                "JOIN pg_namespace typns ON typns.oid = typ.typnamespace "
                "WHERE tblns.nspname = 'app' "
                "AND tbl.relname = 'knowledge_chunk_embeddings' "
                "AND att.attname = 'embedding_vector' AND att.attnum > 0"
            )
        ).one()
        assert vector_type.typname == "vector"
        assert vector_type.nspname == extension_schema
        assert vector_type.atttypmod == 384

        index_facts = connection.execute(
            text(
                "SELECT am.amname, opc.opcname, opcns.nspname "
                "FROM pg_index idx "
                "JOIN pg_class index_class ON index_class.oid = idx.indexrelid "
                "JOIN pg_namespace index_ns ON index_ns.oid = index_class.relnamespace "
                "JOIN pg_am am ON am.oid = index_class.relam "
                "JOIN pg_opclass opc ON opc.oid = idx.indclass[0] "
                "JOIN pg_namespace opcns ON opcns.oid = opc.opcnamespace "
                "WHERE index_ns.nspname = 'app' "
                "AND index_class.relname = 'ix_knowledge_chunk_embeddings_vector_hnsw'"
            )
        ).one()
        assert index_facts == ("hnsw", "vector_cosine_ops", extension_schema)

        quoted_schema = engine.dialect.identifier_preparer.quote(extension_schema)
        vector_value = "[" + ",".join(["1"] + ["0"] * 383) + "]"
        distance = connection.execute(
            text(
                f"SELECT CAST(:value AS {quoted_schema}.vector) "
                f"OPERATOR({quoted_schema}.<=>) "
                f"CAST(:value AS {quoted_schema}.vector)"
            ),
            {"value": vector_value},
        ).scalar_one()
        assert distance == 0

        connection.execute(text("SET enable_seqscan = off"))
        plan = connection.execute(
            text(
                "EXPLAIN (COSTS OFF) SELECT embedding_vector "
                "FROM app.knowledge_chunk_embeddings "
                "WHERE status = 'completed' AND deleted_at IS NULL "
                f"ORDER BY embedding_vector OPERATOR({quoted_schema}.<=>) "
                f"CAST(:value AS {quoted_schema}.vector) LIMIT 1"
            ),
            {"value": vector_value},
        ).scalars().all()
        assert any("ix_knowledge_chunk_embeddings_vector_hnsw" in line for line in plan)


@pytest.mark.parametrize(
    ("migration_sandbox", "expected_error"),
    [
        ("missing", "pgvector extension is not installed"),
        ("extensions_without_usage", "pgvector extension schema is not accessible"),
        ("extensions_without_type_usage", "pgvector vector type is not accessible"),
    ],
    indirect=["migration_sandbox"],
)
def test_pgvector_missing_prerequisites_fail_closed_without_partial_artifacts(
    migration_sandbox: dict[str, object], expected_error: str,
) -> None:
    result = _upgrade(migration_sandbox)
    assert result.returncode != 0
    assert expected_error in result.stderr
    _assert_failed_migration_left_no_phase18_artifacts(migration_sandbox)

    if migration_sandbox["case"] == "missing":
        engine = migration_sandbox["migrator_engine"]
        from sqlalchemy.exc import DBAPIError

        with engine.connect() as connection:
            with pytest.raises(DBAPIError) as error:
                connection.execute(text("CREATE EXTENSION vector"))
            assert getattr(error.value.orig, "sqlstate", None) == "42501"
            connection.rollback()


@pytest.mark.parametrize("migration_sandbox", ["schema_conflict"], indirect=True)
def test_failed_phase18_ddl_rolls_back_every_partial_artifact(
    migration_sandbox: dict[str, object],
) -> None:
    engine = migration_sandbox["migrator_engine"]
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE app.knowledge_embedding_generations (fixture_conflict integer)")
        )

    result = _upgrade(migration_sandbox, "20260727_0018")
    assert result.returncode != 0
    assert "knowledge_embedding_generations" in result.stderr
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM app.alembic_version")
        ).scalar_one()
        artifacts = connection.execute(
            text(
                "SELECT to_regclass('app.knowledge_embedding_profiles'), "
                "to_regclass('app.knowledge_chunk_embeddings')"
            )
        ).one()
    assert version == "20260727_0017"
    assert artifacts == (None, None)


@pytest.mark.parametrize("migration_sandbox", ["missing_btree_gist"], indirect=True)
def test_btree_gist_must_be_provisioned_before_the_least_privilege_upgrade(
    migration_sandbox: dict[str, object],
) -> None:
    result = _upgrade(migration_sandbox)
    assert result.returncode != 0
    assert "btree_gist" in result.stderr
    assert any(
        message in result.stderr.lower()
        for message in ("permission denied", "must be superuser", "must be owner")
    )

    engine = migration_sandbox["migrator_engine"]
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM app.alembic_version")
        ).scalar_one()
        artifacts = connection.execute(
            text(
                "SELECT to_regclass('app.knowledge_embedding_profiles'), "
                "to_regclass('app.knowledge_embedding_generations'), "
                "to_regclass('app.knowledge_chunk_embeddings'), "
                "to_regclass('app.plan_versions'), "
                "to_regclass('app.plan_entitlements'), "
                "to_regclass('app.entitlement_assignments'), "
                "to_regclass('app.non_billable_usage_events')"
            )
        ).one()
    assert version == "20260727_0017"
    assert artifacts == (None, None, None, None, None, None, None)

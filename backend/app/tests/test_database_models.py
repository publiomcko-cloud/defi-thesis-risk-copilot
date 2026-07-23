from sqlalchemy import inspect

from app.db.session import engine, init_db
from app.db.session import normalize_database_url


def test_initial_persistence_tables_exist() -> None:
    init_db()
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())

    assert {
        "analysis_requests",
        "reports",
        "document_sources",
        "market_data_cache",
        "organization_knowledge_sources",
    }.issubset(table_names)


def test_normalize_database_url_handles_supabase_pooler_schema_param() -> None:
    url = normalize_database_url(
        "postgresql://postgres.example:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require&schema=public"
    )

    assert url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in url
    assert "schema=" not in url
    assert "secret" in url

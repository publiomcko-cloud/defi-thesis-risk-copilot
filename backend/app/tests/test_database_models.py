from sqlalchemy import inspect

from app.db.session import engine, init_db


def test_initial_persistence_tables_exist() -> None:
    init_db()
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())

    assert {
        "analysis_requests",
        "reports",
        "document_sources",
        "market_data_cache",
    }.issubset(table_names)

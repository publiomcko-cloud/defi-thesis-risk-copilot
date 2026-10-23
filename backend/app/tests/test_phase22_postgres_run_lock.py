from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine
from app.research_copilot.execution import try_acquire_execution_lock


pytestmark = pytest.mark.postgres_integration


def test_research_execution_lock_is_transaction_scoped_across_postgres_sessions() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("F1 PostgreSQL recovery-lock test requires RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("F1 recovery-lock test requires a PostgreSQL DATABASE_URL")
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    run_id = f"analysis_{uuid4().hex}"
    first, second = Session(), Session()
    try:
        assert try_acquire_execution_lock(first, run_id) is True
        assert try_acquire_execution_lock(second, run_id) is False
        first.commit()
        assert try_acquire_execution_lock(second, run_id) is True
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()
        engine.dispose()

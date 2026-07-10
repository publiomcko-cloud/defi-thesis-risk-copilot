import pytest

from app.db.session import init_db


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    init_db()

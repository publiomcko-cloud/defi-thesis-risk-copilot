"""Fail-closed pgvector deployment preflight.

Run this with the application migration connection before ``alembic upgrade
head``. It only verifies the extension; it never attempts to install it.
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.db.session import create_database_engine


def main() -> int:
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        print("pgvector preflight skipped: DATABASE_URL is not PostgreSQL")
        return 0
    with engine.connect() as connection:
        installed = bool(
            connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar()
        )
    if not installed:
        print(
            "pgvector preflight failed: extension 'vector' is not installed. "
            "Have a database administrator install it before running Alembic.",
            file=sys.stderr,
        )
        return 1
    print("pgvector preflight passed: extension 'vector' is installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

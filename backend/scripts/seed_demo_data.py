import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.session import SessionLocal, engine, init_db
from app.demo.seed_data import seed_demo_data


def main() -> int:
    os.chdir(BACKEND_DIR)
    init_db()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_demo_data(db)
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

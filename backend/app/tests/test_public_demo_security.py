from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.public_demo import reset_public_rate_limits
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def public_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("VAST_ENABLED", "false")
    monkeypatch.setenv("VAST_DRY_RUN", "true")
    get_settings.cache_clear()
    reset_public_rate_limits()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        reset_public_rate_limits()


def test_public_visitor_is_common_not_admin(public_client) -> None:
    response = public_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["role"] == "common"
    assert response.json()["id"] == "public_demo_user"


def test_public_demo_blocks_admin_and_state_changing_routes(public_client) -> None:
    requests = [
        public_client.get("/api/admin/provider-credentials"),
        public_client.post("/api/demo/seed"),
        public_client.post("/api/monitoring/run", json={}),
        public_client.post("/api/documents/ingest", json={"protocol": "pendle"}),
        public_client.post("/api/discovery/run", json={}),
        public_client.post(
            "/api/watchlist/items",
            json={"item_type": "strategy", "title": "Blocked public watch"},
        ),
        public_client.post("/api/evaluation/discovered-items/missing/evaluate"),
    ]

    assert all(response.status_code == 403 for response in requests)


def test_public_compute_endpoints_remain_available(public_client) -> None:
    simulation = public_client.post(
        "/api/simulation/run",
        json={
            "strategy_description": "Synthetic public demo simulation",
            "protocols": ["pendle", "morpho"],
            "implied_apy": 0.12,
            "borrow_apy": 0.05,
            "ltv": 0.5,
            "lltv": 0.86,
            "liquidity_usd": 1_000_000,
            "pt_price": 0.95,
        },
    )
    options = public_client.post(
        "/api/options/analyze",
        json={
            "option_type": "call",
            "underlying_asset": "ETH",
            "underlying_price": 3000,
            "strike_price": 3200,
            "premium": 150,
            "scenario_prices": [2800, 3200, 3500],
        },
    )

    assert simulation.status_code == 200
    assert options.status_code == 200


def test_public_compute_rate_limit_returns_429(public_client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.public_demo.get_settings",
        lambda: SimpleNamespace(
            public_demo_mode=True,
            public_compute_rate_limit_per_minute=1,
        ),
    )
    reset_public_rate_limits()

    payload = {
        "option_type": "call",
        "underlying_asset": "ETH",
        "underlying_price": 3000,
        "strike_price": 3200,
        "premium": 150,
    }
    first = public_client.post("/api/options/analyze", json=payload)
    second = public_client.post("/api/options/analyze", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"

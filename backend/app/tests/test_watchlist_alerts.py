from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.alert_event import AlertEventModel
from app.models.watchlist_item import WatchlistItemModel


def test_watchlist_item_creation_and_manual_rule_evaluation() -> None:
    _reset_watchlist_state()

    with TestClient(app) as client:
        created = client.post(
            "/api/watchlist/items",
            json={
                "item_type": "strategy",
                "title": "Pendle Morpho spread watch",
                "protocol": "pendle",
                "rules": {
                    "borrow_apy_above_threshold": 0.08,
                    "net_spread_below_threshold": 0.02,
                    "liquidity_below_threshold": 500000,
                },
                "snapshot": {
                    "borrow_apy": 0.1,
                    "net_spread_apy": 0.01,
                    "liquidity_usd": 250000,
                },
            },
        )
        item_id = created.json()["item"]["id"]
        evaluated = client.post(f"/api/watchlist/items/{item_id}/evaluate")

    assert created.status_code == 200
    assert evaluated.status_code == 200
    payload = evaluated.json()
    assert payload["status"] == "completed"
    assert set(payload["evaluated_rules"]) == {
        "borrow_apy_above_threshold",
        "net_spread_below_threshold",
        "liquidity_below_threshold",
    }
    assert len(payload["created_alerts"]) == 3
    assert all(alert["status"] == "open" for alert in payload["created_alerts"])
    assert all("trade instruction" in alert["message"] for alert in payload["created_alerts"])


def test_alert_events_can_be_listed_and_acknowledged() -> None:
    _reset_watchlist_state()

    with TestClient(app) as client:
        item = client.post(
            "/api/watchlist/items",
            json={
                "item_type": "market",
                "title": "Morpho borrow watch",
                "protocol": "morpho",
                "rules": {"borrow_apy_above_threshold": 0.05},
                "snapshot": {"borrow_apy": 0.07},
            },
        ).json()["item"]
        client.post(f"/api/watchlist/items/{item['id']}/evaluate")
        alerts = client.get("/api/watchlist/alerts?status=open").json()["items"]
        response = client.patch(
            f"/api/watchlist/alerts/{alerts[0]['id']}",
            json={"status": "acknowledged"},
        )

    assert alerts
    assert response.status_code == 200
    assert response.json()["alert"]["status"] == "acknowledged"


def test_repeated_watchlist_evaluation_does_not_duplicate_open_alerts() -> None:
    _reset_watchlist_state()

    with TestClient(app) as client:
        item = client.post(
            "/api/watchlist/items",
            json={
                "item_type": "market",
                "title": "Duplicate prevention watch",
                "rules": {"borrow_apy_above_threshold": 0.05},
                "snapshot": {"borrow_apy": 0.07},
            },
        ).json()["item"]
        first = client.post(f"/api/watchlist/items/{item['id']}/evaluate").json()
        second = client.post(f"/api/watchlist/items/{item['id']}/evaluate").json()
        alerts = client.get("/api/watchlist/alerts?status=open").json()["items"]

    assert len(first["created_alerts"]) == 1
    assert second["created_alerts"] == []
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "borrow_apy_above_threshold"


def test_watchlist_item_snapshot_and_rules_can_be_updated() -> None:
    _reset_watchlist_state()

    with TestClient(app) as client:
        item = client.post(
            "/api/watchlist/items",
            json={
                "item_type": "strategy",
                "title": "Mutable watch",
                "rules": {"borrow_apy_above_threshold": 0.08},
                "snapshot": {"borrow_apy": 0.04},
            },
        ).json()["item"]
        response = client.patch(
            f"/api/watchlist/items/{item['id']}",
            json={
                "rules": {"borrow_apy_above_threshold": 0.05},
                "snapshot": {"borrow_apy": 0.07},
            },
        )
        evaluated = client.post(f"/api/watchlist/items/{item['id']}/evaluate").json()

    assert response.status_code == 200
    assert response.json()["item"]["rules"]["borrow_apy_above_threshold"] == 0.05
    assert len(evaluated["created_alerts"]) == 1


def test_watchlist_rules_do_not_create_alerts_when_not_triggered() -> None:
    _reset_watchlist_state()

    with TestClient(app) as client:
        item = client.post(
            "/api/watchlist/items",
            json={
                "item_type": "strategy",
                "title": "Quiet spread watch",
                "rules": {
                    "borrow_apy_above_threshold": 0.1,
                    "net_spread_below_threshold": 0.01,
                },
                "snapshot": {
                    "borrow_apy": 0.04,
                    "net_spread_apy": 0.03,
                },
            },
        ).json()["item"]
        response = client.post(f"/api/watchlist/items/{item['id']}/evaluate")

    assert response.status_code == 200
    assert response.json()["created_alerts"] == []
    assert set(response.json()["evaluated_rules"]) == {
        "borrow_apy_above_threshold",
        "net_spread_below_threshold",
    }


def _reset_watchlist_state() -> None:
    with SessionLocal() as db:
        db.execute(delete(AlertEventModel))
        db.execute(delete(WatchlistItemModel))
        db.commit()

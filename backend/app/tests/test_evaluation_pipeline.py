from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.report import ReportModel
from app.models.review_item import ReviewItemModel
from app.models.source_watch import SourceWatchModel


def test_discovered_item_can_be_evaluated_and_queued_for_review() -> None:
    _reset_evaluation_test_state()
    discovered_item_id = _create_pendle_discovered_item()

    with TestClient(app) as client:
        response = client.post(
            f"/api/evaluation/discovered-items/{discovered_item_id}/evaluate"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["evaluation_result"]["risk_summary"]
    assert payload["evaluation_result"]["missing_data"]
    assert payload["review_item"]["status"] == "needs_review"
    assert payload["review_item"]["prepared_for_rag"] is False
    assert payload["review_item"]["discovered_item"]["id"] == discovered_item_id

    with SessionLocal() as db:
        report = db.get(ReportModel, payload["evaluation_result"]["report_id"])
        assert report is not None
        assert report.report_json["report_id"] == payload["evaluation_result"]["report_id"]

    with TestClient(app) as client:
        report_response = client.get(
            f"/api/reports/{payload['evaluation_result']['report_id']}"
        )

    assert report_response.status_code == 200


def test_review_status_update_prepares_but_does_not_ingest_for_rag() -> None:
    _reset_evaluation_test_state()
    discovered_item_id = _create_pendle_discovered_item()

    with TestClient(app) as client:
        evaluation = client.post(
            f"/api/evaluation/discovered-items/{discovered_item_id}/evaluate"
        ).json()
        review_item_id = evaluation["review_item"]["id"]
        response = client.patch(
            f"/api/evaluation/review-items/{review_item_id}",
            json={
                "status": "approved_for_rag",
                "reviewer_notes": "Looks useful, prepare only.",
            },
        )

    assert response.status_code == 200
    review_item = response.json()["review_item"]
    assert review_item["status"] == "approved_for_rag"
    assert review_item["prepared_for_rag"] is True
    assert review_item["reviewer_notes"] == "Looks useful, prepare only."

    with SessionLocal() as db:
        discovered = db.get(DiscoveredItemModel, discovered_item_id)
        assert discovered is not None
        assert discovered.status == "approved_for_rag"


def test_review_items_endpoint_lists_evaluated_items() -> None:
    _reset_evaluation_test_state()
    discovered_item_id = _create_pendle_discovered_item()

    with TestClient(app) as client:
        client.post(f"/api/evaluation/discovered-items/{discovered_item_id}/evaluate")
        response = client.get("/api/evaluation/review-items?status=needs_review")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["discovered_item_id"] == discovered_item_id
    assert "human review is required" in payload["items"][0]["evaluation_result"]["risk_summary"]


def test_evaluating_missing_discovered_item_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post("/api/evaluation/discovered-items/missing/evaluate")

    assert response.status_code == 404


def _create_pendle_discovered_item() -> str:
    with TestClient(app) as client:
        client.post("/api/monitoring/run", json={"source": "pendle"})

    with SessionLocal() as db:
        item = db.execute(
            select(DiscoveredItemModel).where(DiscoveredItemModel.source == "pendle")
        ).scalars().first()
        assert item is not None
        return item.id


def _reset_evaluation_test_state() -> None:
    with SessionLocal() as db:
        db.execute(delete(ReviewItemModel))
        db.execute(delete(EvaluationResultModel))
        db.execute(delete(DiscoveredItemModel))
        db.execute(
            delete(SourceWatchModel).where(SourceWatchModel.id == "watch_test_failure")
        )
        db.commit()

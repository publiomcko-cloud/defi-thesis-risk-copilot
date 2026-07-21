from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.evaluation_result import EvaluationResultModel
from app.main import app
from app.models.discovered_item import DiscoveredItemModel
from app.models.knowledge_base_ingestion import KnowledgeBaseIngestionModel
from app.models.review_item import ReviewItemModel
from app.models.source_watch import SourceWatchModel
from app.monitoring.discovery_service import run_monitoring
from app.monitoring.schemas import MonitoringRunRequest, SourceWatch


def test_monitoring_run_creates_normalized_items_without_rag_ingestion() -> None:
    _reset_monitoring_test_state()

    with TestClient(app) as client:
        response = client.post("/api/monitoring/run", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["created_count"] >= 1
    assert payload["failed_count"] == 0
    assert all(item["status"] == "needs_review" for item in payload["discovered_items"])
    assert all("raw_payload" in item for item in payload["discovered_items"])


def test_monitoring_run_detects_duplicates() -> None:
    _reset_monitoring_test_state()

    with TestClient(app) as client:
        first = client.post("/api/monitoring/run", json={"source": "pendle"})
        second = client.post("/api/monitoring/run", json={"source": "pendle"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    assert second.json()["duplicate_count"] >= 1

    with SessionLocal() as db:
        pendle_count = db.execute(
            select(DiscoveredItemModel).where(DiscoveredItemModel.source == "pendle")
        ).scalars().all()

    assert len(pendle_count) == 1


def test_discovered_items_endpoint_filters_results() -> None:
    _reset_monitoring_test_state()

    with TestClient(app) as client:
        client.post("/api/monitoring/run", json={})
        response = client.get("/api/monitoring/discovered-items?protocol=morpho")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all(item["protocol"] == "morpho" for item in payload["items"])


def test_monitoring_failures_are_recorded_without_crashing() -> None:
    class FailingCollector:
        source = "test_failure"

        def collect(self, watch: SourceWatch) -> list:
            raise RuntimeError("simulated collector failure")

    _reset_monitoring_test_state()

    with SessionLocal() as db:
        db.add(
            SourceWatchModel(
                id="watch_test_failure",
                source="test_failure",
                source_type="documentation",
                protocol="pendle",
                url="https://example.invalid",
                enabled=True,
                config_json={},
            )
        )
        db.commit()

        response = run_monitoring(
            MonitoringRunRequest(source="test_failure"),
            db,
            collectors={"test_failure": FailingCollector()},
        )
        watch = db.get(SourceWatchModel, "watch_test_failure")

    assert response.status == "partial"
    assert response.failed_count == 1
    assert response.failures[0].error.startswith("RuntimeError")
    assert watch is not None
    assert watch.last_error is not None
    assert "simulated collector failure" in watch.last_error


def _reset_monitoring_test_state() -> None:
    with SessionLocal() as db:
        db.execute(delete(KnowledgeBaseIngestionModel))
        db.execute(delete(ReviewItemModel))
        db.execute(delete(EvaluationResultModel))
        db.execute(delete(DiscoveredItemModel))
        db.execute(
            delete(SourceWatchModel).where(SourceWatchModel.id == "watch_test_failure")
        )
        db.commit()

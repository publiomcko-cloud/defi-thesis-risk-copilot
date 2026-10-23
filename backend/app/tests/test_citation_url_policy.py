import json
from pathlib import Path

import pytest

from app.rag.source_urls import normalize_citation_url


FIXTURES = json.loads(
    (Path(__file__).resolve().parents[3] / "shared" / "citation_url_fixtures.json").read_text()
)


@pytest.mark.parametrize("fixture", FIXTURES, ids=[fixture["id"] for fixture in FIXTURES])
def test_backend_citation_policy_matches_shared_fixtures(fixture: dict[str, object]) -> None:
    assert normalize_citation_url(fixture["input"]) == fixture["expected"]

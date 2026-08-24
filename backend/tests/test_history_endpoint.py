"""Tests for GET /history — pagination math, ordering, and the empty
case. Run against the real Postgres (via `db_session`'s rolled-back
transaction, same pattern as every other endpoint test), not a mock —
`list_predictions`'s OFFSET/LIMIT and ORDER BY are real SQL, so they need
a real database to actually exercise."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.main import app
from backend.models.prediction import PredictionRecord


@pytest.fixture()
def client(db_session):
    # The real dev DB already has real rows from manual testing throughout
    # this project (confirmed ~22 at time of writing, from curl/browser
    # verification in earlier phases — not a leak from other tests: proven
    # separately that a commit() inside this same rolled-back-transaction
    # fixture does NOT persist past teardown). Deleting them here is safe
    # for the same reason — it only ever happens inside this test's own
    # transaction, which `db_session`'s fixture rolls back afterward, so
    # the real dev DB is completely unaffected once the test ends. This is
    # what makes "correct total count" and "the zero-results case"
    # assertable at all against a database everything else also shares.
    db_session.query(PredictionRecord).delete()
    db_session.commit()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_records(db_session, count: int) -> list[PredictionRecord]:
    """Inserts `count` records with distinct, increasing `created_at`
    timestamps (oldest first) — the DB's `server_default=func.now()`
    would make them all nearly identical if inserted in a tight loop, so
    ordering can't be tested without setting it explicitly."""
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = []
    for i in range(count):
        record = PredictionRecord(
            image_hash=f"hash-{i:03d}",
            predicted_label="cat",
            confidence=0.9,
            probabilities={"cat": 0.9, "dog": 0.1},
            model_version="test-version",
            inference_latency_ms=10.0,
            created_at=base_time + timedelta(minutes=i),
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    return records


def test_empty_history_returns_zero_results(client: TestClient) -> None:
    response = client.get("/history")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_pagination_item_counts_and_total(client: TestClient, db_session) -> None:
    _seed_records(db_session, count=25)

    page1 = client.get("/history", params={"page": 1, "page_size": 10}).json()
    assert len(page1["items"]) == 10
    assert page1["total"] == 25
    assert page1["page"] == 1
    assert page1["page_size"] == 10

    page2 = client.get("/history", params={"page": 2, "page_size": 10}).json()
    assert len(page2["items"]) == 10
    assert page2["total"] == 25

    page3 = client.get("/history", params={"page": 3, "page_size": 10}).json()
    assert len(page3["items"]) == 5  # remainder
    assert page3["total"] == 25

    # No overlap between pages — pagination is actually slicing, not
    # returning the same rows repeatedly.
    ids_page1 = {item["id"] for item in page1["items"]}
    ids_page2 = {item["id"] for item in page2["items"]}
    ids_page3 = {item["id"] for item in page3["items"]}
    assert ids_page1.isdisjoint(ids_page2)
    assert ids_page1.isdisjoint(ids_page3)
    assert ids_page2.isdisjoint(ids_page3)


def test_page_past_the_end_returns_empty_items_not_an_error(
    client: TestClient, db_session
) -> None:
    _seed_records(db_session, count=5)

    response = client.get("/history", params={"page": 99, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 5  # total still reflects the real count


def test_ordering_is_newest_first(client: TestClient, db_session) -> None:
    records = _seed_records(db_session, count=5)
    # _seed_records inserts oldest (index 0) to newest (index 4).
    expected_newest_to_oldest = [r.image_hash for r in reversed(records)]

    response = client.get("/history", params={"page": 1, "page_size": 10})
    returned_hashes = [item["image_hash"] for item in response.json()["items"]]

    assert returned_hashes == expected_newest_to_oldest

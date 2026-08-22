"""Shared test fixtures. Tests run against the real Postgres/Redis
containers (not mocks) — `db_session` wraps each test in a transaction
that's rolled back afterward so nothing persists into the real dev DB;
`test_redis` uses a separate logical Redis DB (15) that's flushed before
and after each test."""

from __future__ import annotations

import pytest
import redis as redis_lib
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.core.database import engine


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def test_redis():
    test_url = settings.redis_url.rsplit("/", 1)[0] + "/15"
    client = redis_lib.Redis.from_url(test_url, decode_responses=True)
    client.flushdb()
    yield client
    client.flushdb()
    client.close()

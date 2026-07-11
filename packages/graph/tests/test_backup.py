"""Offline tests for the backup serializer — pure value coercion + row shaping.
The DB-backed export is validated by running `make export-graph`."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from policyai_graph.backup import _jsonable, serialize_row


def test_jsonable_coerces_uuid_and_dates():
    u = UUID("11111111-1111-1111-1111-111111111111")
    assert _jsonable(u) == "11111111-1111-1111-1111-111111111111"
    assert _jsonable(date(2026, 6, 29)) == "2026-06-29"
    assert _jsonable(datetime(2026, 6, 29, 10, 30)).startswith("2026-06-29T10:30")
    # passthrough for plain json types
    assert _jsonable("x") == "x"
    assert _jsonable(7) == 7
    assert _jsonable(None) is None
    assert _jsonable(["a", "b"]) == ["a", "b"]


def test_serialize_row_selects_columns_and_coerces():
    class Fake:
        id = UUID("22222222-2222-2222-2222-222222222222")
        title = "Master Direction"
        created_at = datetime(2026, 1, 2, 3, 4, 5)
        secret = "should-not-appear"

    row = serialize_row(Fake(), ["id", "title", "created_at"])
    assert row == {
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "Master Direction",
        "created_at": "2026-01-02T03:04:05",
    }
    assert "secret" not in row

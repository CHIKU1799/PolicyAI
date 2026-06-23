"""Unit tests for the scrapers package — pure logic, no browser/DB/network."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from policyai_graph.models_app import MonitoringSource
from policyai_graph.seed import MONITORING_SOURCES
from policyai_scrapers import SCRAPER_REGISTRY
from policyai_scrapers.base import DocMeta
from policyai_scrapers.runner import _is_due


def test_registry_covers_all_seeded_sources():
    """Every seeded monitoring source must have a scraper, and vice versa."""
    seeded_kinds = {s["scraper_kind"] for s in MONITORING_SOURCES}
    assert seeded_kinds == set(SCRAPER_REGISTRY)
    # and each scraper's regulator_key matches its seed entry
    by_kind = {s["scraper_kind"]: s["regulator_key"] for s in MONITORING_SOURCES}
    for kind, cls in SCRAPER_REGISTRY.items():
        assert cls.regulator_key == by_kind[kind]


def test_content_hash_is_stable_and_change_sensitive():
    a = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="body")
    b = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="body")
    assert a.content_hash() == b.content_hash()  # same content -> same hash (dedup)

    c = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="EDITED")
    assert a.content_hash() != c.content_hash()  # edited body -> re-ingest

    d = DocMeta(source="rbi", source_id="1", source_url="u", title="NEW", raw_text="body")
    assert a.content_hash() != d.content_hash()  # edited title -> re-ingest


def test_is_due_cadence_logic():
    now = datetime.now(UTC)

    never = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    never.enabled = True
    never.cadence_hours = 6
    never.last_scanned_at = None
    assert _is_due(never, now) is True  # never scanned -> due

    fresh = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    fresh.enabled = True
    fresh.cadence_hours = 6
    fresh.last_scanned_at = now - timedelta(hours=1)
    assert _is_due(fresh, now) is False  # within cadence -> not due

    stale = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    stale.enabled = True
    stale.cadence_hours = 6
    stale.last_scanned_at = now - timedelta(hours=7)
    assert _is_due(stale, now) is True  # past cadence -> due

    disabled = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    disabled.enabled = False
    disabled.cadence_hours = 6
    disabled.last_scanned_at = None
    assert _is_due(disabled, now) is False  # disabled -> never due

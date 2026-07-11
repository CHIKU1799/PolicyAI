"""Offline tests for the bitemporal query helpers — pure interval logic and that
the SQLAlchemy filters compile. The DB-backed cascade is covered in test_crud."""

from __future__ import annotations

from datetime import date

from policyai_graph.models import Node
from policyai_graph.models_app import Obligation
from policyai_graph.temporal import (
    app_valid_as_of,
    is_valid_as_of,
    node_valid_as_of,
    valid_as_of,
)

D = date(2026, 6, 15)


def test_in_force_window():
    # started before, no end -> in force
    assert is_valid_as_of(date(2026, 1, 1), None, D)
    # started before, ends after -> in force
    assert is_valid_as_of(date(2026, 1, 1), date(2026, 12, 1), D)


def test_not_yet_effective():
    assert not is_valid_as_of(date(2026, 7, 1), None, D)


def test_half_open_end_excludes_end_day():
    # a record ending exactly on the as-of date is NOT in force that day
    assert not is_valid_as_of(date(2026, 1, 1), D, D)
    # ending the day after -> still in force on D
    assert is_valid_as_of(date(2026, 1, 1), date(2026, 6, 16), D)


def test_open_start_assumption():
    # legacy rows with no start are assumed already in force...
    assert is_valid_as_of(None, None, D)
    # ...unless the caller opts out
    assert not is_valid_as_of(None, None, D, assume_started=False)


def test_sql_filters_compile():
    # The point is that these build valid SQL expressions over the right columns.
    for clause in (
        valid_as_of(Node.effective_from, Node.effective_to, D),
        node_valid_as_of(Node, D),
        app_valid_as_of(Obligation, D),
    ):
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "2026-06-15" in compiled

"""Bitemporal query helpers — point-in-time ("as of") filters over the two axes.

PolicyAI tracks two time axes (see migration 0005 / 0009):

* **valid-time** — when a fact was true in the world. On nodes this is
  ``effective_from`` / ``effective_to``; on the app tables (obligations, gaps,
  controls, requirements) it is ``effective_date`` / ``valid_to``.
* **transaction-time** — when PolicyAI *knew* the fact. ``recorded_at`` (the row
  was learned) to ``invalidated_at`` (the row was retired/corrected).

This module centralises the half-open-interval logic ("valid on date D" means
``start <= D`` and ``end is null or end > D``) so every endpoint asks the same
question the same way, and exposes a pure predicate that is unit-tested without a
database. Intervals are half-open at the end so a record that ends on D is *not*
in force on D — it stopped that day.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ColumnElement, or_


def is_valid_as_of(
    start: date | None,
    end: date | None,
    as_of: date,
    *,
    assume_started: bool = True,
) -> bool:
    """Pure predicate: was a fact with validity ``[start, end)`` in force on ``as_of``?

    ``assume_started`` controls the open-start case: a row with no ``start`` is
    treated as having always been in force (True) rather than never (False), which
    matches how we backfill legacy rows that predate the temporal columns.
    """
    if start is not None and start > as_of:
        return False
    if start is None and not assume_started:
        return False
    if end is not None and end <= as_of:
        return False
    return True


def valid_as_of(
    start_col: ColumnElement,
    end_col: ColumnElement,
    as_of: date,
) -> ColumnElement[bool]:
    """SQLAlchemy version of :func:`is_valid_as_of` for use in ``.where(...)``.

    Open start (NULL) is treated as already-in-force; open end (NULL) as still-in-force.
    """
    return (start_col.is_(None) | (start_col <= as_of)) & (end_col.is_(None) | (end_col > as_of))


def known_as_of(
    recorded_col: ColumnElement,
    invalidated_col: ColumnElement,
    as_of: datetime,
) -> ColumnElement[bool]:
    """Transaction-time filter: was the row part of PolicyAI's knowledge at ``as_of``?

    Lets you reconstruct "what did we believe on date X", independent of what was
    actually in force — the second axis that makes the model bitemporal.
    """
    return (recorded_col.is_(None) | (recorded_col <= as_of)) & (
        invalidated_col.is_(None) | (invalidated_col > as_of)
    )


def node_valid_as_of(node_cls, as_of: date) -> ColumnElement[bool]:
    """Convenience: valid-time filter for Node (effective_from/effective_to)."""
    return valid_as_of(node_cls.effective_from, node_cls.effective_to, as_of)


def app_valid_as_of(model_cls, as_of: date) -> ColumnElement[bool]:
    """Convenience: valid-time filter for an app table (effective_date/valid_to)."""
    return valid_as_of(model_cls.effective_date, model_cls.valid_to, as_of)


__all__ = [
    "is_valid_as_of",
    "valid_as_of",
    "known_as_of",
    "node_valid_as_of",
    "app_valid_as_of",
    "or_",  # re-export so callers composing complex filters need one import
]

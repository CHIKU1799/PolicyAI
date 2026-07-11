"""Shared crawl utilities: incremental watermark, retry/backoff, structured logging.

These tighten "get the latest" without re-downloading the world each cadence:

* ``select_new`` drops documents we've already ingested *before* the expensive
  full-text fetch, so a crawl pays only for genuinely new circulars.
* ``with_retry`` retries transient network failures with exponential backoff —
  regulator sites are flaky and a single blip shouldn't drop a document.
* ``log`` is a module logger so the runner emits structured, level-tagged records
  instead of bare prints that vanish into stdout.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import TypeVar

log = logging.getLogger("policyai.scrapers")

T = TypeVar("T")


def select_new(metas: Sequence[T], known_ids: Iterable[str] | None) -> list[T]:
    """Return only the metas whose ``source_id`` we have not already ingested.

    The watermark: circulars are immutable once published (amendments get new
    source_ids), so a known source_id never needs re-fetching. ``known_ids`` empty
    or None means "first crawl — everything is new".
    """
    if not known_ids:
        return list(metas)
    known = set(known_ids)
    return [m for m in metas if getattr(m, "source_id", None) not in known]


async def with_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    label: str = "",
) -> T:
    """Await ``factory()`` with exponential backoff on exception.

    ``factory`` is a thunk (not a coroutine) so each attempt builds a fresh
    awaitable. Re-raises the last exception once attempts are exhausted.
    """
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return await factory()
        except Exception as exc:  # noqa: BLE001 - retry any transient crawl error
            last_exc = exc
            if i < attempts - 1:
                delay = base_delay * (2**i)
                log.warning("retry %s/%s for %s after error: %s", i + 1, attempts, label, exc)
                await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc

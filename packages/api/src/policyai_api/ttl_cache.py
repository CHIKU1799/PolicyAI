"""In-process TTL cache for hot read endpoints.

``ttl_cache(seconds, max_entries)`` decorates an async helper whose FIRST
positional argument is the explicit cache key (any hashable — use a tuple for
compound keys). Remaining arguments (typically the DB session) are passed
through untouched and are NOT part of the key, so per-request objects don't
defeat the cache.

Multi-tenant rule: the key must include the org id wherever the data is
org-scoped, so tenants never see each other's cached responses.

Uses a monotonic clock and LRU-ish eviction at ``max_entries``. Per-process
only — good enough for read endpoints where a short staleness window is fine.
"""

from __future__ import annotations

import functools
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, TypeVar

R = TypeVar("R")


def ttl_cache(
    seconds: float, max_entries: int = 256
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    def decorator(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        store: OrderedDict[Hashable, tuple[float, R]] = OrderedDict()

        @functools.wraps(fn)
        async def wrapper(key: Hashable, *args: Any, **kwargs: Any) -> R:
            now = time.monotonic()
            hit = store.get(key)
            if hit is not None and now - hit[0] < seconds:
                store.move_to_end(key)
                return hit[1]
            value = await fn(key, *args, **kwargs)
            store[key] = (now, value)
            store.move_to_end(key)
            while len(store) > max_entries:
                store.popitem(last=False)
            return value

        wrapper.clear = store.clear  # type: ignore[attr-defined] - test hook
        return wrapper

    return decorator

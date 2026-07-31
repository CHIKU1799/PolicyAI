"""Per-client sliding-window rate limiting for the expensive endpoints.

In-process and dependency-free, in the same spirit as ``ttl_cache``: good
enough for a single worker instance, resets on deploy, no Redis required.
The guarded endpoints are the ones that spend LLM/embedding budget (/ask,
/scan, /map, /documents/process, /profile/derive) plus the public contact
form (email spam).

Keys are (scope, client IP) for anonymous callers and (scope, user, IP) for
authenticated ones, so the anonymous demo org cannot be used as a free LLM
proxy while signed-in users get a generous budget.

Env knobs (requests per minute, sane defaults; invalid values fall back):
  RATE_LIMIT_AUTH_PER_MIN   default 30   authenticated callers
  RATE_LIMIT_ANON_PER_MIN   default 5    anonymous callers (demo org)
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict, deque

from fastapi import Depends, HTTPException, Request

from policyai_api.auth import Principal, resolve_principal

WINDOW_SECONDS = 60.0

AUTH_LIMIT_DEFAULT = 30
ANON_LIMIT_DEFAULT = 5


class SlidingWindowLimiter:
    """Sliding-window counter per key with LRU-ish eviction at ``max_keys``."""

    def __init__(self, window: float = WINDOW_SECONDS, max_keys: int = 4096) -> None:
        self.window = window
        self.max_keys = max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def retry_after(self, key: str, limit: int, now: float | None = None) -> float:
        """0.0 when the call is allowed (and recorded); otherwise the seconds
        until the oldest hit in the window expires."""
        now = time.monotonic() if now is None else now
        q = self._hits.get(key)
        if q is None:
            q = deque()
            self._hits[key] = q
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= limit:
            return max(self.window - (now - q[0]), 0.001)
        q.append(now)
        self._hits.move_to_end(key)
        while len(self._hits) > self.max_keys:
            self._hits.popitem(last=False)
        return 0.0

    def clear(self) -> None:  # test hook
        self._hits.clear()


_limiter = SlidingWindowLimiter()


def clear() -> None:
    """Reset all counters (test hook)."""
    _limiter.clear()


def client_ip(request: Request) -> str:
    """Client IP, honoring the proxy chain header the PaaS puts in front."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _env_limit(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, "")))
    except ValueError:
        return default


def rate_limited(scope: str, *, require_auth: bool = False):
    """Dependency factory: 429 when the caller exceeds the per-minute budget
    for ``scope``; 401 when ``require_auth`` and the caller is anonymous."""

    async def dependency(
        request: Request,
        principal: Principal = Depends(resolve_principal),
    ) -> None:
        if principal.authenticated:
            limit = _env_limit("RATE_LIMIT_AUTH_PER_MIN", AUTH_LIMIT_DEFAULT)
            key = f"{scope}:auth:{principal.user_id}:{client_ip(request)}"
        else:
            if require_auth:
                raise HTTPException(status_code=401, detail="authentication required")
            limit = _env_limit("RATE_LIMIT_ANON_PER_MIN", ANON_LIMIT_DEFAULT)
            key = f"{scope}:anon:{client_ip(request)}"
        wait = _limiter.retry_after(key, limit)
        if wait > 0:
            retry = int(wait) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: at most {limit} requests per minute "
                    f"to this endpoint. Try again in {retry}s."
                ),
                headers={"Retry-After": str(retry)},
            )

    return dependency

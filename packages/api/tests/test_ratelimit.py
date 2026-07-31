"""Rate limiter tests: the sliding window itself, plus the wiring on the
expensive endpoints (anonymous lockout on /scan and /map, anon vs auth budgets
on /ask, 429 shape). No live DB, Supabase, or LLM: dependencies are overridden
and the agent call is monkeypatched."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from policyai_api import deps, ratelimit
from policyai_api.auth import Principal, resolve_principal
from policyai_api.main import app
from policyai_api.ratelimit import SlidingWindowLimiter
from policyai_api.routes import ask as ask_route
from policyai_api.routes import scan as scan_route

ORG_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DEMO_ORG = UUID("00000000-0000-0000-0000-000000000001")


def authenticated() -> Principal:
    return Principal(USER_ID, "user@firm.in", ORG_ID, False, "admin")


def anonymous() -> Principal:
    return Principal(None, None, DEMO_ORG, False)


class FakeSession:
    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("no DB access expected in these tests")


@pytest.fixture
def make_client() -> Iterator[Any]:
    def factory(principal: Principal) -> TestClient:
        async def _session() -> AsyncIterator[FakeSession]:
            yield FakeSession()

        app.dependency_overrides[resolve_principal] = lambda: principal
        app.dependency_overrides[deps.get_session] = _session
        app.dependency_overrides[deps.get_llm] = lambda: None
        return TestClient(app)

    ratelimit.clear()
    yield factory
    ratelimit.clear()
    app.dependency_overrides.clear()


# --- the window itself ------------------------------------------------------


def test_sliding_window_allows_then_blocks_then_recovers() -> None:
    limiter = SlidingWindowLimiter(window=60.0)
    assert limiter.retry_after("k", 3, now=0.0) == 0.0
    assert limiter.retry_after("k", 3, now=1.0) == 0.0
    assert limiter.retry_after("k", 3, now=2.0) == 0.0
    # 4th call inside the window is refused, with the time until the oldest
    # hit slides out.
    wait = limiter.retry_after("k", 3, now=3.0)
    assert wait == pytest.approx(57.0)
    # A refused call is not recorded: capacity frees exactly when hit #1 ages out.
    assert limiter.retry_after("k", 3, now=60.5) == 0.0


def test_sliding_window_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(window=60.0)
    assert limiter.retry_after("a", 1, now=0.0) == 0.0
    assert limiter.retry_after("a", 1, now=1.0) > 0
    assert limiter.retry_after("b", 1, now=1.0) == 0.0


def test_sliding_window_evicts_oldest_keys() -> None:
    limiter = SlidingWindowLimiter(window=60.0, max_keys=2)
    limiter.retry_after("a", 5, now=0.0)
    limiter.retry_after("b", 5, now=1.0)
    limiter.retry_after("c", 5, now=2.0)  # evicts "a"
    assert len(limiter._hits) == 2
    assert "a" not in limiter._hits


# --- endpoint wiring --------------------------------------------------------


def test_scan_and_map_reject_anonymous(make_client: Any) -> None:
    client = make_client(anonymous())
    assert client.post("/scan").status_code == 401
    assert client.post("/map", json={}).status_code == 401


def test_scan_authenticated_allowed_then_rate_limited(
    make_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[bool] = []

    async def fake_run_once(*, force: bool = False) -> None:
        started.append(force)

    monkeypatch.setattr(scan_route, "run_once", fake_run_once)
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MIN", "2")
    client = make_client(authenticated())

    assert client.post("/scan").status_code == 202
    assert client.post("/scan").status_code == 202
    resp = client.post("/scan")
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.json()["detail"]
    assert int(resp.headers["Retry-After"]) >= 1
    assert len(started) == 2  # the refused call never started a crawl


def test_ask_anonymous_gets_tight_budget(make_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_ask(session: Any, question: str, llm: Any, org_id: Any = None) -> dict:
        calls.append(question)
        return {"answer": "ok", "citations": []}

    monkeypatch.setattr(ask_route, "ask", fake_ask)
    monkeypatch.setenv("RATE_LIMIT_ANON_PER_MIN", "2")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MIN", "30")
    client = make_client(anonymous())

    assert client.post("/ask", json={"question": "q1"}).status_code == 200
    assert client.post("/ask", json={"question": "q2"}).status_code == 200
    resp = client.post("/ask", json={"question": "q3"})
    assert resp.status_code == 429
    assert len(calls) == 2  # the refused call never reached the LLM


def test_ask_auth_budget_larger_than_anon(
    make_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_ask(session: Any, question: str, llm: Any, org_id: Any = None) -> dict:
        return {"answer": "ok", "citations": []}

    monkeypatch.setattr(ask_route, "ask", fake_ask)
    monkeypatch.setenv("RATE_LIMIT_ANON_PER_MIN", "1")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MIN", "5")
    client = make_client(authenticated())
    for _ in range(5):
        assert client.post("/ask", json={"question": "q"}).status_code == 200
    assert client.post("/ask", json={"question": "q"}).status_code == 429


def test_ask_and_stream_share_one_budget(make_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ask(session: Any, question: str, llm: Any, org_id: Any = None) -> dict:
        return {"answer": "ok", "citations": []}

    monkeypatch.setattr(ask_route, "ask", fake_ask)
    monkeypatch.setenv("RATE_LIMIT_ANON_PER_MIN", "2")
    client = make_client(anonymous())
    assert client.post("/ask", json={"question": "q"}).status_code == 200
    assert client.post("/ask", json={"question": "q"}).status_code == 200
    # /ask/stream draws from the same "ask" scope, so it is refused too.
    assert client.post("/ask/stream", json={"question": "q"}).status_code == 429


def test_invalid_env_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MIN", "not-a-number")
    assert ratelimit._env_limit("RATE_LIMIT_AUTH_PER_MIN", 30) == 30
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MIN", "0")
    assert ratelimit._env_limit("RATE_LIMIT_AUTH_PER_MIN", 30) == 1

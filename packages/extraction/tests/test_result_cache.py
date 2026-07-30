"""Unit tests for the persistent LLM result cache (layer 2) and the cache
accounting added to CostTracker (layer 1). No live DB or network: the cache's
session factory is swapped for a fake, following the fake-session approach of
packages/api/tests/test_org_routes.py."""

from __future__ import annotations

from typing import Any

import pytest
from policyai_extraction import llm as llm_mod
from policyai_extraction import result_cache
from policyai_extraction.llm import CostTracker, LLMClient
from policyai_extraction.schemas import ExtractedRegulation


class FakeResult:
    def __init__(self, scalar: Any = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeSession:
    """Async-context-manager session recording statements; answers SELECTs
    with a canned response payload."""

    def __init__(self, response: dict | None = None) -> None:
        self.response = response
        self.statements: list[str] = []
        self.committed = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def execute(self, stmt: Any) -> FakeResult:
        sql = " ".join(str(stmt).split()).lower()
        self.statements.append(sql)
        if sql.startswith("select"):
            return FakeResult(self.response)
        return FakeResult()

    async def commit(self) -> None:
        self.committed = True


@pytest.fixture
def fake_session(monkeypatch) -> FakeSession:
    session = FakeSession()
    monkeypatch.setattr(result_cache, "_sessionmaker", lambda: session)
    return session


def _anthropic_client(monkeypatch) -> LLMClient:
    monkeypatch.setattr(llm_mod, "LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return LLMClient()


REG_PAYLOAD = {
    "title": "Master Direction on NBFC-MFI",
    "regulator_key": "rbi",
    "summary": "Sets pricing caps for microfinance loans.",
}


# ---- key construction --------------------------------------------------


def test_make_key_stable_across_dict_ordering():
    a = {"provider": "anthropic", "model": "m", "system": "s", "purpose": "extract"}
    b = {"purpose": "extract", "system": "s", "model": "m", "provider": "anthropic"}
    assert result_cache.make_key(a) == result_cache.make_key(b)
    assert len(result_cache.make_key(a)) == 64  # sha256 hex


def test_make_key_sensitive_to_content():
    base = {"provider": "anthropic", "model": "m", "system": "s"}
    assert result_cache.make_key(base) != result_cache.make_key({**base, "system": "S"})
    assert result_cache.make_key(base) != result_cache.make_key({**base, "model": "other"})


# ---- get / put against a faked session ---------------------------------


async def test_get_returns_cached_payload(fake_session: FakeSession):
    fake_session.response = REG_PAYLOAD
    assert await result_cache.get("k" * 64) == REG_PAYLOAD
    assert any("llm_cache" in s for s in fake_session.statements)


async def test_put_inserts_and_commits(fake_session: FakeSession):
    await result_cache.put("k" * 64, "claude-sonnet-4-6", "extract", REG_PAYLOAD)
    inserts = [s for s in fake_session.statements if s.startswith("insert into llm_cache")]
    assert len(inserts) == 1
    assert "on conflict" in inserts[0]
    assert fake_session.committed


async def test_cache_failures_never_raise(monkeypatch):
    def boom() -> None:
        raise RuntimeError("no database")

    monkeypatch.setattr(result_cache, "_get_sessionmaker", boom)
    assert await result_cache.get("k" * 64) is None
    await result_cache.put("k" * 64, None, None, {})  # must not raise


# ---- extract() hit / miss wiring ----------------------------------------


async def test_extract_hit_replays_without_llm_call(monkeypatch, fake_session: FakeSession):
    fake_session.response = REG_PAYLOAD
    client = _anthropic_client(monkeypatch)

    async def no_call(*args: Any, **kwargs: Any):
        raise AssertionError("LLM must not be called on a cache hit")

    monkeypatch.setattr(client, "_extract_uncached", no_call)
    out = await client.extract("prompt", ExtractedRegulation, system="s", cache_purpose="extract")
    assert isinstance(out, ExtractedRegulation)
    assert out.title == REG_PAYLOAD["title"]
    # zero cost recorded for a replayed result
    assert client.cost.calls == 0 and client.cost.usd == 0.0


async def test_extract_miss_stores_validated_result(monkeypatch, fake_session: FakeSession):
    client = _anthropic_client(monkeypatch)
    extracted = ExtractedRegulation.model_validate(REG_PAYLOAD)

    async def fake_llm(*args: Any, **kwargs: Any) -> ExtractedRegulation:
        return extracted

    monkeypatch.setattr(client, "_extract_uncached", fake_llm)
    out = await client.extract("prompt", ExtractedRegulation, system="s", cache_purpose="extract")
    assert out is extracted
    assert any(s.startswith("insert into llm_cache") for s in fake_session.statements)


async def test_extract_cache_disabled_by_env(monkeypatch, fake_session: FakeSession):
    monkeypatch.setenv("LLM_RESULT_CACHE", "0")
    client = _anthropic_client(monkeypatch)
    extracted = ExtractedRegulation.model_validate(REG_PAYLOAD)

    async def fake_llm(*args: Any, **kwargs: Any) -> ExtractedRegulation:
        return extracted

    monkeypatch.setattr(client, "_extract_uncached", fake_llm)
    await client.extract("prompt", ExtractedRegulation, system="s", cache_purpose="extract")
    assert fake_session.statements == []  # cache never touched


# ---- CostTracker cache accounting (layer 1) ------------------------------


def test_cost_tracker_prices_cache_reads_and_writes():
    c = CostTracker()
    # 1M cached-read tokens at 10% of the $3 sonnet input rate = $0.30;
    # 1M cache-write tokens at 125% = $3.75.
    c.record("claude-sonnet-4-6", 0, 0, cache_read=1_000_000)
    assert c.usd == pytest.approx(0.30)
    c.record("claude-sonnet-4-6", 0, 0, cache_write=1_000_000)
    assert c.usd == pytest.approx(0.30 + 3.75)
    # saved = reads at 90% off, minus the 25% write premium
    assert c.usd_saved == pytest.approx(3.0 * 0.9 - 3.0 * 0.25)
    assert "cached-read tokens" in c.summary()


def test_cost_tracker_backwards_compatible():
    c = CostTracker()
    c.record("claude-opus-4-8", 1_000_000, 1_000_000)
    assert c.usd == pytest.approx(30.0)
    assert c.cache_read_tokens == 0 and c.cache_write_tokens == 0
    assert "cached-read" not in c.summary()

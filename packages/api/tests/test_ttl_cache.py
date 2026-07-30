"""Unit tests for the in-process TTL cache used by hot read endpoints."""

from __future__ import annotations

from uuid import uuid4

from policyai_api.ttl_cache import ttl_cache


def make_counter():
    calls: list[object] = []

    @ttl_cache(seconds=60, max_entries=3)
    async def compute(key, session=None):
        calls.append(key)
        return {"key": key, "n": len(calls)}

    return compute, calls


async def test_two_calls_within_ttl_hit_once():
    compute, calls = make_counter()
    org = uuid4()
    first = await compute(org, session="request-1-session")
    second = await compute(org, session="request-2-session")
    assert first is second  # served from cache
    assert calls == [org]  # underlying computation ran once


async def test_different_org_key_misses():
    compute, calls = make_counter()
    org_a, org_b = uuid4(), uuid4()
    a = await compute(org_a)
    b = await compute(org_b)
    assert a != b
    assert calls == [org_a, org_b]  # one computation per tenant


async def test_expiry_recomputes(monkeypatch):
    import policyai_api.ttl_cache as mod

    now = [1000.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    compute, calls = make_counter()
    key = ("kg", "rbi", 1, 200)
    await compute(key)
    now[0] += 61  # past the 60s TTL
    await compute(key)
    assert calls == [key, key]


async def test_clear_and_eviction():
    compute, calls = make_counter()
    await compute("a")
    compute.clear()
    await compute("a")
    assert calls == ["a", "a"]  # clear() forces a recompute

    # LRU-ish eviction: max_entries=3, so the oldest key falls out
    for k in ("k1", "k2", "k3", "k4"):
        await compute(k)
    before = len(calls)
    await compute("k4")  # still cached
    assert len(calls) == before
    await compute("k1")  # evicted -> recomputed
    assert len(calls) == before + 1

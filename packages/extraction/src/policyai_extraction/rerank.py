"""Optional open-source reranker — sharpens retrieval before Claude reasons.

pgvector gives a fast but coarse nearest-neighbour shortlist. A cross-encoder
(BAAI/bge-reranker-v2-m3, open-source) re-scores each candidate against the query
and reorders them, so the obligation-mapping gap analysis and the Ask agent feed
on the *most relevant* text — better precision, with Claude still doing the
reasoning.

Graceful by design: on any error, or when RERANK_PROVIDER is ``off``, callers get
the original (vector) order back — nothing breaks. Default is ``cohere`` (managed,
multilingual, no infra) since the Cohere key is already configured; Claude still
does all the reasoning.

  RERANK_PROVIDER=cohere : Cohere /rerank (rerank-v3.5, needs COHERE_API_KEY)
  RERANK_PROVIDER=local  : in-process CrossEncoder (needs sentence-transformers)
  RERANK_PROVIDER=hf     : a TEI /rerank endpoint (RERANK_ENDPOINT + HF_API_TOKEN)
  RERANK_PROVIDER=off    : disabled (identity order)
"""

from __future__ import annotations

import asyncio
import os

import httpx

RERANK_PROVIDER = os.getenv("RERANK_PROVIDER", "cohere").lower()
_MODEL = "BAAI/bge-reranker-v2-m3"
_COHERE_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5")
_TIMEOUT = httpx.Timeout(60.0)
_model = None


def is_enabled() -> bool:
    return RERANK_PROVIDER in ("cohere", "local", "hf")


def _get_local():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(_MODEL)
    return _model


async def rerank(query: str, docs: list[str], *, top_k: int | None = None) -> list[int]:
    """Return indices of ``docs`` ordered most- to least-relevant to ``query``
    (truncated to ``top_k``). No-op identity order when disabled or on error."""
    n = len(docs)
    top_k = top_k or n
    if n == 0 or not is_enabled():
        return list(range(n))[:top_k]
    try:
        if RERANK_PROVIDER == "cohere":
            scores = await _rerank_cohere(query, docs)
        elif RERANK_PROVIDER == "local":
            model = _get_local()
            scores = await asyncio.to_thread(
                lambda: model.predict([(query, d) for d in docs]).tolist()
            )
        else:
            scores = await _rerank_hf(query, docs)
        order = sorted(range(n), key=lambda i: scores[i], reverse=True)
        return order[:top_k]
    except Exception as exc:  # noqa: BLE001 - never let reranking break retrieval
        print(f"[rerank] falling back to vector order: {exc}")
        return list(range(n))[:top_k]


async def _rerank_cohere(query: str, docs: list[str]) -> list[float]:
    key = os.getenv("COHERE_API_KEY")
    if not key:
        raise RuntimeError("COHERE_API_KEY not set")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": _COHERE_MODEL, "query": query, "documents": docs, "top_n": len(docs)}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post("https://api.cohere.com/v2/rerank", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    # Cohere v2 returns {"results": [{"index": i, "relevance_score": s}, ...]}
    scores = [0.0] * len(docs)
    for item in data.get("results", []):
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx < len(docs):
            scores[idx] = float(item.get("relevance_score", 0.0))
    return scores


async def _rerank_hf(query: str, docs: list[str]) -> list[float]:
    endpoint = os.getenv("RERANK_ENDPOINT")
    if not endpoint:
        raise RuntimeError("RERANK_ENDPOINT not set")
    headers = {"Content-Type": "application/json"}
    token = os.getenv("HF_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(endpoint, headers=headers, json={"query": query, "texts": docs})
        resp.raise_for_status()
        data = resp.json()
    # TEI rerank returns [{"index": i, "score": s}, ...]
    scores = [0.0] * len(docs)
    for item in data:
        if isinstance(item, dict) and "index" in item:
            scores[item["index"]] = float(item.get("score", 0.0))
    return scores

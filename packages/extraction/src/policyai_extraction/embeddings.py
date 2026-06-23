"""Embedding client — pluggable provider, all 1024-dim to match the schema.

Set ``EMBEDDING_PROVIDER`` to one of:
  - ``local``  : run BAAI/bge-m3 in-process via sentence-transformers. No API, no
                 token, no rate limits — the most robust option. Needs the extra
                 dep: ``uv add sentence-transformers`` (pulls torch, ~2GB).
  - ``hf``     : call a Hugging Face endpoint. Set HF_EMBEDDING_ENDPOINT to your
                 dedicated TEI endpoint; if blank but HF_API_TOKEN is set, it
                 falls back to the HF serverless feature-extraction API for
                 bge-m3 (free, but cold-starts and can be rate-limited).
  - ``voyage`` : Voyage AI voyage-3 (managed, one key, very reliable).
  - ``cohere`` : Cohere embed-multilingual-v3 (managed, one key).

``EMBEDDING_DIM`` is imported from the graph package so the vector width can never
silently drift from the ``Vector(1024)`` columns; every vector is asserted to it.
"""

from __future__ import annotations

import asyncio
import os

import httpx
from policyai_graph.models import EMBEDDING_DIM

PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hf").lower()
_HTTP_TIMEOUT = httpx.Timeout(120.0)  # HF serverless can cold-start slowly
# HF serverless feature-extraction endpoint used when no dedicated endpoint is set.
_HF_SERVERLESS = (
    "https://router.huggingface.co/hf-inference/models/BAAI/bge-m3/pipeline/feature-extraction"
)
_LOCAL_MODEL = "BAAI/bge-m3"


class EmbeddingError(RuntimeError):
    pass


def _check_dims(vectors: list[list[float]]) -> list[list[float]]:
    for v in vectors:
        if len(v) != EMBEDDING_DIM:
            raise EmbeddingError(
                f"Embedding provider returned dim {len(v)}, expected {EMBEDDING_DIM}. "
                "Check the model — bge-m3 / voyage-3 / cohere v3 must be configured for 1024-dim."
            )
    return vectors


def _normalize_hf(data: object, n_inputs: int) -> list[list[float]]:
    """HF endpoints vary in shape: TEI returns a list of vectors; some configs
    wrap it in {'embeddings': ...}; a single-input feature-extraction call can
    return a bare vector. Normalize all of these to a list of vectors."""
    if isinstance(data, dict):
        data = data.get("embeddings") or data.get("data") or data
    if isinstance(data, list) and data and isinstance(data[0], (int, float)):
        # A single flat vector -> wrap it (only valid when one input was sent).
        return [list(data)]  # type: ignore[list-item]
    if isinstance(data, list):
        return [list(v) for v in data]
    raise EmbeddingError(f"Unexpected HF embedding response shape: {type(data)}")


_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise EmbeddingError(
                "EMBEDDING_PROVIDER=local needs sentence-transformers. "
                "Install it: `uv add sentence-transformers` (or pip install)."
            ) from exc
        _local_model = SentenceTransformer(_LOCAL_MODEL)
    return _local_model


async def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    # encode() is blocking/CPU-bound — run it off the event loop.
    vectors = await asyncio.to_thread(
        lambda: model.encode(texts, normalize_embeddings=True).tolist()
    )
    return _check_dims(vectors)


async def _embed_hf(texts: list[str]) -> list[list[float]]:
    token = os.getenv("HF_API_TOKEN")
    endpoint = os.getenv("HF_EMBEDDING_ENDPOINT")
    if not endpoint:
        if not token:
            raise EmbeddingError(
                "Set HF_EMBEDDING_ENDPOINT (dedicated endpoint) or HF_API_TOKEN "
                "(serverless), or switch EMBEDDING_PROVIDER to local/voyage/cohere."
            )
        endpoint = _HF_SERVERLESS  # serverless fallback when only a token is set
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Text Embeddings Inference (TEI) accepts {"inputs": [...]} and returns a
    # list of vectors aligned to the inputs.
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(endpoint, headers=headers, json={"inputs": texts})
        resp.raise_for_status()
        data = resp.json()
    return _check_dims(_normalize_hf(data, len(texts)))


async def _embed_voyage(texts: list[str]) -> list[list[float]]:
    key = os.getenv("VOYAGE_API_KEY")
    if not key:
        raise EmbeddingError("VOYAGE_API_KEY is not set")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {key}"},
            json={"input": texts, "model": "voyage-3", "output_dimension": EMBEDDING_DIM},
        )
        resp.raise_for_status()
        data = resp.json()
    return _check_dims([item["embedding"] for item in data["data"]])


async def _embed_cohere(texts: list[str]) -> list[list[float]]:
    key = os.getenv("COHERE_API_KEY")
    if not key:
        raise EmbeddingError("COHERE_API_KEY is not set")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            "https://api.cohere.com/v2/embed",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "texts": texts,
                "model": "embed-multilingual-v3.0",
                "input_type": "search_document",
                "embedding_types": ["float"],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return _check_dims(data["embeddings"]["float"])


_PROVIDERS = {
    "local": _embed_local,
    "hf": _embed_hf,
    "voyage": _embed_voyage,
    "cohere": _embed_cohere,
}


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the configured provider. Returns one
    ``EMBEDDING_DIM``-length vector per input, in order."""
    if not texts:
        return []
    fn = _PROVIDERS.get(PROVIDER)
    if fn is None:
        raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER={PROVIDER!r}")
    return await fn(texts)


async def embed_text(text: str) -> list[float]:
    """Convenience: embed a single string."""
    return (await embed_texts([text]))[0]

"""Optional gbrain / hermes enrichment adapter.

gbrain is a separate BFSI knowledge graph of real companies and people. PolicyAI
calls it to (a) enrich a company's applicability profile at onboarding and (b)
suggest real owners for generated tasks. It is strictly optional: if
``GBRAIN_BASE_URL`` is unset or the service is unreachable, every method returns
an empty result and the platform runs docs-only.

The HTTP surface here is intentionally thin and defensive — gbrain owns its own
schema; we only consume the few fields we need and never hard-fail on its shape.
"""

from __future__ import annotations

import os

import httpx

_TIMEOUT = httpx.Timeout(20.0)


def is_configured() -> bool:
    return bool(os.getenv("GBRAIN_BASE_URL"))


def _headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    key = os.getenv("GBRAIN_API_KEY")
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


async def _get(path: str, params: dict | None = None) -> dict | list | None:
    base = os.getenv("GBRAIN_BASE_URL")
    if not base:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(base.rstrip("/") + path, params=params, headers=_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001 - enrichment must never break the caller
        print(f"[gbrain] {path} failed: {exc}")
        return None


async def find_company(name: str) -> dict | None:
    """Resolve a company in the gbrain BFSI graph. Hits the Hermes Platform API
    `GET /graph/companies?q=` and returns the best-match company dict (id, name,
    sector, ...) or None."""
    data = await _get("/graph/companies", {"q": name, "limit": 1})
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


async def suggest_owners(company_name: str, *, topic: str | None = None) -> list[str]:
    """Suggest real owners at a company for an obligation. Hits
    `GET /graph/people?company=&q=` — gbrain returns people ranked by seniority,
    so the first names are the most senior. Returns "Name — Designation" strings
    (possibly empty). ``topic`` biases toward relevant roles (e.g. compliance/risk)."""
    data = await _get(
        "/graph/people",
        {"company": company_name, "q": topic or "compliance risk", "limit": 8},
    )
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for person in data:
        if not isinstance(person, dict):
            continue
        name = person.get("name") or person.get("full_name")
        if not name:
            continue
        title = person.get("designation") or person.get("title")
        out.append(f"{name} — {title}" if title else str(name))
    return out

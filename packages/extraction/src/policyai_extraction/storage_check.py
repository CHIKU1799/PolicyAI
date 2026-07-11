"""Object-storage connectivity check: round-trips a test object through the
configured backend (Supabase or R2).

    uv run python -m policyai_extraction.storage_check
"""

from __future__ import annotations

import asyncio

from policyai_extraction import storage

_KEY = "healthcheck/storage_check.txt"
_PAYLOAD = b"policyai storage ok"


async def _main() -> None:
    print(f"backend     : {storage.STORAGE_BACKEND}")
    print(f"archive on  : {storage.archive_enabled()}")
    try:
        await storage.upload(_KEY, _PAYLOAD, content_type="text/plain")
        data = await storage.download(_KEY)
        ok = data == _PAYLOAD
        print(f"round-trip  : {'OK ✓' if ok else 'MISMATCH'}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED      : {type(exc).__name__}: {str(exc)[:200]}")


if __name__ == "__main__":
    asyncio.run(_main())

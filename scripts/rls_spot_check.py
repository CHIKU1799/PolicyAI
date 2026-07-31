"""RLS spot check: what can a completely unauthenticated caller (the public
ANON key, no user JWT) read or write via Supabase REST?

Run from the repo root (reads SUPABASE_URL / SUPABASE_ANON_KEY from .env):

    uv run --no-sync python scripts/rls_spot_check.py

Read-only except for one deliberately harmless probe: a PATCH on obligations
filtered to an impossible id (matches zero rows), which reveals whether the
legacy anon-update policy from supabase/migrations/0009 is still active
without modifying any data.

PASS means the anon key is properly locked out (zero rows / permission
denied). FAIL means the table is exposed and needs the 0015 hardening
migration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env(Path(__file__).resolve().parent.parent / ".env")
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not anon:
        print("SUPABASE_URL / SUPABASE_ANON_KEY not configured")
        return 2

    headers = {"apikey": anon, "Authorization": f"Bearer {anon}"}
    client = httpx.Client(timeout=15.0)
    failures = 0

    def check_read(table: str, select: str = "*", expect_locked: bool = True) -> None:
        nonlocal failures
        r = client.get(
            f"{url}/rest/v1/{table}", params={"select": select, "limit": "3"}, headers=headers
        )
        rows = r.json() if r.status_code == 200 else None
        exposed = r.status_code == 200 and isinstance(rows, list) and len(rows) > 0
        if expect_locked:
            status = "FAIL (EXPOSED)" if exposed else "PASS (locked)"
            failures += int(exposed)
        else:
            status = "open by design" if exposed else "returns nothing"
        detail = f"HTTP {r.status_code}, rows={len(rows) if isinstance(rows, list) else 'n/a'}"
        print(f"  anon SELECT {table:<20} -> {status:<16} [{detail}]")

    def check_update(table: str, body: dict) -> None:
        nonlocal failures
        # Filter matches zero rows: proves whether the policy allows anon
        # UPDATE without ever touching data.
        r = client.patch(
            f"{url}/rest/v1/{table}",
            params={"id": "eq.00000000-0000-0000-0000-000000000000"},
            headers={**headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
            json=body,
        )
        allowed = r.status_code in (200, 204)
        status = "FAIL (anon UPDATE allowed)" if allowed else "PASS (denied)"
        failures += int(allowed)
        print(f"  anon UPDATE {table:<20} (0-row filter) -> {status} [HTTP {r.status_code}]")

    print(f"RLS spot check against {url} using the ANON key, no user session\n")
    print("Tenant/private tables (must be locked):")
    check_read("memberships", "user_id,org_id,role")
    check_read("org_invites", "email,role")
    check_read("platform_admins", "user_id,email")
    check_read("obligations", "org_id,title,status")
    check_read("company_documents", "org_id,filename")
    check_read("gaps", "org_id,description")
    check_read("tasks", "org_id,title")
    check_read("alerts", "org_id,message")
    check_read("company_profiles", "org_id,entity_classes")
    check_read("demo_requests", "email,name")
    check_read("llm_cache", "cache_key")
    check_read("raw_documents", "id")
    print("\nWrite probes (all must be denied):")
    check_update("obligations", {"status": "open"})
    check_update("demo_requests", {"name": "probe"})
    check_update("llm_cache", {"response": {}})
    check_update("nodes", {"node_type": "regulation"})
    check_update("edges", {"edge_type": "references"})
    print("\nShared reference data (public read by design, informational):")
    check_read("requirements", "requirement_type", expect_locked=False)
    check_read("monitoring_sources", "name", expect_locked=False)
    check_read("nodes", "node_type", expect_locked=False)
    check_read("edges", "edge_type", expect_locked=False)

    print(f"\n{'FAILURES: ' + str(failures) if failures else 'All checks passed.'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

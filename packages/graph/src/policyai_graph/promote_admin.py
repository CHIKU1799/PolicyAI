"""Promote a Supabase Auth user to platform super-admin.

Platform admins are granted deliberately (never on signup). This looks up the user
by email in Supabase's auth.users and inserts a platform_admins row, so they can
open the /admin console and read across every org.

    make seed-admin EMAIL=you@example.com
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from policyai_graph.db import make_engine, make_sessionmaker


async def _promote(email: str) -> int:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    try:
        async with sm() as session:
            row = await session.execute(
                text("select id::text, email from auth.users where lower(email) = lower(:e)"),
                {"e": email},
            )
            found = row.first()
            if not found:
                print(f"No Auth user with email {email!r}. Sign up first, then re-run.")
                return 1
            user_id, user_email = found
            await session.execute(
                text(
                    "insert into public.platform_admins (user_id, email) values (:u, :e) "
                    "on conflict (user_id) do update set email = excluded.email"
                ),
                {"u": user_id, "e": user_email},
            )
            await session.commit()
            print(f"Promoted {user_email} ({user_id}) to platform admin.")
            return 0
    finally:
        await engine.dispose()


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: python -m policyai_graph.promote_admin <email>")
        return 2
    return asyncio.run(_promote(sys.argv[1].strip()))


if __name__ == "__main__":
    raise SystemExit(main())

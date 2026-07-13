"""Auth + tenancy resolution for the worker API.

The browser calls the worker with the Supabase access token in the Authorization
header. We validate it by asking Supabase who the token belongs to (GET
/auth/v1/user), then resolve that user's org from ``memberships`` and whether they
are a platform super-admin. No JWT secret or extra crypto dependency required.

Degrades gracefully: with no token (or Supabase unconfigured) the request falls
back to the default demo org, so local/dev and the internal crawler keep working.
Real multi-tenant scoping kicks in the moment the frontend sends a token.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException
from policyai_graph.models_app import DEFAULT_ORG_ID, Membership, PlatformAdmin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_session

_USER_CACHE_TTL = 0  # tokens are short-lived; skip caching for correctness.


@dataclass
class Principal:
    """Who is making the request, resolved from the bearer token."""

    user_id: UUID | None
    email: str | None
    org_id: UUID
    is_platform_admin: bool

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None


async def _supabase_user(token: str) -> dict | None:
    url = os.getenv("SUPABASE_URL")
    anon = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not anon:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{url.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": anon},
            )
        if resp.status_code == 200:
            return resp.json()
    except httpx.HTTPError:
        return None
    return None


async def resolve_principal(
    session: AsyncSession = Depends(get_session),
    authorization: str = Header(default=""),
) -> Principal:
    """FastAPI dependency: turn the Authorization header into a Principal.

    Anonymous / unconfigured -> the default org (backward compatible)."""
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        return Principal(None, None, DEFAULT_ORG_ID, False)

    user = await _supabase_user(token)
    if not user or not user.get("id"):
        return Principal(None, None, DEFAULT_ORG_ID, False)

    user_id = UUID(user["id"])
    email = user.get("email")

    is_admin = (
        await session.execute(select(PlatformAdmin.user_id).where(PlatformAdmin.user_id == user_id))
    ).scalar_one_or_none() is not None

    org_id = (
        (
            await session.execute(
                select(Membership.org_id)
                .where(Membership.user_id == user_id)
                .order_by(Membership.created_at.asc())
            )
        )
        .scalars()
        .first()
    )

    return Principal(user_id, email, org_id or DEFAULT_ORG_ID, is_admin)


async def require_platform_admin(
    principal: Principal = Depends(resolve_principal),
) -> Principal:
    """Guard for the /admin console: only platform super-admins pass."""
    if not principal.is_platform_admin:
        raise HTTPException(status_code=403, detail="platform admin required")
    return principal


def effective_org(principal: Principal, requested: UUID | None = None) -> UUID:
    """The org a request may act on. Platform admins may target any org they
    name; everyone else is pinned to the org resolved from their token, no
    matter what the client sent."""
    if requested is not None and principal.is_platform_admin:
        return requested
    return principal.org_id

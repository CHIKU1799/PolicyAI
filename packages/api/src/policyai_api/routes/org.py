"""Org team management: members, roles, and invites. Org-admin only.

The worker runs on the service-role connection, so it can read ``auth.users``
directly to resolve member emails and add memberships for already-registered
invitees. Invitees without an account get a pending ``org_invites`` row that the
Supabase signup trigger consumes when they register (supabase 0014).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, require_org_admin
from policyai_api.deps import get_session

router = APIRouter(prefix="/org", tags=["org"])

ASSIGNABLE_ROLES = {"admin", "member"}


class MemberRow(BaseModel):
    user_id: str
    email: str | None
    role: str
    joined_at: str | None


class InviteRow(BaseModel):
    id: str
    email: str
    role: str
    created_at: str | None


class InviteCreate(BaseModel):
    email: str
    role: str = "member"


class InviteResult(BaseModel):
    # "member_added": the invitee already had an account and joined immediately.
    # "invite_pending": stored for the signup trigger to consume on registration.
    result: str
    email: str
    role: str


class RoleUpdate(BaseModel):
    role: str


class MemberResult(BaseModel):
    user_id: str
    role: str


def _check_role(role: str) -> str:
    role = role.strip().lower()
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'member'")
    return role


def _check_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or len(email) < 3:
        raise HTTPException(status_code=422, detail="invalid email address")
    return email


@router.get("/members", response_model=list[MemberRow])
async def list_members(
    principal: Principal = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
) -> list[MemberRow]:
    rows = await session.execute(
        text(
            "select m.user_id::text, u.email, m.role, m.created_at::text "
            "from public.memberships m "
            "left join auth.users u on u.id = m.user_id "
            "where m.org_id = :org_id order by m.created_at asc"
        ),
        {"org_id": str(principal.org_id)},
    )
    return [
        MemberRow(user_id=uid, email=email, role=role, joined_at=joined)
        for uid, email, role, joined in rows.all()
    ]


@router.get("/invites", response_model=list[InviteRow])
async def list_invites(
    principal: Principal = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
) -> list[InviteRow]:
    rows = await session.execute(
        text(
            "select id::text, email, role, created_at::text from public.org_invites "
            "where org_id = :org_id and accepted_at is null order by created_at asc"
        ),
        {"org_id": str(principal.org_id)},
    )
    return [
        InviteRow(id=iid, email=email, role=role, created_at=created)
        for iid, email, role, created in rows.all()
    ]


@router.post("/invites", response_model=InviteResult)
async def create_invite(
    payload: InviteCreate,
    principal: Principal = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
) -> InviteResult:
    email = _check_email(payload.email)
    role = _check_role(payload.role)
    org_id = str(principal.org_id)
    created_by = str(principal.user_id) if principal.user_id else None

    existing_user = (
        await session.execute(
            text("select id::text from auth.users where lower(email) = :email limit 1"),
            {"email": email},
        )
    ).scalar_one_or_none()

    if existing_user:
        # Already registered: add the membership now; keep the invite row as an
        # audit record, stamped accepted.
        await session.execute(
            text(
                "insert into public.memberships (id, user_id, org_id, role) "
                "values (gen_random_uuid(), :user_id, :org_id, :role) "
                "on conflict (user_id, org_id) do nothing"
            ),
            {"user_id": existing_user, "org_id": org_id, "role": role},
        )
        await session.execute(
            text(
                "insert into public.org_invites "
                "(id, org_id, email, role, created_by, accepted_at) "
                "values (gen_random_uuid(), :org_id, :email, :role, :created_by, now())"
            ),
            {"org_id": org_id, "email": email, "role": role, "created_by": created_by},
        )
        await session.commit()
        return InviteResult(result="member_added", email=email, role=role)

    pending = (
        await session.execute(
            text(
                "select id from public.org_invites where org_id = :org_id "
                "and lower(email) = :email and accepted_at is null limit 1"
            ),
            {"org_id": org_id, "email": email},
        )
    ).scalar_one_or_none()
    if pending is None:
        await session.execute(
            text(
                "insert into public.org_invites (id, org_id, email, role, created_by) "
                "values (gen_random_uuid(), :org_id, :email, :role, :created_by)"
            ),
            {"org_id": org_id, "email": email, "role": role, "created_by": created_by},
        )
        await session.commit()
    return InviteResult(result="invite_pending", email=email, role=role)


@router.patch("/members/{user_id}", response_model=MemberResult)
async def update_member_role(
    user_id: UUID,
    payload: RoleUpdate,
    principal: Principal = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
) -> MemberResult:
    role = _check_role(payload.role)
    org_id = str(principal.org_id)

    current = (
        await session.execute(
            text(
                "select role from public.memberships "
                "where org_id = :org_id and user_id = :user_id"
            ),
            {"org_id": org_id, "user_id": str(user_id)},
        )
    ).scalar_one_or_none()
    if current is None:
        raise HTTPException(status_code=404, detail="no such member in your org")

    if current == "admin" and role != "admin":
        admins = (
            await session.execute(
                text(
                    "select count(*) from public.memberships "
                    "where org_id = :org_id and role = 'admin'"
                ),
                {"org_id": org_id},
            )
        ).scalar_one()
        if int(admins or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail="cannot demote the last admin of the org; promote someone else first",
            )

    await session.execute(
        text(
            "update public.memberships set role = :role "
            "where org_id = :org_id and user_id = :user_id"
        ),
        {"role": role, "org_id": org_id, "user_id": str(user_id)},
    )
    await session.commit()
    return MemberResult(user_id=str(user_id), role=role)


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: UUID,
    principal: Principal = Depends(require_org_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    deleted = (
        await session.execute(
            text(
                "delete from public.org_invites "
                "where id = :invite_id and org_id = :org_id and accepted_at is null "
                "returning id::text"
            ),
            {"invite_id": str(invite_id), "org_id": str(principal.org_id)},
        )
    ).scalar_one_or_none()
    if deleted is None:
        raise HTTPException(status_code=404, detail="no such pending invite")
    await session.commit()
    return {"deleted": deleted}

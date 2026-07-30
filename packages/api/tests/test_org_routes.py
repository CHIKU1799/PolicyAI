"""Worker tests for the /org team-management routes.

No live DB or Supabase needed: the resolved principal and the DB session are
faked via FastAPI dependency overrides. ``FakeSession`` dispatches on the
distinctive fragments of org.py's text() SQL and records every statement, so
tests can assert both the HTTP behavior and what would have hit the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from policyai_api import deps
from policyai_api.auth import Principal, resolve_principal
from policyai_api.main import app

ORG_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def org_admin() -> Principal:
    return Principal(USER_ID, "admin@firm.in", ORG_ID, False, "admin")


def org_member() -> Principal:
    return Principal(USER_ID, "member@firm.in", ORG_ID, False, "member")


def platform_admin() -> Principal:
    return Principal(USER_ID, "ops@policyai.in", ORG_ID, True, None)


class FakeResult:
    def __init__(self, rows: list[tuple] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def all(self) -> list[tuple]:
        return self._rows

    def first(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        return self._scalar


class FakeSession:
    """Answers org.py's text() queries from canned values; records all SQL."""

    def __init__(
        self,
        *,
        auth_user_id: str | None = None,
        member_rows: list[tuple] | None = None,
        member_role: str | None = None,
        admin_count: int = 1,
        pending_invite_id: str | None = None,
        deletable_invite: bool = False,
    ) -> None:
        self.auth_user_id = auth_user_id
        self.member_rows = member_rows or []
        self.member_role = member_role
        self.admin_count = admin_count
        self.pending_invite_id = pending_invite_id
        self.deletable_invite = deletable_invite
        self.statements: list[tuple[str, dict]] = []
        self.committed = False

    async def execute(self, stmt: Any, params: dict | None = None) -> FakeResult:
        sql = " ".join(str(stmt).split()).lower()
        self.statements.append((sql, params or {}))
        if "left join auth.users" in sql:
            return FakeResult(rows=self.member_rows)
        if "from auth.users" in sql:
            return FakeResult(scalar=self.auth_user_id)
        if "select id from public.org_invites" in sql:
            return FakeResult(scalar=self.pending_invite_id)
        if sql.startswith("select id::text, email"):
            return FakeResult(rows=[])
        if "select role from public.memberships" in sql:
            return FakeResult(scalar=self.member_role)
        if "select count(*) from public.memberships" in sql:
            return FakeResult(scalar=self.admin_count)
        if "delete from public.org_invites" in sql:
            return FakeResult(scalar=str(uuid4()) if self.deletable_invite else None)
        return FakeResult()

    async def commit(self) -> None:
        self.committed = True

    def sql_matching(self, fragment: str) -> list[tuple[str, dict]]:
        return [(sql, p) for sql, p in self.statements if fragment in sql]


ClientFactory = Callable[[Principal, FakeSession], TestClient]


@pytest.fixture
def make_client() -> Iterator[ClientFactory]:
    def factory(principal: Principal, session: FakeSession) -> TestClient:
        async def _session() -> AsyncIterator[FakeSession]:
            yield session

        app.dependency_overrides[resolve_principal] = lambda: principal
        app.dependency_overrides[deps.get_session] = _session
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def test_non_admin_member_gets_403(make_client: ClientFactory) -> None:
    session = FakeSession()
    client = make_client(org_member(), session)
    assert client.get("/org/members").status_code == 403
    assert client.get("/org/invites").status_code == 403
    resp = client.post("/org/invites", json={"email": "new@firm.in", "role": "member"})
    assert resp.status_code == 403
    assert client.patch(f"/org/members/{uuid4()}", json={"role": "admin"}).status_code == 403
    assert client.delete(f"/org/invites/{uuid4()}").status_code == 403
    # Nothing ever reached the database.
    assert session.statements == []


def test_platform_admin_passes_org_admin_guard(make_client: ClientFactory) -> None:
    rows = [(str(USER_ID), "admin@firm.in", "admin", "2026-07-01")]
    client = make_client(platform_admin(), FakeSession(member_rows=rows))
    resp = client.get("/org/members")
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "user_id": str(USER_ID),
            "email": "admin@firm.in",
            "role": "admin",
            "joined_at": "2026-07-01",
        }
    ]


def test_last_admin_demotion_refused(make_client: ClientFactory) -> None:
    session = FakeSession(member_role="admin", admin_count=1)
    client = make_client(org_admin(), session)
    resp = client.patch(f"/org/members/{USER_ID}", json={"role": "member"})
    assert resp.status_code == 409
    assert "last admin" in resp.json()["detail"]
    assert session.sql_matching("update public.memberships") == []


def test_demotion_allowed_when_another_admin_exists(make_client: ClientFactory) -> None:
    session = FakeSession(member_role="admin", admin_count=2)
    client = make_client(org_admin(), session)
    resp = client.patch(f"/org/members/{USER_ID}", json={"role": "member"})
    assert resp.status_code == 200
    assert resp.json() == {"user_id": str(USER_ID), "role": "member"}
    updates = session.sql_matching("update public.memberships")
    assert len(updates) == 1
    assert updates[0][1]["role"] == "member"
    assert session.committed


def test_promote_unknown_member_is_404(make_client: ClientFactory) -> None:
    session = FakeSession(member_role=None)
    client = make_client(org_admin(), session)
    resp = client.patch(f"/org/members/{uuid4()}", json={"role": "admin"})
    assert resp.status_code == 404


def test_invalid_role_rejected(make_client: ClientFactory) -> None:
    client = make_client(org_admin(), FakeSession(member_role="member"))
    resp = client.patch(f"/org/members/{USER_ID}", json={"role": "superuser"})
    assert resp.status_code == 422


def test_invite_existing_user_adds_membership_immediately(make_client: ClientFactory) -> None:
    existing_uid = str(uuid4())
    session = FakeSession(auth_user_id=existing_uid)
    client = make_client(org_admin(), session)
    resp = client.post("/org/invites", json={"email": "Jane.Doe@Firm.IN", "role": "member"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "member_added", "email": "jane.doe@firm.in", "role": "member"}

    inserts = session.sql_matching("insert into public.memberships")
    assert len(inserts) == 1
    assert inserts[0][1]["user_id"] == existing_uid
    assert inserts[0][1]["org_id"] == str(ORG_ID)
    # The audit invite row is stamped accepted at creation time.
    invite_inserts = session.sql_matching("insert into public.org_invites")
    assert len(invite_inserts) == 1
    assert "accepted_at" in invite_inserts[0][0]
    assert invite_inserts[0][1]["email"] == "jane.doe@firm.in"
    assert session.committed


def test_invite_unknown_user_stays_pending(make_client: ClientFactory) -> None:
    session = FakeSession(auth_user_id=None)
    client = make_client(org_admin(), session)
    resp = client.post("/org/invites", json={"email": "NEW@firm.in", "role": "admin"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "invite_pending", "email": "new@firm.in", "role": "admin"}
    assert session.sql_matching("insert into public.memberships") == []
    invite_inserts = session.sql_matching("insert into public.org_invites")
    assert len(invite_inserts) == 1
    assert "accepted_at" not in invite_inserts[0][0]


def test_duplicate_pending_invite_not_reinserted(make_client: ClientFactory) -> None:
    session = FakeSession(auth_user_id=None, pending_invite_id=str(uuid4()))
    client = make_client(org_admin(), session)
    resp = client.post("/org/invites", json={"email": "new@firm.in", "role": "member"})
    assert resp.status_code == 200
    assert resp.json()["result"] == "invite_pending"
    assert session.sql_matching("insert into public.org_invites") == []


def test_cancel_missing_invite_is_404(make_client: ClientFactory) -> None:
    client = make_client(org_admin(), FakeSession(deletable_invite=False))
    assert client.delete(f"/org/invites/{uuid4()}").status_code == 404


def test_cancel_pending_invite(make_client: ClientFactory) -> None:
    session = FakeSession(deletable_invite=True)
    client = make_client(org_admin(), session)
    resp = client.delete(f"/org/invites/{uuid4()}")
    assert resp.status_code == 200
    assert session.committed

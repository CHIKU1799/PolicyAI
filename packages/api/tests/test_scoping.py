"""Org-scoping and hardening regression tests.

Covers the fixes from the security audit:
  * /documents/process refuses anonymous callers, path traversal, foreign-org
    storage paths, and disallowed file types;
  * /timeline/{node_id} filters obligations, gaps, and audit events by the
    caller's org (previously it leaked every org's rows for a regulation);
  * the internal-endpoint secret guard fails closed and compares in constant time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from policyai_api import deps, ratelimit
from policyai_api.auth import Principal, resolve_principal
from policyai_api.deps import require_internal_secret
from policyai_api.main import app
from policyai_graph.models import Node

ORG_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_ORG = UUID("33333333-3333-3333-3333-333333333333")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DEMO_ORG = UUID("00000000-0000-0000-0000-000000000001")


def authenticated() -> Principal:
    return Principal(USER_ID, "user@firm.in", ORG_ID, False, "admin")


def anonymous() -> Principal:
    return Principal(None, None, DEMO_ORG, False)


class FakeORMResult:
    """Answers both row-style and ORM-style result access with canned values."""

    def __init__(self, scalar: Any = None, items: list[Any] | None = None) -> None:
        self._scalar = scalar
        self._items = items or []

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> FakeORMResult:
        return self

    def all(self) -> list[Any]:
        return self._items


class RecordingSession:
    """Records every statement's compiled SQL; dispatches canned results."""

    def __init__(self, node: Node | None = None) -> None:
        self.node = node
        self.statements: list[str] = []

    async def execute(self, stmt: Any, params: Any = None) -> FakeORMResult:
        sql = " ".join(str(stmt).split()).lower()
        self.statements.append(sql)
        # The initial lookup is WHERE nodes.id = ...; the lineage walk queries
        # WHERE nodes.superseded_by_node_id = ... and must find nothing.
        if "from nodes" in sql and "where nodes.id =" in sql:
            return FakeORMResult(scalar=self.node)
        return FakeORMResult()

    async def commit(self) -> None:  # pragma: no cover - not reached in these tests
        pass

    def sql_matching(self, fragment: str) -> list[str]:
        return [s for s in self.statements if fragment in s]


@pytest.fixture
def make_client() -> Iterator[Any]:
    def factory(principal: Principal, session: Any) -> TestClient:
        async def _session() -> AsyncIterator[Any]:
            yield session

        app.dependency_overrides[resolve_principal] = lambda: principal
        app.dependency_overrides[deps.get_session] = _session
        app.dependency_overrides[deps.get_llm] = lambda: None
        return TestClient(app)

    ratelimit.clear()
    yield factory
    ratelimit.clear()
    app.dependency_overrides.clear()


# --- /documents/process hardening ------------------------------------------


def _process_payload(**overrides: Any) -> dict:
    payload = {
        "storage_path": f"{ORG_ID}/1700000000-policy.pdf",
        "filename": "policy.pdf",
        "mime": "application/pdf",
    }
    payload.update(overrides)
    return payload


def test_process_document_rejects_anonymous(make_client: Any) -> None:
    client = make_client(anonymous(), RecordingSession())
    resp = client.post("/documents/process", json=_process_payload())
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "bad_path",
    [
        "../secrets/service.json",
        "11111111-1111-1111-1111-111111111111/../other/file.pdf",
        "/etc/passwd",
        "11111111-1111-1111-1111-111111111111\\file.pdf",
        "",
        "  spaced.pdf",
    ],
)
def test_process_document_rejects_traversal_paths(make_client: Any, bad_path: str) -> None:
    session = RecordingSession()
    client = make_client(authenticated(), session)
    resp = client.post("/documents/process", json=_process_payload(storage_path=bad_path))
    assert resp.status_code == 422
    assert session.statements == []  # refused before any DB or storage access


def test_process_document_rejects_foreign_org_prefix(make_client: Any) -> None:
    session = RecordingSession()
    client = make_client(authenticated(), session)
    resp = client.post(
        "/documents/process",
        json=_process_payload(storage_path=f"{OTHER_ORG}/1700000000-policy.pdf"),
    )
    assert resp.status_code == 403
    assert "organization's folder" in resp.json()["detail"]
    assert session.statements == []


def test_process_document_rejects_unprefixed_path(make_client: Any) -> None:
    client = make_client(authenticated(), RecordingSession())
    resp = client.post(
        "/documents/process", json=_process_payload(storage_path="1700000000-policy.pdf")
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("bad_name", ["malware.exe", "archive.zip", "noext", "image.png"])
def test_process_document_rejects_disallowed_types(make_client: Any, bad_name: str) -> None:
    client = make_client(authenticated(), RecordingSession())
    resp = client.post("/documents/process", json=_process_payload(filename=bad_name))
    assert resp.status_code == 415


def test_process_document_rejects_oversize_file(
    make_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from policyai_api.routes import documents as documents_route

    async def fake_download(path: str) -> bytes:
        return b"x" * (2 * 1024 * 1024)

    monkeypatch.setattr(documents_route, "download_from_storage", fake_download)
    monkeypatch.setenv("UPLOAD_MAX_MB", "1")
    client = make_client(authenticated(), RecordingSession())
    resp = client.post("/documents/process", json=_process_payload())
    assert resp.status_code == 413


# --- /timeline/{node_id} org scoping ----------------------------------------


def _regulation_node() -> Node:
    node = Node(node_type="regulation", properties={"title": "Test Regulation"})
    node.id = uuid4()
    node.is_current = True
    node.effective_from = None
    node.effective_to = None
    node.invalidated_at = None
    node.superseded_by_node_id = None
    return node


def test_timeline_scopes_tenant_rows_to_caller_org(make_client: Any) -> None:
    node = _regulation_node()
    session = RecordingSession(node=node)
    client = make_client(authenticated(), session)
    resp = client.get(f"/timeline/{node.id}")
    assert resp.status_code == 200
    assert resp.json()["obligations"] == []

    obligation_queries = session.sql_matching("from obligations")
    assert obligation_queries, "timeline must query obligations"
    assert all("obligations.org_id" in q for q in obligation_queries)
    event_queries = session.sql_matching("from audit_events")
    assert event_queries, "timeline must query audit events"
    assert all("audit_events.org_id" in q for q in event_queries)


def test_timeline_ignores_requested_org_for_non_admin(make_client: Any) -> None:
    node = _regulation_node()
    session = RecordingSession(node=node)
    client = make_client(authenticated(), session)
    # A non-admin naming another org must still be pinned to their own org:
    # the org filter appears, and effective_org discards the request value.
    resp = client.get(f"/timeline/{node.id}", params={"org_id": str(OTHER_ORG)})
    assert resp.status_code == 200
    assert all("obligations.org_id" in q for q in session.sql_matching("from obligations"))


# --- internal secret guard ---------------------------------------------------


def test_internal_secret_fails_closed_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_internal_secret("")
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException):
        require_internal_secret("anything")


def test_internal_secret_rejects_wrong_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_SECRET", "s3cret")
    with pytest.raises(HTTPException):
        require_internal_secret("nope")
    with pytest.raises(HTTPException):
        require_internal_secret("")


def test_internal_secret_accepts_correct_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_SECRET", "s3cret")
    assert require_internal_secret("s3cret") is None

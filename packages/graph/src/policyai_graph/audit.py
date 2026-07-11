"""Append-only audit trail — the 'who/what/when changed' timeline.

Every governance-relevant state change (obligation created/invalidated, gap
opened/closed, control tested, policy approved, regulation superseded) writes one
``AuditEvent`` row here. Rows are never updated or deleted, so the table is an
authoritative record of *when* each compliance fact came into or went out of force.
Callers commit.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.models_app import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    entity_type: str,
    action: str,
    entity_id: UUID | None = None,
    org_id: UUID | None = None,
    actor: str = "system",
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        org_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        detail=detail or {},
    )
    session.add(event)
    return event

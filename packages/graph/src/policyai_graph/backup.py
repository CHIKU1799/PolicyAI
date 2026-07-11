"""Logical backup / export of the compliance knowledge graph.

Supabase gives you physical backups (PITR / daily snapshots), but those are tied to
the provider and the exact Postgres version. This module produces a *portable*,
provider-independent JSON snapshot of the irreplaceable data — the knowledge graph
(nodes + edges) and the whole compliance state (regulations' requirements,
obligations, gaps, tasks, controls, company profiles, and the append-only audit
trail). It can be diffed, archived off-Supabase, and reloaded into a fresh
database, so the platform survives a provider outage or an accidental drop.

Embeddings are excluded by default: they are large (1024 floats/row) and fully
re-derivable from the text, so leaving them out keeps the snapshot lean. Pass
``include_embeddings=True`` for a byte-exact copy.

CLI:
    python -m policyai_graph.backup [out.json] [--include-embeddings]

A native ``pg_dump`` (for in-place Postgres restore) is also available via
``scripts/backup_db.sh`` / ``make backup``; this JSON export is the portable one.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import Edge, Node, RawDocument
from policyai_graph.models_app import (
    AuditEvent,
    CompanyProfile,
    Control,
    Gap,
    Obligation,
    Requirement,
    Task,
)

SCHEMA_VERSION = 1

# (model, columns) for each exported table. Order matters for a clean reload:
# graph structure first, then the compliance state that references it.
_EXPORT_SPEC: list[tuple[type, list[str]]] = [
    (
        Node,
        [
            "id",
            "node_type",
            "properties",
            "effective_from",
            "effective_to",
            "recorded_at",
            "invalidated_at",
            "superseded_by_node_id",
            "is_current",
            "created_at",
        ],
    ),
    (
        Edge,
        [
            "id",
            "source_id",
            "target_id",
            "edge_type",
            "properties",
            "valid_from",
            "valid_to",
            "invalidated_at",
            "created_at",
        ],
    ),
    (
        Requirement,
        [
            "id",
            "org_id",
            "regulation_node_id",
            "text",
            "requirement_type",
            "applies_to",
            "frequency",
            "citation",
            "evidence_expected",
            "penalty",
            "seq",
            "effective_date",
            "valid_to",
            "invalidated_at",
            "superseded_by_id",
            "created_at",
        ],
    ),
    (
        Obligation,
        [
            "id",
            "org_id",
            "regulation_node_id",
            "title",
            "summary",
            "what_changed",
            "gap_analysis",
            "severity",
            "status",
            "obligation_type",
            "frequency",
            "regulatory_citation",
            "penalty_summary",
            "evidence_required",
            "mapping_confidence",
            "relevance_rationale",
            "effective_date",
            "valid_to",
            "invalidated_at",
            "superseded_by_id",
            "created_at",
        ],
    ),
    (
        Gap,
        [
            "id",
            "org_id",
            "obligation_id",
            "requirement_id",
            "description",
            "severity",
            "status",
            "remediation_plan",
            "owner",
            "due_date",
            "effective_date",
            "valid_to",
            "invalidated_at",
            "superseded_by_id",
            "created_at",
        ],
    ),
    (
        Task,
        [
            "id",
            "org_id",
            "obligation_id",
            "deadline_node_id",
            "title",
            "description",
            "owner",
            "due_date",
            "priority",
            "status",
            "created_at",
        ],
    ),
    (
        Control,
        [
            "id",
            "org_id",
            "ref_code",
            "title",
            "description",
            "control_type",
            "frequency",
            "owner",
            "effectiveness",
            "active",
            "effective_date",
            "valid_to",
            "invalidated_at",
            "superseded_by_id",
            "created_at",
        ],
    ),
    (CompanyProfile, ["id", "org_id", "entity_classes", "topics", "regulators", "notes"]),
    (
        AuditEvent,
        ["id", "org_id", "entity_type", "entity_id", "action", "actor", "detail", "created_at"],
    ),
]

# RawDocument is exported separately so embeddings can be toggled.
_RAWDOC_COLS = [
    "id",
    "source",
    "source_id",
    "source_url",
    "title",
    "raw_text",
    "published_date",
    "content_hash",
    "regulation_node_id",
    "fetched_at",
]


def _jsonable(value: Any) -> Any:
    """Coerce a column value to something json.dumps can handle."""
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize_row(obj: Any, columns: list[str]) -> dict:
    return {c: _jsonable(getattr(obj, c)) for c in columns}


async def export_graph(session: AsyncSession, *, include_embeddings: bool = False) -> dict:
    """Build the full portable snapshot as a JSON-serializable dict."""
    tables: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}

    for model, cols in _EXPORT_SPEC:
        rows = (await session.execute(select(model))).scalars().all()
        tables[model.__tablename__] = [serialize_row(r, cols) for r in rows]
        counts[model.__tablename__] = len(rows)

    raw_cols = list(_RAWDOC_COLS)
    if include_embeddings:
        raw_cols.append("embedding")
    raw_rows = (await session.execute(select(RawDocument))).scalars().all()
    tables["raw_documents"] = [
        {
            **serialize_row(r, _RAWDOC_COLS),
            **(
                {"embedding": list(r.embedding) if r.embedding is not None else None}
                if include_embeddings
                else {}
            ),
        }
        for r in raw_rows
    ]
    counts["raw_documents"] = len(raw_rows)

    alembic_version = (
        (await session.execute(text("select version_num from alembic_version"))).scalars().first()
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "alembic_version": alembic_version,
        "include_embeddings": include_embeddings,
        "counts": counts,
        "tables": tables,
    }


async def _run(out: Path, *, include_embeddings: bool, stamp: str) -> dict:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    try:
        async with sm() as session:
            snapshot = await export_graph(session, include_embeddings=include_embeddings)
    finally:
        await engine.dispose()
    snapshot["exported_at"] = stamp
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, default=str))
    return snapshot


def main() -> int:
    ap = argparse.ArgumentParser(description="Export the compliance graph to portable JSON.")
    ap.add_argument(
        "out",
        type=Path,
        nargs="?",
        default=None,
        help="output path (default backups/graph-<UTC timestamp>.json)",
    )
    ap.add_argument("--include-embeddings", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or Path("backups") / f"graph-{stamp}.json"
    snapshot = asyncio.run(_run(out, include_embeddings=args.include_embeddings, stamp=stamp))
    total = sum(snapshot["counts"].values())
    print(f"exported {total} rows across {len(snapshot['counts'])} tables -> {out}")
    for tbl, n in sorted(snapshot["counts"].items()):
        print(f"  {tbl:22s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

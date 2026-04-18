from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 1024


class Base(DeclarativeBase):
    pass


class NodeType(StrEnum):
    REGULATION = "regulation"
    REGULATOR = "regulator"
    ENTITY_CLASS = "entity_class"
    PARENT_ACT = "parent_act"
    TOPIC = "topic"
    DEADLINE = "deadline"


class EdgeType(StrEnum):
    AMENDS = "amends"
    SUPERSEDES = "supersedes"
    ISSUED_BY = "issued_by"
    APPLIES_TO = "applies_to"
    DERIVED_FROM = "derived_from"
    COVERS_TOPIC = "covers_topic"
    HAS_DEADLINE = "has_deadline"
    REFERENCES = "references"


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    outgoing_edges: Mapped[list[Edge]] = relationship(
        "Edge",
        foreign_keys="Edge.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list[Edge]] = relationship(
        "Edge",
        foreign_keys="Edge.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Node(id={self.id}, type={self.node_type!r}, props={self.properties!r})"


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(String(32), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped[Node] = relationship(
        Node, foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target: Mapped[Node] = relationship(
        Node, foreign_keys=[target_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "edge_type", name="uq_edge_triple"),
    )

    def __repr__(self) -> str:
        return (
            f"Edge(type={self.edge_type!r}, "
            f"source={self.source_id}, target={self.target_id})"
        )


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    regulation_node_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_raw_document_source_id"),
    )

    def __repr__(self) -> str:
        return f"RawDocument(source={self.source!r}, id={self.source_id!r})"

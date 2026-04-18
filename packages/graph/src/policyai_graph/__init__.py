"""Knowledge graph storage and queries over PostgreSQL + pgvector."""

from policyai_graph.db import get_database_url, make_engine, make_sessionmaker
from policyai_graph.models import (
    EMBEDDING_DIM,
    Base,
    Edge,
    EdgeType,
    Node,
    NodeType,
    RawDocument,
)

__version__ = "0.1.0"
__all__ = [
    "EMBEDDING_DIM",
    "Base",
    "Edge",
    "EdgeType",
    "Node",
    "NodeType",
    "RawDocument",
    "get_database_url",
    "make_engine",
    "make_sessionmaker",
]

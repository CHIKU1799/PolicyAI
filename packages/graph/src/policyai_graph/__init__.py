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
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    Alert,
    AlertKind,
    CompanyDocument,
    CompanyProfile,
    DocumentStatus,
    MonitoringSource,
    Obligation,
    ObligationStatus,
    Priority,
    ScanRun,
    ScanStatus,
    Severity,
    Task,
    TaskStatus,
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
    "DEFAULT_ORG_ID",
    "Alert",
    "AlertKind",
    "CompanyDocument",
    "CompanyProfile",
    "DocumentStatus",
    "MonitoringSource",
    "Obligation",
    "ObligationStatus",
    "Priority",
    "ScanRun",
    "ScanStatus",
    "Severity",
    "Task",
    "TaskStatus",
    "get_database_url",
    "make_engine",
    "make_sessionmaker",
]

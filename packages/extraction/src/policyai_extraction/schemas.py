"""Pydantic schemas for structured extraction from regulatory documents.

These define the shape Claude must return (via forced tool use) and the contract
the graph pipeline upserts from. Field names map onto graph node/edge types:
``entity_classes`` -> APPLIES_TO, ``topics`` -> COVERS_TOPIC, ``deadlines`` ->
HAS_DEADLINE, ``amends``/``supersedes`` -> AMENDS/SUPERSEDES.

Keep these schemas free of the JSON-schema keywords Claude's tool layer dislikes
(no min/max length, no regex) — validation lives in Python, not the schema.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ExtractedDeadline(BaseModel):
    description: str = Field(description="What must be done by this date.")
    due_date: date | None = Field(
        default=None,
        description="Absolute calendar date resolved against the document's "
        "publication date. Null if the document states no dated obligation.",
    )
    relative_text: str | None = Field(
        default=None,
        description="The original phrasing if relative, e.g. 'within 90 days of this circular'.",
    )


class ExtractedReference(BaseModel):
    title: str = Field(description="Title or number of the referenced regulation.")
    relationship: str = Field(
        description="One of: amends, supersedes, references, derived_from.",
    )


class ExtractedRegulation(BaseModel):
    """The structured form of a single regulatory document."""

    title: str = Field(description="Official title of the circular/notification.")
    regulator_key: str = Field(
        description="Canonical key of the issuing regulator: rbi, sebi, irdai, or mca.",
    )
    department: str | None = Field(
        default=None,
        description="Issuing sub-department canonical key if identifiable, e.g. rbi.dor.",
    )
    summary: str = Field(description="2-4 sentence plain-English summary of what this does.")
    entity_classes: list[str] = Field(
        default_factory=list,
        description="Canonical keys of entity classes this applies to, e.g. ['nbfc', 'nbfc_mfi']. "
        "Use the seeded vocabulary; omit anything that does not match.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Normalized compliance topics, e.g. ['kyc', 'capital_adequacy', "
        "'fair_practices_code']. Lowercase snake_case.",
    )
    deadlines: list[ExtractedDeadline] = Field(default_factory=list)
    references: list[ExtractedReference] = Field(default_factory=list)
    severity: str = Field(
        default="medium",
        description="Compliance impact: critical, high, medium, low, or informational.",
    )


class CompanyProfileExtraction(BaseModel):
    """Derived applicability fingerprint for a company, from its uploaded docs."""

    entity_classes: list[str] = Field(
        default_factory=list,
        description="Canonical entity-class keys the company operates as.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Compliance topics relevant to this company.",
    )
    regulators: list[str] = Field(
        default_factory=list,
        description="Canonical regulator keys the company is subject to.",
    )
    rationale: str | None = Field(
        default=None, description="Short justification grounded in the uploaded documents."
    )


class ObligationMapping(BaseModel):
    """Claude's analysis of how one regulation obliges one company."""

    is_relevant: bool = Field(description="Whether this regulation applies to the company.")
    title: str = Field(description="Short obligation title.")
    summary: str = Field(description="Plain-English statement of what the company must do.")
    what_changed: str | None = Field(
        default=None, description="What is new versus prior regulations, if anything."
    )
    gap_analysis: str | None = Field(
        default=None,
        description="Gap between this obligation and the company's existing policy documents.",
    )
    severity: str = Field(default="medium")
    tasks: list[MappedTask] = Field(default_factory=list)


class MappedTask(BaseModel):
    title: str = Field(description="Concrete action a human must take.")
    description: str | None = None
    suggested_owner: str | None = Field(
        default=None, description="Role or named person who should own this (if known)."
    )
    due_date: date | None = None
    priority: str = Field(default="medium", description="urgent, high, medium, or low.")


# Resolve forward reference (MappedTask used before definition).
ObligationMapping.model_rebuild()

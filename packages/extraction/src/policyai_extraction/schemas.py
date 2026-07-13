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
    # Open models sometimes omit the description (or put it in relative_text);
    # default to "" and let the pipeline fall back / skip rather than fail the doc.
    description: str = Field(default="", description="What must be done by this date.")
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


class ExtractedRequirement(BaseModel):
    """One atomic, actionable compliance requirement stated in the document.

    A single circular usually contains several discrete requirements (a disclosure,
    a reporting obligation, a board-approval mandate, a prohibition…). Extracting
    them individually is what makes the obligation register concrete and auditable.
    """

    text: str = Field(description="The specific requirement, stated imperatively.")
    requirement_type: str = Field(
        default="operational",
        description="One of: disclosure, reporting, recordkeeping, governance, "
        "operational, prohibition, capital, consumer_protection, registration, audit.",
    )
    applies_to: list[str] = Field(
        default_factory=list,
        description="Entity-class canonical keys this specific requirement binds, if narrower "
        "than the whole document. Omit if it applies to all addressees.",
    )
    frequency: str | None = Field(
        default=None,
        description="Cadence if recurring: one_time, daily, monthly, quarterly, half_yearly, "
        "annual, event_driven, ongoing. Null if not periodic.",
    )
    citation: str | None = Field(
        default=None,
        description="The clause/para/section number in the document, "
        "e.g. 'para 4.2' or 'Sec 3(1)'.",
    )
    evidence_expected: str | None = Field(
        default=None,
        description="What a firm would show to prove compliance (a policy, a filing, a register).",
    )
    penalty: str | None = Field(
        default=None,
        description="Stated consequence of non-compliance for this requirement, if any.",
    )


class ExtractedRegulation(BaseModel):
    """The structured form of a single regulatory document."""

    title: str = Field(description="Official title of the circular/notification.")
    regulator_key: str = Field(
        description="Canonical key of the issuing regulator, e.g. rbi, sebi, irdai, mca, "
        "cbdt, cbic, certin, meity, dgft, npci.",
    )
    department: str | None = Field(
        default=None,
        description="Issuing sub-department canonical key if identifiable, e.g. rbi.dor.",
    )
    document_type: str = Field(
        default="circular",
        description="One of: circular, master_direction, master_circular, notification, "
        "guideline, regulation, directive, press_release, act, rule, advisory, faq.",
    )
    reference_number: str | None = Field(
        default=None,
        description="The official document number, "
        "e.g. 'RBI/2026-27/45' or 'SEBI/HO/MRD/2026/123'.",
    )
    summary: str = Field(description="2-4 sentence plain-English summary of what this does.")
    effective_date: date | None = Field(
        default=None,
        description="The date the document comes into force "
        "(may differ from its publication date). Null if not stated.",
    )
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
    requirements: list[ExtractedRequirement] = Field(
        default_factory=list,
        description="The discrete, actionable compliance requirements the document imposes.",
    )
    penalties: list[str] = Field(
        default_factory=list,
        description="Document-level consequences of non-compliance (fines, licence action, etc.).",
    )
    compliance_frequency: str | None = Field(
        default=None,
        description="Overall cadence the document implies, if any (one_time, annual, ongoing…).",
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


class RequirementGap(BaseModel):
    """Coverage of ONE of the regulation's requirements against the company's policies."""

    requirement_index: int = Field(
        description="0-based index into the REQUIREMENTS list provided in the prompt."
    )
    status: str = Field(
        description="covered (the policy already satisfies it), partial (addressed but "
        "incomplete/outdated), missing (not addressed at all), or conflicting (the policy "
        "actively CONTRADICTS the requirement — e.g. it permits what the regulation forbids, "
        "or sets a weaker limit). 'conflicting' is the most serious: it is a live violation.",
    )
    gap_description: str | None = Field(
        default=None,
        description="What is missing, insufficient, or contradictory. Null when 'covered'.",
    )
    evidence_quote: str | None = Field(
        default=None,
        description="The EXACT sentence/clause from the company policy excerpts that covers or "
        "contradicts this requirement — quoted verbatim so the finding is auditable. Null if no "
        "policy passage addresses it (status 'missing').",
    )
    severity: str = Field(
        default="medium", description="critical, high, medium, low — the risk of this gap."
    )
    suggested_action: str | None = Field(
        default=None, description="The remediation to close it (a policy clause, a control)."
    )


class ObligationMapping(BaseModel):
    """Claude's analysis of how one regulation obliges one company."""

    is_relevant: bool = Field(description="Whether this regulation applies to the company.")
    confidence: float = Field(
        default=0.5,
        description="Your confidence (0.0-1.0) that this regulation applies to THIS company, "
        "given its profile. High only when entity classes/topics clearly match.",
    )
    relevance_rationale: str | None = Field(
        default=None,
        description="One sentence: why this does (or doesn't) apply to the company — the specific "
        "entity class / topic / activity that makes it relevant. Grounds the obligation for audit.",
    )
    title: str = Field(description="Short obligation title.")
    summary: str = Field(description="Plain-English statement of what the company must do.")
    obligation_type: str = Field(
        default="operational",
        description="Dominant nature: disclosure, reporting, recordkeeping, governance, "
        "operational, prohibition, capital, consumer_protection, registration, audit.",
    )
    frequency: str | None = Field(
        default=None,
        description="Cadence the company must meet this on (one_time, monthly, quarterly, "
        "annual, ongoing, event_driven). Null if not periodic.",
    )
    regulatory_citation: str | None = Field(
        default=None,
        description="The governing document number / clause the obligation rests on.",
    )
    penalty_summary: str | None = Field(
        default=None, description="Consequence of non-compliance, summarized for the firm."
    )
    evidence_required: str | None = Field(
        default=None, description="What the firm must retain/produce to evidence compliance."
    )
    what_changed: str | None = Field(
        default=None, description="What is new versus prior regulations, if anything."
    )
    gap_analysis: str | None = Field(
        default=None,
        description="Overall gap between this obligation and the company's "
        "existing policy documents.",
    )
    requirement_gaps: list[RequirementGap] = Field(
        default_factory=list,
        description="Per-requirement coverage assessment — one entry per requirement in the "
        "REQUIREMENTS list, in order. This is where the concrete, actionable gaps live.",
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


class ImpactAction(BaseModel):
    action: str = Field(description="A concrete step the firm should take.")
    priority: str = Field(default="short_term", description="immediate, short_term, or monitor.")


class ImpactAssessment(BaseModel):
    """A drafted impact assessment of one regulation for one firm — the Copilot
    'analyst first pass' a compliance officer reviews and edits, not a verdict."""

    applicability: str = Field(
        description="Whether and why this regulation applies to the firm, grounded "
        "in its entity classes and business topics."
    )
    overall_severity: str = Field(
        default="medium", description="critical, high, medium, or low impact on this firm."
    )
    summary: str = Field(description="3-5 sentence executive summary of the impact.")
    affected_areas: list[str] = Field(
        default_factory=list,
        description="Business areas / policy domains affected, "
        "e.g. 'loan pricing', 'KYC onboarding'.",
    )
    key_requirements: list[str] = Field(
        default_factory=list,
        description="The 3-7 requirements that bite hardest for this firm, paraphrased.",
    )
    suggested_actions: list[ImpactAction] = Field(default_factory=list)

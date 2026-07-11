"""Complexity-based model routing — tag each document, send it to a right-sized model.

A two-line "all agency banks open on Sunday" notice and a 40-page master direction
should not cost the same to process. This module tags a document's complexity from
cheap, deterministic signals (length, document type, cross-reference density) and
maps that tag to a model tier per pipeline stage, so trivial documents use a cheap
fast model and dense regulations use the strong one. It cuts spend on a large
ingest without dropping quality where quality matters.

Routing is on by default (``MODEL_ROUTING=true``). Set it false to pin every call
to the stage default (``ANTHROPIC_MODEL_EXTRACTION`` / ``ANTHROPIC_MODEL_MAPPING``).
Each tier is individually overridable via env, e.g. ``MODEL_MAPPING_LOW``.
"""

from __future__ import annotations

import os
from typing import Literal

from policyai_extraction.llm import MODEL_EXTRACTION, MODEL_MAPPING

Complexity = Literal["low", "medium", "high"]

# Default model per (stage, complexity). Extraction never needs opus; mapping (the
# high-stakes "what must we do" reasoning) escalates to opus for non-trivial docs.
_DEFAULTS: dict[tuple[str, Complexity], str] = {
    ("extraction", "low"): "claude-haiku-4-5",
    ("extraction", "medium"): MODEL_EXTRACTION,
    ("extraction", "high"): MODEL_EXTRACTION,
    ("mapping", "low"): "claude-sonnet-4-6",
    ("mapping", "medium"): MODEL_MAPPING,
    ("mapping", "high"): MODEL_MAPPING,
}

# Length thresholds (characters of document body). Tuned to Indian regulatory
# notices: sub-1.5k is a one-point circular; 12k+ is a master direction / framework.
_LOW_MAX = 1500
_HIGH_MIN = 12000

# Document types that are inherently dense regardless of length — bump them up.
_HEAVY_TYPES = {
    "master_direction",
    "master_circular",
    "regulations",
    "framework",
    "guidelines",
    "directions",
}
# Document types that are inherently light — keep them low unless they're long.
_LIGHT_TYPES = {"press_release", "notice", "clarification", "faq"}


def routing_enabled() -> bool:
    return os.getenv("MODEL_ROUTING", "true").lower() not in ("false", "0", "no")


def classify_complexity(
    text: str, document_type: str | None = None, *, reference_count: int = 0
) -> Complexity:
    """Tag a document's processing complexity from deterministic signals."""
    n = len(text or "")
    dtype = (document_type or "").strip().lower()

    # Length is the primary signal.
    if n >= _HIGH_MIN:
        base: Complexity = "high"
    elif n <= _LOW_MAX:
        base = "low"
    else:
        base = "medium"

    # Dense document types escalate one step; light types never exceed medium.
    if dtype in _HEAVY_TYPES and base != "high":
        base = "high" if base == "medium" else "medium"
    elif dtype in _LIGHT_TYPES and base == "high":
        base = "medium"

    # A web of amendments/cross-references signals a complex change set.
    if reference_count >= 5 and base == "low":
        base = "medium"

    return base


def model_for(stage: str, complexity: Complexity) -> str:
    """Resolve the model id for a (stage, complexity), honoring env overrides.

    Override key is ``MODEL_<STAGE>_<COMPLEXITY>`` (upper-case), e.g.
    ``MODEL_MAPPING_HIGH=claude-opus-4-8``.
    """
    override = os.getenv(f"MODEL_{stage.upper()}_{complexity.upper()}")
    if override:
        return override
    return _DEFAULTS.get((stage, complexity), MODEL_EXTRACTION)


def route_model(
    stage: str,
    text: str,
    document_type: str | None = None,
    *,
    reference_count: int = 0,
    default: str | None = None,
) -> tuple[str, Complexity | None]:
    """Pick a model for this document at this stage. Returns (model_id, complexity_tag).

    When routing is disabled, returns (``default`` or the stage default, None) so the
    caller's behavior is unchanged.
    """
    if not routing_enabled():
        fallback = default or (MODEL_MAPPING if stage == "mapping" else MODEL_EXTRACTION)
        return fallback, None
    tag = classify_complexity(text, document_type, reference_count=reference_count)
    return model_for(stage, tag), tag

"""Pure scoring functions for the eval harness — no I/O, no network, unit-tested.

The gold set states the entity classes / topics a document *must* surface (recall
is what matters for compliance — missing an applicable class is the costly error),
plus the expected regulator, document type, and a minimum requirement count.

Recall alone is not enough: a model that emits every class scores perfect recall
while being useless. We therefore also score *precision* against an allowed set
(the expected items plus any explicitly-allowed extras) so hallucinated classes
and topics are penalised, and report F1 as the headline retrieval number.

Aliases let the gold set tolerate surface variants — "Microfinance Institutions",
"NBFC-MFI" and "nbfc_mfi" should all match the canonical key — without resorting
to brittle substring matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from policyai_extraction.grounding import is_grounded

# Maps surface variants the LLM tends to emit to the canonical vocabulary key.
# Kept here (not in the graph seed) because it is an eval-time tolerance, not a
# data-model fact. Extend as real extractions reveal new variants.
DEFAULT_ALIASES: dict[str, str] = {
    "microfinance institution": "nbfc_mfi",
    "microfinance institutions": "nbfc_mfi",
    "nbfc-mfi": "nbfc_mfi",
    "nbfc - microfinance institution": "nbfc_mfi",
    "non-banking financial company": "nbfc",
    "non banking financial company": "nbfc",
    "registered investment adviser": "investment_adviser",
    "investment advisor": "investment_adviser",
    "ria": "investment_adviser",
    "scheduled commercial bank": "scb",
    "small finance bank": "sfb",
    "body corporate": "body_corporate",
    "body corporate (it act)": "body_corporate",
    "fair practices code": "fair_practices_code",
    "grievance redressal": "grievance_redressal",
    "know your customer": "kyc",
    "cyber security": "cyber_security",
    "cybersecurity": "cyber_security",
    "incident reporting": "incident_reporting",
    "master direction": "master_direction",
}


def _norm(s: str) -> str:
    return s.strip().lower()


def _canon(s: str, aliases: dict[str, str] | None) -> str:
    """Normalise then fold through the alias map (and a space/underscore variant)."""
    key = _norm(s)
    if not aliases:
        return key
    if key in aliases:
        return aliases[key]
    spaced = key.replace("_", " ")
    return aliases.get(spaced, key)


def _as_set(items: list[str], aliases: dict[str, str] | None) -> set[str]:
    return {_canon(i, aliases) for i in items}


def set_recall(
    predicted: list[str], gold: list[str], aliases: dict[str, str] | None = None
) -> float:
    """Fraction of gold items the prediction covers (1.0 if gold is empty)."""
    gold_set = _as_set(gold, aliases)
    if not gold_set:
        return 1.0
    pred_set = _as_set(predicted, aliases)
    return len(gold_set & pred_set) / len(gold_set)


def set_precision(
    predicted: list[str], gold_allowed: list[str], aliases: dict[str, str] | None = None
) -> float:
    """Fraction of predicted items that are in the allowed/gold set (1.0 if none predicted)."""
    pred_set = _as_set(predicted, aliases)
    if not pred_set:
        return 1.0
    allowed = _as_set(gold_allowed, aliases)
    return len(pred_set & allowed) / len(pred_set)


def f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class CaseScore:
    name: str
    regulator_ok: bool
    doc_type_ok: bool
    entity_recall: float
    topic_recall: float
    requirements_ok: bool
    relevant_ok: bool  # mapping relevance matched expectation (if evaluated)
    entity_precision: float = 1.0
    topic_precision: float = 1.0
    notes: list[str] = field(default_factory=list)

    @property
    def entity_f1(self) -> float:
        return f1(self.entity_precision, self.entity_recall)

    @property
    def topic_f1(self) -> float:
        return f1(self.topic_precision, self.topic_recall)

    @property
    def passed(self) -> bool:
        # Recall must clear the bar AND precision must not collapse — a model that
        # spams classes to game recall fails on precision.
        return (
            self.regulator_ok
            and self.entity_recall >= 0.5
            and self.entity_precision >= 0.5
            and self.requirements_ok
            and self.relevant_ok
        )


def score_extraction(
    pred: dict, gold: dict, aliases: dict[str, str] | None = DEFAULT_ALIASES
) -> CaseScore:
    """Score one extracted regulation against its gold record.

    ``pred`` keys: regulator_key, document_type, entity_classes, topics, requirements (list).
    ``gold`` keys: regulator_key, document_type, entity_classes_expected, topics_expected,
    min_requirements, [entity_classes_allowed, topics_allowed, is_relevant_expected,
    is_relevant_actual].

    ``*_allowed`` is the superset of acceptable items for precision (defaults to the
    expected set). This lets a doc legitimately surface extra classes without being
    punished, while still catching off-vocabulary hallucinations.
    """
    notes: list[str] = []
    reg_ok = _norm(pred.get("regulator_key", "")) == _norm(gold.get("regulator_key", ""))
    if not reg_ok:
        notes.append(f"regulator {pred.get('regulator_key')!r} != {gold.get('regulator_key')!r}")

    doc_ok = True
    if gold.get("document_type"):
        doc_ok = _canon(pred.get("document_type", ""), aliases) == _canon(
            gold["document_type"], aliases
        )

    ent_expected = gold.get("entity_classes_expected", [])
    ent_allowed = gold.get("entity_classes_allowed", ent_expected)
    ent_recall = set_recall(pred.get("entity_classes", []), ent_expected, aliases)
    ent_precision = set_precision(pred.get("entity_classes", []), ent_allowed, aliases)
    missing_ent = _as_set(ent_expected, aliases) - _as_set(pred.get("entity_classes", []), aliases)
    if missing_ent:
        notes.append(f"missed entity classes: {sorted(missing_ent)}")
    spurious_ent = _as_set(pred.get("entity_classes", []), aliases) - _as_set(ent_allowed, aliases)
    if spurious_ent:
        notes.append(f"spurious entity classes: {sorted(spurious_ent)}")

    topic_expected = gold.get("topics_expected", [])
    topic_allowed = gold.get("topics_allowed", topic_expected)
    topic_recall = set_recall(pred.get("topics", []), topic_expected, aliases)
    topic_precision = set_precision(pred.get("topics", []), topic_allowed, aliases)

    n_req = len(pred.get("requirements", []))
    req_ok = n_req >= gold.get("min_requirements", 0)
    if not req_ok:
        notes.append(f"requirements {n_req} < min {gold.get('min_requirements')}")

    relevant_ok = True
    if "is_relevant_expected" in gold and "is_relevant_actual" in gold:
        relevant_ok = bool(gold["is_relevant_expected"]) == bool(gold["is_relevant_actual"])
        if not relevant_ok:
            notes.append(
                f"relevance {gold['is_relevant_actual']} != expected {gold['is_relevant_expected']}"
            )

    return CaseScore(
        name=gold.get("_name", "?"),
        regulator_ok=reg_ok,
        doc_type_ok=doc_ok,
        entity_recall=ent_recall,
        topic_recall=topic_recall,
        entity_precision=ent_precision,
        topic_precision=topic_precision,
        requirements_ok=req_ok,
        relevant_ok=relevant_ok,
        notes=notes,
    )


def aggregate(scores: list[CaseScore]) -> dict:
    """Roll up case scores into a scorecard dict."""
    n = len(scores) or 1
    return {
        "cases": len(scores),
        "passed": sum(1 for s in scores if s.passed),
        "pass_rate": round(sum(1 for s in scores if s.passed) / n, 3),
        "regulator_accuracy": round(sum(1 for s in scores if s.regulator_ok) / n, 3),
        "doc_type_accuracy": round(sum(1 for s in scores if s.doc_type_ok) / n, 3),
        "entity_recall": round(sum(s.entity_recall for s in scores) / n, 3),
        "entity_precision": round(sum(s.entity_precision for s in scores) / n, 3),
        "entity_f1": round(sum(s.entity_f1 for s in scores) / n, 3),
        "topic_recall": round(sum(s.topic_recall for s in scores) / n, 3),
        "topic_precision": round(sum(s.topic_precision for s in scores) / n, 3),
        "topic_f1": round(sum(s.topic_f1 for s in scores) / n, 3),
        "requirements_ok_rate": round(sum(1 for s in scores if s.requirements_ok) / n, 3),
        "relevance_accuracy": round(sum(1 for s in scores if s.relevant_ok) / n, 3),
    }


# --------------------------------------------------------------------------- #
# Mapping-quality scoring (structural / deterministic — no LLM judge needed).
# --------------------------------------------------------------------------- #


@dataclass
class MappingScore:
    name: str
    relevance_ok: bool
    confidence_ok: bool  # confidence is in [0,1] and present when relevant
    grounded_ok: bool  # every gap cites text present in the provided excerpts/requirements
    severity_ok: bool  # severity is a known level
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.relevance_ok and self.confidence_ok and self.grounded_ok and self.severity_ok


_SEVERITIES = {"critical", "high", "medium", "low"}


def score_mapping(mapping: dict, gold: dict) -> MappingScore:
    """Score one obligation mapping for structural quality and grounding.

    ``mapping`` keys: is_relevant, mapping_confidence, severity, requirement_gaps
    (list of {gap_description|description, status}), gap_analysis.
    ``gold`` keys: is_relevant_expected, [grounding_corpus] — a string the gaps must
    be supported by (concatenated requirement text + policy excerpts), [_name].
    """
    notes: list[str] = []
    is_relevant = bool(mapping.get("is_relevant", True))
    relevance_ok = is_relevant == bool(gold.get("is_relevant_expected", is_relevant))
    if not relevance_ok:
        notes.append(f"relevance {is_relevant} != expected {gold.get('is_relevant_expected')}")

    conf = mapping.get("mapping_confidence")
    confidence_ok = True
    if is_relevant:
        confidence_ok = isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0
        if not confidence_ok:
            notes.append(f"confidence {conf!r} not in [0,1]")

    severity = _norm(str(mapping.get("severity", "medium")))
    severity_ok = severity in _SEVERITIES
    if not severity_ok:
        notes.append(f"unknown severity {severity!r}")

    # Grounding: each gap should reference vocabulary that appears in the corpus.
    # A cheap, deterministic proxy for "did the model invent a gap out of nothing":
    # require meaningful token overlap between the gap text and the corpus.
    grounded_ok = True
    corpus = gold.get("grounding_corpus", "") or ""
    if corpus and is_relevant:
        for gap in mapping.get("requirement_gaps", []) or []:
            text = gap.get("gap_description") or gap.get("description") or ""
            if gap.get("status") == "covered" or not text:
                continue
            if not is_grounded(text, corpus):
                grounded_ok = False
                notes.append(f"ungrounded gap: {text[:60]!r}")

    return MappingScore(
        name=gold.get("_name", "?"),
        relevance_ok=relevance_ok,
        confidence_ok=confidence_ok,
        grounded_ok=grounded_ok,
        severity_ok=severity_ok,
        notes=notes,
    )


def aggregate_mapping(scores: list[MappingScore]) -> dict:
    n = len(scores) or 1
    return {
        "cases": len(scores),
        "passed": sum(1 for s in scores if s.passed),
        "pass_rate": round(sum(1 for s in scores if s.passed) / n, 3),
        "relevance_accuracy": round(sum(1 for s in scores if s.relevance_ok) / n, 3),
        "confidence_valid_rate": round(sum(1 for s in scores if s.confidence_ok) / n, 3),
        "grounded_rate": round(sum(1 for s in scores if s.grounded_ok) / n, 3),
        "severity_valid_rate": round(sum(1 for s in scores if s.severity_ok) / n, 3),
    }

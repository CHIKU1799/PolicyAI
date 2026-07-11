"""Offline tests for the eval harness — scoring math, fixture consistency, and the
relevance gate. The live LLM run (run_eval) is exercised separately with a key."""

from __future__ import annotations

import json

import pytest
from policyai_extraction.eval.baseline import Regression, compare
from policyai_extraction.eval.run_eval import _FIXTURES, _relevance
from policyai_extraction.eval.scoring import (
    DEFAULT_ALIASES,
    aggregate,
    f1,
    score_extraction,
    score_mapping,
    set_precision,
    set_recall,
)
from policyai_extraction.schemas import ExtractedRegulation
from policyai_graph.seed import ENTITY_CLASSES


def test_set_metrics():
    assert set_recall(["a", "b", "c"], ["a", "b"]) == 1.0
    assert set_recall(["a"], ["a", "b"]) == 0.5
    assert set_recall(["x"], []) == 1.0  # nothing required
    assert set_precision(["a", "z"], ["a", "b"]) == 0.5
    assert set_precision([], ["a"]) == 1.0
    assert f1(1.0, 0.5) == pytest.approx(2 / 3)
    assert f1(0.0, 0.0) == 0.0


def test_score_extraction_pass_and_fail():
    gold = {
        "_name": "t",
        "regulator_key": "rbi",
        "document_type": "master_direction",
        "entity_classes_expected": ["nbfc_mfi"],
        "topics_expected": ["fair_practices_code"],
        "min_requirements": 2,
        "is_relevant_expected": True,
        "is_relevant_actual": True,
    }
    good = score_extraction(
        {
            "regulator_key": "rbi",
            "document_type": "master_direction",
            "entity_classes": ["nbfc_mfi", "nbfc"],
            "topics": ["fair_practices_code"],
            "requirements": [{"text": "a"}, {"text": "b"}],
        },
        gold,
    )
    assert good.passed and good.entity_recall == 1.0 and good.regulator_ok

    bad = score_extraction(
        {
            "regulator_key": "sebi",  # wrong regulator
            "document_type": "circular",
            "entity_classes": [],
            "topics": [],
            "requirements": [],
        },
        gold,
    )
    assert not bad.passed
    assert bad.notes  # explains why


def test_aggregate_rolls_up():
    gold = {
        "_name": "t",
        "regulator_key": "rbi",
        "entity_classes_expected": ["nbfc"],
        "min_requirements": 0,
    }
    s = score_extraction(
        {"regulator_key": "rbi", "entity_classes": ["nbfc"], "topics": [], "requirements": []},
        gold,
    )
    card = aggregate([s])
    assert card["cases"] == 1
    assert card["regulator_accuracy"] == 1.0
    assert 0.0 <= card["pass_rate"] <= 1.0


def test_precision_penalises_spam_classes():
    # A model that emits every class gets perfect recall but tanked precision and fails.
    gold = {
        "_name": "t",
        "regulator_key": "rbi",
        "entity_classes_expected": ["nbfc_mfi"],
        "entity_classes_allowed": ["nbfc_mfi", "nbfc"],
        "min_requirements": 0,
    }
    spammy = score_extraction(
        {
            "regulator_key": "rbi",
            "entity_classes": ["nbfc_mfi", "scb", "aif", "mutual_fund", "life_insurer"],
            "topics": [],
            "requirements": [],
        },
        gold,
    )
    assert spammy.entity_recall == 1.0
    assert spammy.entity_precision < 0.5
    assert not spammy.passed  # precision gate catches the spam
    assert any("spurious" in n for n in spammy.notes)


def test_aliases_match_surface_variants():
    gold = {
        "_name": "t",
        "regulator_key": "rbi",
        "entity_classes_expected": ["nbfc_mfi"],
        "topics_expected": ["fair_practices_code"],
        "min_requirements": 0,
        "is_relevant_expected": True,
        "is_relevant_actual": True,
    }
    s = score_extraction(
        {
            "regulator_key": "rbi",
            # surface forms the LLM tends to emit
            "entity_classes": ["Microfinance Institutions"],
            "topics": ["Fair Practices Code"],
            "requirements": [],
        },
        gold,
        aliases=DEFAULT_ALIASES,
    )
    assert s.entity_recall == 1.0 and s.topic_recall == 1.0


def test_score_mapping_flags_hallucinated_gap():
    gold = {
        "_name": "h",
        "is_relevant_expected": True,
        "grounding_corpus": "Lender must disclose the effective interest rate and charges.",
    }
    mapping = {
        "is_relevant": True,
        "mapping_confidence": 0.9,
        "severity": "high",
        "requirement_gaps": [
            {
                "status": "gap",
                "gap_description": "No cryptocurrency custody desk for offshore settlement.",
            }
        ],
    }
    s = score_mapping(mapping, gold)
    assert not s.grounded_ok and not s.passed


def test_score_mapping_accepts_grounded_and_valid():
    gold = {
        "_name": "g",
        "is_relevant_expected": True,
        "grounding_corpus": "Lender must disclose the effective interest rate and charges.",
    }
    mapping = {
        "is_relevant": True,
        "mapping_confidence": 0.8,
        "severity": "high",
        "requirement_gaps": [
            {
                "status": "gap",
                "gap_description": "Factsheet omits the effective interest rate disclosure.",
            }
        ],
    }
    s = score_mapping(mapping, gold)
    assert s.grounded_ok and s.confidence_ok and s.severity_ok and s.passed


def test_score_mapping_rejects_out_of_range_confidence_and_bad_severity():
    s = score_mapping(
        {
            "is_relevant": True,
            "mapping_confidence": 1.7,
            "severity": "urgent",
            "requirement_gaps": [],
        },
        {"_name": "b", "is_relevant_expected": True},
    )
    assert not s.confidence_ok and not s.severity_ok and not s.passed


def test_regression_gate_detects_drop():
    baseline = {"pass_rate": 0.9, "entity_f1": 0.8}
    # within tolerance -> clean
    assert compare({"pass_rate": 0.88, "entity_f1": 0.79}, baseline) == []
    # entity_f1 collapses -> regression reported
    regs = compare({"pass_rate": 0.9, "entity_f1": 0.5}, baseline)
    assert len(regs) == 1 and regs[0].metric == "entity_f1"
    assert isinstance(regs[0], Regression)
    # no baseline -> never blocks
    assert compare({"pass_rate": 0.1}, None) == []


def test_mapping_fixtures_detection_is_perfect():
    # The curated mapping fixtures must be classified exactly as labelled, otherwise
    # the offline gate is meaningless. Mirrors run_eval._run_mapping detection logic.
    gold_all = json.loads((_FIXTURES / "mapping_gold.json").read_text())
    for name, gold in gold_all.items():
        s = score_mapping(gold["mapping"], {**gold, "_name": name})
        assert s.passed == bool(gold["expect_pass"]), name


def test_gold_fixtures_consistent_and_self_relevant():
    gold_all = json.loads((_FIXTURES / "gold.json").read_text())
    valid_classes = {e["canonical_key"] for e in ENTITY_CLASSES}
    for name, gold in gold_all.items():
        assert (_FIXTURES / name).exists(), f"missing fixture {name}"
        # every expected entity class is in the seeded vocabulary (catches typos)
        for ec in gold["entity_classes_expected"]:
            assert ec in valid_classes, f"{name}: unknown entity class {ec}"
        # the relevance gate, fed the gold extraction, reproduces the expected verdict
        if "profile" in gold and "is_relevant_expected" in gold:
            fake = ExtractedRegulation(
                title=name,
                regulator_key=gold["regulator_key"],
                summary="x",
                entity_classes=gold["entity_classes_expected"],
                topics=gold["topics_expected"],
            )
            assert _relevance(fake, gold["profile"]) is gold["is_relevant_expected"], name

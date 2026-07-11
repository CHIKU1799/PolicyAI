"""Run the PolicyAI eval suite and gate on regressions against a committed baseline.

    python -m policyai_extraction.eval.run_eval                # run all suites
    python -m policyai_extraction.eval.run_eval --only mapping # just the offline suite
    python -m policyai_extraction.eval.run_eval --promote      # bless current as baseline

Two suites:
  * extraction — runs the extractor live through the configured LLM (needs a key)
    and scores regulator/doc-type/entity/topic precision+recall and mapping
    relevance against gold fixtures.
  * mapping — fully offline. Scores recorded obligation-mapping outputs for
    structural quality and grounding (confidence in range, gaps supported by the
    source text, valid severity). Always runs, so it can gate CI without keys.

Each suite persists its scorecard under eval/results/ and is compared to
eval/baseline.json; the process exits non-zero if any tracked metric regresses
beyond tolerance or the pass rate falls below ``--min-pass``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from policyai_extraction.eval.baseline import (
    compare,
    load_baseline,
    persist_result,
    promote_baseline,
)
from policyai_extraction.eval.scoring import (
    aggregate,
    aggregate_mapping,
    score_extraction,
    score_mapping,
)
from policyai_extraction.llm import MODEL_EXTRACTION, LLMClient
from policyai_extraction.mapping import _expand_classes
from policyai_extraction.pipeline import load_prompt
from policyai_extraction.schemas import ExtractedRegulation

_FIXTURES = Path(__file__).parent / "fixtures"


def _relevance(extracted: ExtractedRegulation, profile: dict) -> bool:
    """Mirror the mapping relevance gate: class match always qualifies; a topic-only
    match must also come from a regulator the company is subject to."""
    profile_classes = _expand_classes(set(profile.get("entity_classes", [])))
    profile_topics = set(profile.get("topics", []))
    profile_regs = set(profile.get("regulators", []))
    class_hit = set(extracted.entity_classes) & profile_classes
    topic_hit = set(extracted.topics) & profile_topics
    regulator_ok = (not profile_regs) or (extracted.regulator_key in profile_regs)
    return bool(class_hit or (topic_hit and regulator_ok))


# --------------------------------------------------------------------------- #
# Suite: extraction (live LLM)
# --------------------------------------------------------------------------- #
async def _run_extraction() -> dict:
    gold_all = json.loads((_FIXTURES / "gold.json").read_text())
    llm = LLMClient()
    system = load_prompt("regulation_extraction_v1.md")
    scores = []
    try:
        for name, gold in gold_all.items():
            text = (_FIXTURES / name).read_text()
            prompt = (
                f"Document title: {name}\nSource: {gold['regulator_key']}\n"
                f"Published date: {gold.get('published_date', 'unknown')}\n\n"
                f"--- DOCUMENT TEXT ---\n{text[:40000]}"
            )
            extracted = await llm.extract(
                prompt, ExtractedRegulation, system=system, model=MODEL_EXTRACTION
            )
            pred = {
                "regulator_key": extracted.regulator_key,
                "document_type": extracted.document_type,
                "entity_classes": extracted.entity_classes,
                "topics": extracted.topics,
                "requirements": extracted.requirements,
            }
            g = {**gold, "_name": name}
            if "profile" in gold and "is_relevant_expected" in gold:
                g["is_relevant_actual"] = _relevance(extracted, gold["profile"])
            scores.append(score_extraction(pred, g))
    finally:
        await llm.aclose()

    card = aggregate(scores)
    print("\n=== extraction scorecard ===")
    for s in scores:
        flag = "PASS" if s.passed else "FAIL"
        print(
            f"[{flag}] {s.name:32s} reg={int(s.regulator_ok)} "
            f"ent_p={s.entity_precision:.2f} ent_r={s.entity_recall:.2f} "
            f"ent_f1={s.entity_f1:.2f} topic_f1={s.topic_f1:.2f} "
            f"req_ok={int(s.requirements_ok)} relevant_ok={int(s.relevant_ok)}"
        )
        for note in s.notes:
            print(f"        - {note}")
    _print_card(card)
    print(f"\n(cost: {llm.cost.summary()})")
    return card


# --------------------------------------------------------------------------- #
# Suite: mapping (offline, structural)
# --------------------------------------------------------------------------- #
def _run_mapping() -> dict:
    gold_all = json.loads((_FIXTURES / "mapping_gold.json").read_text())
    scores = []
    detected_ok = 0
    print("\n=== mapping scorecard ===")
    for name, gold in gold_all.items():
        g = {**gold, "_name": name}
        s = score_mapping(gold["mapping"], g)
        scores.append(s)
        # Detection accuracy: does the scorer's verdict match the curated label?
        # Good mappings should pass; deliberately-broken ones should be flagged.
        expect = bool(gold.get("expect_pass", True))
        correct = s.passed == expect
        detected_ok += int(correct)
        flag = "OK " if correct else "MISS"
        print(
            f"[{flag}] {s.name:34s} verdict={int(s.passed)} expect={int(expect)} "
            f"rel={int(s.relevance_ok)} conf={int(s.confidence_ok)} "
            f"grounded={int(s.grounded_ok)} sev={int(s.severity_ok)}"
        )
        for note in s.notes:
            print(f"        - {note}")
    card = aggregate_mapping(scores)
    # Headline number for the gate is detection accuracy, not raw pass count —
    # the fixtures intentionally include broken mappings the scorer must catch.
    card["pass_rate"] = round(detected_ok / (len(scores) or 1), 3)
    card["detection_accuracy"] = card["pass_rate"]
    _print_card(card)
    return card


def _print_card(card: dict) -> None:
    print("\nAggregate:")
    for k, v in card.items():
        print(f"  {k:22s} {v}")


def _gate(card: dict, label: str, min_pass: float, timestamp: str) -> int:
    """Persist, compare to baseline, and return a process exit code (0 == ok)."""
    persist_result(card, label=label, timestamp=timestamp)
    failures = []
    if card["pass_rate"] < min_pass:
        failures.append(f"pass_rate {card['pass_rate']} < min {min_pass}")
    regressions = compare(card, (load_baseline() or {}).get(label))
    failures.extend(str(r) for r in regressions)
    if failures:
        print(f"\nFAILED [{label}]:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nOK [{label}]: pass_rate {card['pass_rate']} >= {min_pass}, no regressions")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-pass", type=float, default=0.66)
    ap.add_argument("--only", choices=["extraction", "mapping"], default=None)
    ap.add_argument("--promote", action="store_true", help="bless current results as baseline")
    args = ap.parse_args()

    if args.promote:
        for label in (["extraction", "mapping"] if not args.only else [args.only]):
            try:
                promote_baseline(label)
                print(f"promoted {label} -> baseline.json")
            except FileNotFoundError as exc:
                print(f"skip {label}: {exc}")
        return 0

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rc = 0

    if args.only in (None, "mapping"):
        rc |= _gate(_run_mapping(), "mapping", args.min_pass, timestamp)

    if args.only in (None, "extraction"):
        if os.getenv("LLM_PROVIDER", "anthropic") == "anthropic" and not os.getenv(
            "ANTHROPIC_API_KEY"
        ):
            print("\nANTHROPIC_API_KEY not set — skipping live extraction suite.")
        else:
            rc |= _gate(asyncio.run(_run_extraction()), "extraction", args.min_pass, timestamp)

    return rc


if __name__ == "__main__":
    sys.exit(main())

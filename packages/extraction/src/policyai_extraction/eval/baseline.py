"""Regression gate for the eval harness.

A scorecard on its own tells you today's number; it does not tell you whether a
prompt edit, model swap, or retrieval change made things *worse*. This module
persists every run and compares the headline metrics against a committed
``baseline.json``, failing if any tracked metric drops by more than a tolerance.

Workflow:
    make eval                # runs, writes results/<ts>.json + results/latest.json
    make eval-baseline       # promote latest -> baseline.json (after a deliberate change)

The baseline is committed to git so regressions are caught in review/CI, and the
per-run history under results/ lets you chart drift over time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_EVAL_DIR = Path(__file__).parent
BASELINE_PATH = _EVAL_DIR / "baseline.json"
RESULTS_DIR = _EVAL_DIR / "results"

# Metrics where higher is better, with the max regression we tolerate before
# failing. Small tolerances absorb LLM run-to-run noise; a real regression blows
# straight past them.
TRACKED_METRICS: dict[str, float] = {
    "pass_rate": 0.05,
    "regulator_accuracy": 0.05,
    "entity_recall": 0.05,
    "entity_precision": 0.05,
    "entity_f1": 0.05,
    "topic_f1": 0.05,
    "relevance_accuracy": 0.05,
}


@dataclass
class Regression:
    metric: str
    baseline: float
    current: float
    drop: float

    def __str__(self) -> str:
        return (
            f"{self.metric}: {self.current:.3f} < baseline {self.baseline:.3f} "
            f"(drop {self.drop:.3f})"
        )


def load_baseline(path: Path = BASELINE_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def compare(current: dict, baseline: dict | None) -> list[Regression]:
    """Return the list of metrics that regressed beyond tolerance (empty == clean)."""
    if not baseline:
        return []
    regressions: list[Regression] = []
    for metric, tol in TRACKED_METRICS.items():
        if metric not in current or metric not in baseline:
            continue
        base_v = float(baseline[metric])
        cur_v = float(current[metric])
        if cur_v < base_v - tol:
            regressions.append(Regression(metric, base_v, cur_v, round(base_v - cur_v, 3)))
    return regressions


def persist_result(card: dict, *, label: str, timestamp: str) -> Path:
    """Write the scorecard to results/<label>-<ts>.json and refresh latest.json.

    ``timestamp`` is passed in (not generated here) so the harness stays
    deterministic and testable.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    record = {"label": label, "timestamp": timestamp, **card}
    out = RESULTS_DIR / f"{label}-{timestamp}.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True))
    (RESULTS_DIR / f"{label}-latest.json").write_text(json.dumps(record, indent=2, sort_keys=True))
    return out


def promote_baseline(label: str = "extraction", path: Path = BASELINE_PATH) -> dict:
    """Copy the latest result for ``label`` into the committed baseline."""
    latest = RESULTS_DIR / f"{label}-latest.json"
    if not latest.exists():
        raise FileNotFoundError(f"no latest result to promote: {latest}")
    card = json.loads(latest.read_text())
    existing = load_baseline(path) or {}
    existing[label] = card
    path.write_text(json.dumps(existing, indent=2, sort_keys=True))
    return existing

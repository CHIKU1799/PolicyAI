"""Map a targeted set of regulations, one fresh session each.

``map_all`` re-scans every unmapped regulation on each pass, which is wasteful when
only a known handful still need mapping (e.g. ones that kept dying on a flaky
network). This maps exactly the regulations that still pass the strong entity-class
relevance gate but lack an obligation, using a FRESH session per regulation so a
dropped connection can't poison the next one, with extra retries for network blips.

    uv run python -m policyai_extraction.map_targeted [--attempts 5]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models_app import DEFAULT_ORG_ID, Obligation
from sqlalchemy import text

from policyai_extraction.dbretry import is_transient
from policyai_extraction.llm import LLMClient
from policyai_extraction.mapping import map_obligation

log = logging.getLogger("policyai.map_targeted")

# Entity classes the demo NBFC-MFI is subject to (incl. the auto-expanded parent).
_CLASSES = ["nbfc_mfi", "nbfc", "pmla_reporting_entity"]

_ELIGIBLE_SQL = text("""
    select distinct e.source_id
    from edges e
    join nodes n on n.id = e.target_id
    where e.edge_type = 'applies_to'
      and n.properties->>'canonical_key' = any(:cls)
      and e.source_id not in (select regulation_node_id from obligations)
    """)


async def run(*, attempts: int = 5, org_id=DEFAULT_ORG_ID) -> dict:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    llm = LLMClient()
    tally = {"mapped": 0, "not_relevant": 0, "failed": 0}
    try:
        async with sm() as s:
            ids = [r[0] for r in (await s.execute(_ELIGIBLE_SQL, {"cls": _CLASSES})).all()]
        log.info("%d eligible unmapped regulations", len(ids))

        for rid in ids:
            for attempt in range(1, attempts + 1):
                # Fresh session per attempt: a connection that died on the previous
                # regulation can never carry over and corrupt this one.
                try:
                    async with sm() as s:
                        result = await map_obligation(s, rid, llm, org_id=org_id)
                        await s.commit()
                    if result is not None:
                        tally["mapped"] += 1
                    else:
                        tally["not_relevant"] += 1
                    break
                except Exception as exc:  # noqa: BLE001
                    if is_transient(exc) and attempt < attempts:
                        await asyncio.sleep(2.0 * attempt)
                        log.info("retry %d/%d for %s (transient)", attempt, attempts, rid)
                        continue
                    tally["failed"] += 1
                    log.warning("FAILED %s: %s", rid, str(exc)[:160])
                    break
            # Guard against double-charging: only regenerate an obligation once mapped.
            already = None
            async with sm() as s:
                already = (
                    await s.execute(
                        text("select 1 from obligations where regulation_node_id = :r"),
                        {"r": rid},
                    )
                ).first()
            if already:
                log.info("mapped %s (running: %d)", rid, tally["mapped"])
    finally:
        await llm.aclose()
        await engine.dispose()
    log.info("done: %s", tally)
    log.info("cost: %s", llm.cost.summary())
    return tally


def main() -> int:
    ap = argparse.ArgumentParser(description="Map the eligible-but-unmapped regulations.")
    ap.add_argument("--attempts", type=int, default=5, help="retries per regulation on transient")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    tally = asyncio.run(run(attempts=args.attempts))
    print(tally)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

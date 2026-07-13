"""Build an ingest records.jsonl from a local SEBI circular dump.

Input layout (a pageindex-style scrape):
    <dump>/meta/sebi_circulars_<id>.json   title, date, detail_url, sha256
    <dump>/raw/sebi_circulars_<id>.pdf     the circular itself

Unique-only guarantees:
  - skips notification ids already ingested as (source='sebi', source_id=<id>)
  - skips byte-identical PDFs within the dump (meta sha256)
  - skips titles that normalize to one already in raw_documents for sebi
    (the live crawler stores slug source_ids, so id-dedup alone can't catch
    the overlap with the ~50 crawled circulars)

Usage:
    DATABASE_URL=... uv run python scripts/build_sebi_records.py \
        --dump "/path/to/data/sebi" --out inbox/sebi/records.jsonl
Then:
    make ingest FILE=inbox/sebi/records.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from policyai_graph.db import make_engine
from pypdf import PdfReader
from sqlalchemy import text as sqltext

_WS = re.compile(r"\s+")
_NORM = re.compile(r"[^a-z0-9]+")


def norm_title(t: str) -> str:
    return _NORM.sub(" ", (t or "").lower()).strip()


def pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return _WS.sub(" ", "\n".join(pages)).strip()


async def existing(engine) -> tuple[set[str], set[str]]:
    async with engine.connect() as c:
        ids = {
            r[0]
            for r in await c.execute(
                sqltext("select source_id from raw_documents where source = 'sebi'")
            )
        }
        titles = {
            norm_title(r[0])
            for r in await c.execute(
                sqltext("select title from raw_documents where source = 'sebi'")
            )
        }
    return ids, titles


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", default="inbox/sebi/records.jsonl")
    ap.add_argument("--min-chars", type=int, default=300)
    args = ap.parse_args()

    dump = Path(args.dump)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    engine = make_engine()
    known_ids, known_titles = await existing(engine)
    await engine.dispose()

    seen_sha: set[str] = set()
    seen_titles: set[str] = set(known_titles)
    stats = {"written": 0, "dup_id": 0, "dup_sha": 0, "dup_title": 0, "no_pdf": 0, "thin": 0}

    with out.open("w") as fh:
        for meta_path in sorted(dump.glob("meta/*.json")):
            m = json.loads(meta_path.read_text())
            sid = str(m.get("notification_id") or "").strip()
            title = (m.get("title") or "").strip()
            if not sid or not title:
                continue
            if sid in known_ids:
                stats["dup_id"] += 1
                continue
            sha = m.get("sha256")
            if sha and sha in seen_sha:
                stats["dup_sha"] += 1
                continue
            nt = norm_title(title)
            if nt in seen_titles:
                stats["dup_title"] += 1
                continue
            pdf = dump / "raw" / f"{meta_path.stem}.pdf"
            if not pdf.exists():
                stats["no_pdf"] += 1
                continue
            try:
                body = pdf_text(pdf)
            except Exception as exc:  # noqa: BLE001 - skip unreadable PDFs, keep going
                print(f"  ! {pdf.name}: {type(exc).__name__}: {str(exc)[:80]}")
                stats["no_pdf"] += 1
                continue
            if len(body) < args.min_chars:
                stats["thin"] += 1
                continue
            if sha:
                seen_sha.add(sha)
            seen_titles.add(nt)
            fh.write(
                json.dumps(
                    {
                        "source": "sebi",
                        "source_id": sid,
                        "title": title,
                        "source_url": m.get("detail_url") or m.get("pdf_url") or "",
                        "published_date": m.get("date"),
                        "raw_text": body,
                    }
                )
                + "\n"
            )
            stats["written"] += 1
            if stats["written"] % 200 == 0:
                print(f"  … {stats['written']} records")

    print(json.dumps(stats, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())

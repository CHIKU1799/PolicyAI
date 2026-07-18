"""Pipeline quality report: score every level of the corpus from the DB.

Levels: ingestion -> extraction -> graph integrity -> mapping -> retrieval.
Pure SQL, no LLM spend; run after any batch to catch quality regressions.

    DATABASE_URL=... uv run python scripts/quality_report.py
"""

from __future__ import annotations

import asyncio

from policyai_graph.db import make_engine
from sqlalchemy import text


async def q(conn, sql: str, **params):
    return (await conn.execute(text(sql), params)).fetchall()


async def scalar(conn, sql: str, **params) -> int:
    return int((await conn.execute(text(sql), params)).scalar() or 0)


def line(label: str, value, warn: bool = False) -> None:
    flag = " ⚠" if warn else ""
    print(f"  {label:<46} {value}{flag}")


async def main() -> None:
    engine = make_engine()
    async with engine.connect() as c:
        print("== L1 · Ingestion ==")
        for src, n in await q(
            c, "select source, count(*) from raw_documents group by source order by 2 desc"
        ):
            line(f"documents · {src}", n)
        no_emb = await scalar(c, "select count(*) from raw_documents where embedding is null")
        line("missing embeddings", no_emb, warn=no_emb > 0)
        thin = await scalar(
            c, "select count(*) from raw_documents where length(coalesce(raw_text,'')) < 500"
        )
        line("thin documents (<500 chars)", thin, warn=thin > 20)
        dupes = await scalar(
            c,
            "select count(*) from (select content_hash from raw_documents "
            "group by content_hash having count(*) > 1) d",
        )
        line("duplicate content hashes", dupes, warn=dupes > 5)

        print("\n== L2 · Extraction ==")
        total_regs = await scalar(c, "select count(*) from nodes where node_type='regulation'")
        line("regulation nodes", total_regs)
        no_reqs = await scalar(
            c,
            "select count(*) from nodes where node_type='regulation' "
            "and coalesce((properties->>'requirement_count')::int, 0) = 0",
        )
        line(
            "regs with 0 requirements",
            f"{no_reqs} ({100*no_reqs//max(total_regs,1)}%)",
            warn=no_reqs > total_regs * 0.25,
        )
        no_summary = await scalar(
            c,
            "select count(*) from nodes where node_type='regulation' "
            "and coalesce(properties->>'summary','') = ''",
        )
        line("regs missing summary", no_summary, warn=no_summary > total_regs * 0.05)
        no_date = await scalar(
            c,
            "select count(*) from nodes where node_type='regulation' "
            "and coalesce(properties->>'published_date','') = ''",
        )
        line("regs missing published date", no_date, warn=no_date > total_regs * 0.2)
        for model, n in await q(
            c,
            "select coalesce(properties->>'extraction_model','(unknown)'), count(*) "
            "from nodes where node_type='regulation' group by 1 order by 2 desc",
        ):
            line(f"extracted by · {model}", n)
        avg_reqs = (
            await q(
                c,
                "select round(avg(coalesce((properties->>'requirement_count')::int,0)),1) "
                "from nodes where node_type='regulation'",
            )
        )[0][0]
        line("avg requirements per regulation", avg_reqs)
        total_reqs = await scalar(c, "select count(*) from requirements")
        line("total requirements", total_reqs)
        no_cit = await scalar(c, "select count(*) from requirements where coalesce(citation,'')=''")
        line(
            "requirements missing citation",
            f"{no_cit} ({100*no_cit//max(total_reqs,1)}%)",
            warn=no_cit > total_reqs * 0.4,
        )

        print("\n== L3 · Graph integrity ==")
        orphans = await scalar(
            c,
            "select count(*) from nodes n where n.node_type='regulation' and not exists "
            "(select 1 from edges e where e.source_id=n.id or e.target_id=n.id)",
        )
        line("orphan regulation nodes (no edges)", orphans, warn=orphans > 10)
        dup_keys = await scalar(
            c,
            "select count(*) from (select node_type, properties->>'canonical_key' k "
            "from nodes where properties->>'canonical_key' is not null "
            "group by 1, 2 having count(*) > 1) d",
        )
        line("duplicate keys within a node type", dup_keys, warn=dup_keys > 0)
        edges = await scalar(c, "select count(*) from edges")
        line("total edges", edges)

        print("\n== L4 · Mapping (per org) ==")
        orgs = await q(
            c,
            "select o.id, o.name from organizations o where exists "
            "(select 1 from obligations ob where ob.org_id = o.id)",
        )
        for oid, name in orgs:
            obl = await scalar(c, "select count(*) from obligations where org_id=:o", o=oid)
            no_c = await scalar(
                c,
                "select count(*) from obligations where org_id=:o "
                "and coalesce(regulatory_citation,'')=''",
                o=oid,
            )
            gaps_open = await scalar(
                c, "select count(*) from gaps where org_id=:o and status != 'closed'", o=oid
            )
            gaps_ev = await scalar(
                c,
                "select count(*) from gaps where org_id=:o and requirement_id is not null "
                "and coalesce(evidence_quote,'') != ''",
                o=oid,
            )
            unmapped = await scalar(
                c,
                "select count(*) from nodes n where n.node_type='regulation' and not exists "
                "(select 1 from obligations ob where ob.regulation_node_id=n.id and ob.org_id=:o)",
                o=oid,
            )
            line(f"{name[:28]:<28} obligations", f"{obl} ({no_c} uncited)", warn=no_c > obl * 0.1)
            line(f"{'':<28} open gaps / evidenced", f"{gaps_open} / {gaps_ev}")
            line(f"{'':<28} regs not yet assessed", unmapped, warn=False)

        print("\n== L5 · Retrieval readiness ==")
        emb_docs = await scalar(c, "select count(*) from raw_documents where embedding is not null")
        line("embedded documents", emb_docs)
        kb_no_emb = await scalar(
            c, "select count(*) from company_documents where embedding is null"
        )
        line("company docs missing embeddings", kb_no_emb, warn=kb_no_emb > 0)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

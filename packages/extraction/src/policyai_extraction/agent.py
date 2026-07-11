"""'Ask PolicyAI' — a tool-using agent that answers compliance questions from the
graph, the obligation/task tables, and the regulation corpus (pgvector), and
returns cited answers.

The agent (Claude, mapping model) decides which tools to call:
  - search_regulations : semantic search over ingested regulation text
  - query_obligations  : the org's mapped obligations (filter by status/severity)
  - query_tasks        : the org's actionable tasks (filter by status)
  - get_company_profile: the org's applicability fingerprint

Regulations surfaced by search are collected as citations so the UI can link back
to the source — the auditability compliance teams need.
"""

from __future__ import annotations

import json
from uuid import UUID

from policyai_graph.models import Node, RawDocument
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    CompanyProfile,
    Obligation,
    Requirement,
    Task,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction import rerank
from policyai_extraction.embeddings import embed_text
from policyai_extraction.llm import MODEL_MAPPING, LLMClient

SYSTEM = (
    "You are PolicyAI, a regulatory-compliance analyst for Indian financial-sector "
    "firms. Answer the user's question using ONLY the tools provided — the company's "
    "obligations, tasks, profile, and the ingested regulation corpus. Call tools as "
    "needed before answering.\n\n"
    "Rules:\n"
    "- Ground every claim in tool results. If the tools return nothing relevant, say "
    "you don't have that in the ingested data — do NOT answer from prior knowledge or "
    "guess.\n"
    "- Cite inline: when a claim rests on a regulation, name its exact title in the "
    "sentence so the source list lines up with the text.\n"
    '- Treat regulations as current unless the user asks historically ("as of", '
    '"previously", "what was required before"). If a regulation has been superseded, '
    "flag that rather than presenting it as live.\n"
    "- Be concise and lead with the answer; compliance officers want the bottom line "
    "first, then the supporting detail.\n"
    "- Today's date context comes from the data; don't invent dates."
)

TOOLS = [
    {
        "name": "search_regulations",
        "description": "Semantic search over the ingested regulation corpus. Use for "
        "'what changed', 'is there a rule about X', or to find relevant regulations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query."},
                "limit": {"type": "integer", "description": "Max results (default 5)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_obligations",
        "description": "List the company's mapped obligations. Filter by status "
        "(open/in_review/addressed/dismissed) and/or severity (critical/high/medium/low).",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "severity": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "query_tasks",
        "description": "List the company's actionable tasks. Filter by status "
        "(todo/in_progress/blocked/done). Useful for 'what's overdue' or 'what's open'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "search_requirements",
        "description": "Search the atomic compliance requirements extracted from regulations "
        "(by keyword in their text). Use for 'what exactly must we do about X', 'what are the "
        "reporting requirements for Y', penalties, or to cite specific clauses/sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to match in requirement text.",
                },
                "requirement_type": {
                    "type": "string",
                    "description": "Optional filter: disclosure, reporting, recordkeeping, "
                    "governance, operational, prohibition, capital, consumer_protection, "
                    "registration, audit.",
                },
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_company_profile",
        "description": "The company's regulatory profile: entity classes, topics, regulators.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_insights",
        "description": "The prioritized list of what needs the compliance team's attention right "
        "now (overdue gaps, ineffective/untested controls, uncovered obligations & requirements, "
        "unmapped regulations, low-confidence mappings). Use for 'what should I do', 'what's "
        "urgent', 'where are we exposed'.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _rrf(ranked_lists: list[list], *, k: int = 60) -> list:
    """Reciprocal-rank fusion — merge several ranked id lists into one order.
    A doc that ranks well in either the vector or the keyword list floats up."""
    scores: dict = {}
    for lst in ranked_lists:
        for rank, item in enumerate(lst):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: scores[i], reverse=True)


class _Tools:
    """Executes the agent's tool calls against the DB and collects citations."""

    def __init__(self, session: AsyncSession, org_id: UUID):
        self.session = session
        self.org_id = org_id
        self.citations: list[dict] = []

    async def run(self, name: str, args: dict) -> str:
        try:
            if name == "search_regulations":
                return await self._search_regulations(args.get("query", ""), args.get("limit", 5))
            if name == "query_obligations":
                return await self._query_obligations(
                    args.get("status"), args.get("severity"), args.get("limit", 20)
                )
            if name == "query_tasks":
                return await self._query_tasks(args.get("status"), args.get("limit", 20))
            if name == "search_requirements":
                return await self._search_requirements(
                    args.get("query", ""), args.get("requirement_type"), args.get("limit", 10)
                )
            if name == "get_company_profile":
                return await self._get_profile()
            if name == "get_insights":
                return await self._get_insights()
            return json.dumps({"error": f"unknown tool {name}"})
        except Exception as exc:  # noqa: BLE001 - surface tool errors to the model, don't crash
            return json.dumps({"error": str(exc)[:300]})

    async def _search_regulations(self, query: str, limit: int) -> str:
        if not query.strip():
            return json.dumps([])
        want = min(limit, 8)
        pool = min(want * 4, 24) if rerank.is_enabled() else want

        # Vector candidates (semantic).
        qvec = await embed_text(query)
        vec_rows = list(
            (
                await self.session.execute(
                    select(RawDocument)
                    .where(RawDocument.embedding.isnot(None))
                    .order_by(RawDocument.embedding.cosine_distance(qvec))
                    .limit(pool)
                )
            )
            .scalars()
            .all()
        )

        # Keyword candidates (full-text) — catches exact circular numbers / section
        # refs that embeddings miss. Computed on the fly; graceful if FTS is absent.
        txt_rows: list[RawDocument] = []
        try:
            ts = func.to_tsvector(
                "english",
                func.coalesce(RawDocument.title, "")
                + " "
                + func.coalesce(RawDocument.raw_text, ""),
            )
            tq = func.websearch_to_tsquery("english", query)
            txt_rows = list(
                (
                    await self.session.execute(
                        select(RawDocument)
                        .where(ts.op("@@")(tq))
                        .order_by(func.ts_rank(ts, tq).desc())
                        .limit(pool)
                    )
                )
                .scalars()
                .all()
            )
        except Exception as exc:  # noqa: BLE001 - FTS is a bonus; never break retrieval
            print(f"[ask] full-text search skipped: {str(exc)[:120]}")

        # Reciprocal-rank fusion of the two candidate lists, then rerank to top `want`.
        by_id = {r.id: r for r in vec_rows}
        by_id.update({r.id: r for r in txt_rows})
        fused_ids = _rrf([[r.id for r in vec_rows], [r.id for r in txt_rows]])[:pool]
        rows = [by_id[i] for i in fused_ids] or vec_rows
        if rerank.is_enabled() and len(rows) > 1:
            order = await rerank.rerank(
                query, [(r.raw_text or "")[:1500] for r in rows], top_k=want
            )
            rows = [rows[i] for i in order]
        else:
            rows = rows[:want]
        results = []
        for r in rows:
            cite = {"title": r.title, "source_url": r.source_url, "source": r.source}
            if cite not in self.citations:
                self.citations.append(cite)
            results.append(
                {
                    "title": r.title,
                    "source": r.source,
                    "published_date": str(r.published_date) if r.published_date else None,
                    "snippet": (r.raw_text or "")[:600],
                }
            )
        return json.dumps(results)

    async def _query_obligations(self, status, severity, limit) -> str:
        stmt = select(Obligation).where(Obligation.org_id == self.org_id)
        if status:
            stmt = stmt.where(Obligation.status == status)
        if severity:
            stmt = stmt.where(Obligation.severity == severity)
        rows = (await self.session.execute(stmt.limit(min(limit, 50)))).scalars().all()
        return json.dumps(
            [
                {
                    "title": o.title,
                    "summary": o.summary,
                    "severity": o.severity,
                    "status": o.status,
                    "obligation_type": o.obligation_type,
                    "frequency": o.frequency,
                    "regulatory_citation": o.regulatory_citation,
                    "penalty": o.penalty_summary,
                    "evidence_required": o.evidence_required,
                    "what_changed": o.what_changed,
                    "gap_analysis": o.gap_analysis,
                }
                for o in rows
            ]
        )

    async def _search_requirements(self, query: str, requirement_type, limit) -> str:
        if not query.strip():
            return json.dumps([])
        stmt = (
            select(Requirement, Node)
            .join(Node, Node.id == Requirement.regulation_node_id)
            .where(Requirement.text.ilike(f"%{query}%"))
        )
        if requirement_type:
            stmt = stmt.where(Requirement.requirement_type == requirement_type)
        rows = (await self.session.execute(stmt.limit(min(limit or 10, 25)))).all()
        results = []
        for r, n in rows:
            p = n.properties or {}
            if p.get("source_url"):
                cite = {
                    "title": p.get("title") or "regulation",
                    "source_url": p["source_url"],
                    "source": p.get("regulator") or "",
                }
                if cite not in self.citations:
                    self.citations.append(cite)
            results.append(
                {
                    "requirement": r.text,
                    "type": r.requirement_type,
                    "frequency": r.frequency,
                    "citation": r.citation,
                    "evidence": r.evidence_expected,
                    "penalty": r.penalty,
                    "regulation": p.get("title"),
                }
            )
        return json.dumps(results)

    async def _query_tasks(self, status, limit) -> str:
        stmt = select(Task).where(Task.org_id == self.org_id)
        if status:
            stmt = stmt.where(Task.status == status)
        rows = (await self.session.execute(stmt.limit(min(limit, 50)))).scalars().all()
        return json.dumps(
            [
                {
                    "title": t.title,
                    "owner": t.owner,
                    "due_date": str(t.due_date) if t.due_date else None,
                    "priority": t.priority,
                    "status": t.status,
                }
                for t in rows
            ]
        )

    async def _get_insights(self) -> str:
        from policyai_extraction.insights import compute_insights

        data = await compute_insights(self.session, self.org_id)
        return json.dumps(
            {
                "posture": data["posture_note"],
                "insights": [
                    {
                        "label": i["label"],
                        "severity": i["severity"],
                        "count": i["count"],
                        "what_to_do": i["action_label"],
                    }
                    for i in data["insights"]
                ],
            }
        )

    async def _get_profile(self) -> str:
        profile = (
            await self.session.execute(
                select(CompanyProfile).where(CompanyProfile.org_id == self.org_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            return json.dumps({"note": "no company profile derived yet"})
        return json.dumps(
            {
                "company": profile.notes,
                "entity_classes": profile.entity_classes,
                "topics": profile.topics,
                "regulators": profile.regulators,
            }
        )


async def ask(
    session: AsyncSession,
    question: str,
    llm: LLMClient,
    *,
    org_id: UUID = DEFAULT_ORG_ID,
) -> dict:
    """Answer a question with tool-grounded RAG. Returns {answer, citations}."""
    tools = _Tools(session, org_id)
    answer = await llm.converse_with_tools(
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
        tools=TOOLS,
        tool_runner=tools.run,
        model=MODEL_MAPPING,
    )
    return {"answer": answer, "citations": tools.citations}


async def ask_stream(
    session: AsyncSession,
    question: str,
    llm: LLMClient,
    *,
    org_id: UUID = DEFAULT_ORG_ID,
):
    """Stream the answer as events for SSE: a run of ``{"type":"token","text":...}``
    while the answer is produced, then one ``{"type":"citations","citations":[...]}``,
    then ``{"type":"done"}``. Citations are collected by the tools during the run."""
    tools = _Tools(session, org_id)
    async for delta in llm.converse_with_tools_stream(
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
        tools=TOOLS,
        tool_runner=tools.run,
        model=MODEL_MAPPING,
    ):
        if delta:
            yield {"type": "token", "text": delta}
    yield {"type": "citations", "citations": tools.citations}
    yield {"type": "done"}

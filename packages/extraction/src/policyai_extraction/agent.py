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

from policyai_graph.models import RawDocument
from policyai_graph.models_app import DEFAULT_ORG_ID, CompanyProfile, Obligation, Task
from sqlalchemy import select
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
    "- Ground every claim in tool results. If the data doesn't answer the question, "
    "say so plainly rather than guessing.\n"
    "- When you reference a regulation, name its title so the source is traceable.\n"
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
        "name": "get_company_profile",
        "description": "The company's regulatory profile: entity classes, topics, regulators.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


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
            if name == "get_company_profile":
                return await self._get_profile()
            return json.dumps({"error": f"unknown tool {name}"})
        except Exception as exc:  # noqa: BLE001 - surface tool errors to the model, don't crash
            return json.dumps({"error": str(exc)[:300]})

    async def _search_regulations(self, query: str, limit: int) -> str:
        if not query.strip():
            return json.dumps([])
        qvec = await embed_text(query)
        want = min(limit, 8)
        pool = min(want * 4, 24) if rerank.is_enabled() else want
        stmt = (
            select(RawDocument)
            .where(RawDocument.embedding.isnot(None))
            .order_by(RawDocument.embedding.cosine_distance(qvec))
            .limit(pool)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if rerank.is_enabled() and len(rows) > 1:
            order = await rerank.rerank(
                query, [(r.raw_text or "")[:1500] for r in rows], top_k=want
            )
            rows = [rows[i] for i in order]
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
                    "what_changed": o.what_changed,
                    "gap_analysis": o.gap_analysis,
                }
                for o in rows
            ]
        )

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

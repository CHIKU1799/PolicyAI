# PolicyAI — Project Context

## What we're building
A regulatory intelligence platform for India. 2-week MVP scope: 
ingest RBI and SEBI circulars, extract structured information using 
Claude API, build a queryable knowledge graph, expose via FastAPI, 
render in a Next.js frontend.

## Why a knowledge graph (not a document store)
Indian regulations are relational — circulars amend master directions, 
apply to specific entity classes, derive from parent acts. A graph 
captures these relationships; a document store throws them away.

## Tech stack (locked)
- Backend: Python 3.11, FastAPI, async
- Database: PostgreSQL 15 with pgvector extension
- Scraping: Playwright (async API)
- LLM: Anthropic Claude API (claude-sonnet-4)
- Orchestration: Prefect (start simple, one flow per source)
- Frontend: Next.js 14 app router, TypeScript, Tailwind
- Graph viz: react-force-graph-2d
- Deployment: local dev first, Railway for staging

## Knowledge graph schema
Nodes:
- Regulation (circular, notification, master direction)
- Regulator (RBI, SEBI, and sub-departments)
- EntityClass (NBFC, Bank, AIF, Payment Aggregator, etc.)
- ParentAct (statutory anchor like RBI Act 1934)
- Topic (KYC, capital adequacy, fair practices code)
- Deadline (date obligations extracted from regulations)

Edges:
- AMENDS, SUPERSEDES, ISSUED_BY, APPLIES_TO, 
  DERIVED_FROM, COVERS_TOPIC, HAS_DEADLINE, REFERENCES

## Success criteria for the 2-week MVP
1. 150+ circulars ingested (6 months of RBI and SEBI)
2. Extraction accuracy: 85%+ on entities, 75%+ on relationships, 
   measured on a 30-circular held-out test set
3. Full-text and semantic search working
4. Graph visualization for one hero use case (NBFC microfinance)
5. All code tested, documented, and reproducible

## Non-goals (explicitly out of scope)
- Authentication and billing
- Email alerts and notifications
- Multiple states or regional languages
- IRDAI, MCA, or any other regulator
- Production deployment with SLA
- Mobile responsive design

## Team
Solo developer (me). Claude Code is my pair programmer.

## Code conventions
- Black + ruff for Python, strict type hints
- All LLM calls go through a single client wrapper with retry 
  logic and cost tracking
- Every prompt lives in prompts/ directory as a separate file 
  with a version number and eval results
- All extractions are validated against Pydantic models before 
  entering the database

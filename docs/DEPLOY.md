# Deploying PolicyAI

Three tiers, three providers. Nothing of substance lives on local disk.

| Tier | Host | What runs there |
|------|------|-----------------|
| **DB / Storage / Realtime** | **Supabase** | Postgres 15 + pgvector, Auth, Storage (uploaded policy PDFs), Realtime, pg_cron/pg_net |
| **Worker + Crawler** | **Render** | FastAPI service (`policyai-worker`) + 6-hourly Playwright crawl cron (`policyai-crawler`) — see `render.yaml` |
| **Dashboard** | **Vercel** | Next.js 14 app in `frontend/` |

Code is on GitHub `main` (`CHIKU1799/PolicyAI`). Render and Vercel both deploy from `main`.

---

## 0. Prerequisites
- A Supabase project (already provisioned — reuse the one behind the current `DATABASE_URL`).
- A Render account and a Vercel account.
- A funded LLM key. Either **Anthropic** (`LLM_PROVIDER=anthropic`) or a **free OpenAI-compatible** provider like Groq (`LLM_PROVIDER=openai_compatible`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1`). Extraction/mapping will 400 without credits on the chosen provider.

---

## 1. Supabase (one-time)
1. **Extensions + platform objects:** open the SQL editor and run, in order, every file in `supabase/migrations/*.sql` (starts with `0000_platform.sql` — pgvector, Realtime publication, pg_net internal trigger, then the RLS files).
2. **App schema:** from a machine with `DATABASE_URL` set to the session pooler (`:5432`), run:
   ```
   make db-migrate     # alembic upgrade head  -> creates all app tables (currently 0011)
   make db-seed        # regulators, entity classes, parent acts, 16 monitoring sources
   ```
3. **Storage bucket:** create a bucket named `company-documents` (matches `SUPABASE_KB_BUCKET`) for firms' uploaded policy files.
4. Grab from *Project Settings → API*: the project URL, the **anon** key, and the **service-role** key (server-side only).

---

## 2. Render (worker + crawler)
`render.yaml` is a blueprint — in Render, **New → Blueprint**, point it at the repo. It creates both services. Then create an **environment group named `policyai`** (both services reference `fromGroup: policyai`) with:

**Required**
- `DATABASE_URL` — Supabase session pooler URI, scheme `postgresql+asyncpg://` (password with `@` is handled by `db.py`).
- `LLM_PROVIDER` — `anthropic` or `openai_compatible`.
- If Anthropic: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_EXTRACTION=claude-sonnet-4-6`, `ANTHROPIC_MODEL_MAPPING=claude-opus-4-8`.
- If OpenAI-compatible: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`.
- `EMBEDDING_PROVIDER` — `cohere` or `voyage` recommended on Render (avoid `local`; the 2 GB model bloats the image). Set the matching key: `COHERE_API_KEY` / `VOYAGE_API_KEY`.
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KB_BUCKET=company-documents`.
- `INTERNAL_API_SECRET` — random string; also used by the Supabase pg_net trigger calling `/internal/*`.
- `FRONTEND_ORIGINS` — the Vercel domain(s), comma-separated (CORS). Fill this in **after** step 3.

**Optional**
- `RERANK_PROVIDER=cohere` (reuses `COHERE_API_KEY`) — improves retrieval precision; `off` to disable.
- `STORAGE_BACKEND` — `supabase` (default) or `r2` + `R2_*` keys for the document lake.
- `GBRAIN_BASE_URL` / `GBRAIN_API_KEY` — Hermes enrichment for profiles/task owners; blank = docs-only.
- `RESEND_API_KEY` + `ALERT_EMAIL_TO` — email alerts; no-op unless both set.
- `MAP_AFTER_SCAN=true` (default) — crawl also maps new regs to obligations.
- `SCRAPER_REQUEST_DELAY=2.0`, `SCRAPER_BACKFILL_MONTHS=6`.

**Health check:** worker `healthCheckPath` is `/ready` (503 until DB reachable). `/health` is bare liveness.

**Deep backfill (optional, after first deploy):** the cron only scrapes the current listing. To backfill history from a Render shell:
```
uv run python -m policyai_scrapers.backfill --regulator rbi --from-id 12635 --dry-run     # count first (free)
uv run python -m policyai_scrapers.backfill --regulator rbi --from-id 12635 --limit 50 --map
```

---

## 3. Vercel (dashboard)
1. **New Project → import the repo**, set **Root Directory = `frontend/`** (Vercel auto-detects Next.js; build `next build`).
2. Environment variables (these three are all the browser/SSR needs):
   - `NEXT_PUBLIC_SUPABASE_URL` — the Supabase project URL.
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — the anon key.
   - `NEXT_PUBLIC_API_URL` — the Render worker URL (e.g. `https://policyai-worker.onrender.com`).
3. Deploy, then copy the Vercel domain back into Render's `FRONTEND_ORIGINS` and redeploy the worker (closes the CORS loop).

---

## 4. Post-deploy smoke test
1. `GET https://<worker>/ready` → `200`.
2. Open the Vercel dashboard → the KPI tiles / obligations load (Supabase reachable from the browser).
3. Upload a policy PDF on the Policies page → a `CompanyDocument` row appears (Storage + worker text-extract wired).
4. Trigger **Scan now** → a `ScanRun` completes and new obligations/gaps show up.

---

## Deploy sequencing gotchas
- **DB first.** Migrations + seed must run before the worker boots, or `/ready` stays 503.
- **CORS is circular.** The Vercel domain isn't known until step 3, so `FRONTEND_ORIGINS` is filled last.
- **`main` is the deploy branch** for both Render and Vercel — merge feature branches before expecting a redeploy.
- **Cold starts:** Render `starter` sleeps; the first request after idle is slow. Fine for a demo.

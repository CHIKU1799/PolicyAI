# PolicyAI server deployment (Docker)

Everything runs from `docker compose`. The database is **cloud Supabase**, so
"the DB and all the data" travel with the `.env` file, not with the containers:
point any server at the same `DATABASE_URL` and it sees the same regulations,
obligations, controls, and users. Nothing to dump or restore.

## What the person deploying needs

1. This repository.
2. The `.env` file, **shared separately and securely** (it holds the Supabase
   service-role key and LLM API keys; it is gitignored and must never be
   committed). `.env.example` documents every variable.
3. Docker + Docker Compose on the server.

## Bring it up

```bash
cp /path/to/received/.env .env   # place the shared .env at the repo root

docker compose build             # builds api + web images (~10 min first time)
docker compose up -d api web     # API on :8000, frontend on :3000
```

Check it:

```bash
curl http://localhost:8000/ready   # {"status":"ok","db":"ok"} = DB reachable
curl -I http://localhost:3000      # 200 = frontend up
```

## Things to adjust per server

- `NEXT_PUBLIC_API_URL` in `.env` must be the URL browsers will use to reach
  the API from outside (e.g. `https://api.yourdomain.com`), not `localhost`,
  then rebuild the web image (`docker compose build web`). NEXT_PUBLIC values
  are baked in at build time.
- `FRONTEND_ORIGINS` in `.env` must include the public frontend URL, or the
  API will reject browser requests with CORS errors.
- Put a reverse proxy (nginx/Caddy) with TLS in front of :3000 and :8000.

## Crawling (ingesting new regulations)

One pass over all enabled sources (RBI, SEBI, IRDAI, MCA, PIB):

```bash
docker compose run --rm crawler
```

Schedule it on the host, e.g. every 6 hours:

```cron
0 */6 * * * cd /path/to/policyai && docker compose run --rm crawler >> /var/log/policyai-crawl.log 2>&1
```

Per-source cadence is enforced inside the runner, so running it more often is
safe. To re-extract documents that failed mid-crawl:

```bash
docker compose run --rm crawler uv run python scripts/reprocess_unmapped.py
```

## Database migrations

The shared Supabase project is already migrated (Alembic head `0013`). After
pulling a newer version of the repo that adds migrations:

```bash
docker compose run --rm api sh -c "cd packages/graph && uv run --no-sync alembic upgrade head"
```

Notes on this command:
- `alembic` alone will print "not found" — it lives in the uv-managed venv, so
  it must go through `uv run`.
- The `cd packages/graph` is required: `alembic.ini` lives there, and alembic
  only looks in the current directory.
- `--no-sync` stops uv from re-resolving dependencies at container start.

## Fully offline / self-hosted DB (optional)

If a deployment must not use cloud Supabase, there is a local Postgres with
pgvector in the compose file:

```bash
docker compose up -d postgres
# then set DATABASE_URL=postgresql://policyai:policyai@postgres:5432/policyai
# in .env, run migrations + seed:
docker compose run --rm api sh -c "cd packages/graph && uv run --no-sync alembic upgrade head"
```

Note: Supabase Auth, Storage, and RLS-backed frontend reads do not work
against plain Postgres; the local DB is for API-only/offline development.

## Notes

- The API image includes Playwright Chromium (needed by the scrapers) and
  caches the local embedding model in the `policyai_hf_cache` volume; the
  first crawl downloads the model once.
- Logs: `docker compose logs -f api web`.

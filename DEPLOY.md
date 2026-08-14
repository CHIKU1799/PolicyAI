# PolicyAI deployment

Two supported paths:

1. **Sevalla** (PaaS, builds from GitHub) — see the next section.
2. **Any server with Docker Compose** — see "Server deployment (Docker)".

Both use the same two images (`docker/api.Dockerfile`, `docker/web.Dockerfile`)
and the same cloud Supabase database, so they are interchangeable.

## Sevalla deployment

Sevalla builds straight from the GitHub repo using the existing Dockerfiles.
Create **two applications** from `github.com/CHIKU1799/PolicyAI`, branch `main`.

### App 1: policyai-api (worker + crawler + digest)

Build settings (Settings -> Build):

- Build strategy: **Dockerfile**
- Dockerfile path: `docker/api.Dockerfile`
- Context: `.`

Environment variables: everything from `.env` EXCEPT the `NEXT_PUBLIC_*` ones
(those belong to the web app). At minimum: `DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KB_BUCKET`,
`LLM_PROVIDER` + the active provider key, `EMBEDDING_PROVIDER`,
`RERANK_PROVIDER` + `COHERE_API_KEY`, and:

```
FRONTEND_ORIGINS=https://<your-web-app>.sevalla.app
```

(comma-append any custom domain later, or the browser gets CORS errors).

None of the API env vars are needed at build time, so no build-time toggles.
The image's CMD already binds `0.0.0.0:$PORT`, which Sevalla injects.

Processes (Sevalla runs every process from the same built image):

| Process | Type | Start command | Schedule |
|---|---|---|---|
| web | Web process | (image default CMD) | — |
| crawler | Cron job | `uv run --no-sync python -m policyai_scrapers.runner` | `0 */6 * * *` |
| digest | Cron job | `uv run --no-sync python -m policyai_extraction.digest` | `30 3 * * *` |

Sizing and storage:

- With `EMBEDDING_PROVIDER=local`, the API downloads the bge-m3 model
  (~2.3 GB) into `HF_HOME=/data` on first use and needs it in RAM. Give the
  web process **at least 2 GB RAM** and attach **persistent storage mounted at
  `/data`** (Sevalla disks are configured in the dashboard, not the
  Dockerfile) so the model survives deploys. If you'd rather run a small pod,
  set `EMBEDDING_PROVIDER=hf` (or `cohere`) instead and skip the disk.
- Verify after deploy: `https://<api-app>.sevalla.app/ready` should return
  `{"status":"ok","db":"ok"}`.

### App 2: policyai-web (Next.js frontend)

Build settings:

- Build strategy: **Dockerfile**
- Dockerfile path: `docker/web.Dockerfile`
- Context: `.`

`NEXT_PUBLIC_*` values are inlined at **build time**. Sevalla passes an env
var into a Dockerfile build only when the Dockerfile declares a matching
`ARG` — `docker/web.Dockerfile` already declares all four — so just add them
as normal environment variables on this app, then trigger a build:

```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_SUPABASE_KB_BUCKET=company-documents
NEXT_PUBLIC_API_URL=https://<api-app>.sevalla.app
```

Changing any of these later requires a **rebuild**, not just a restart.

Optionally also add the LLM provider keys (`GROQ_API_KEY`, `CEREBRAS_API_KEY`,
`GEMINI_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`
- any subset) as **runtime** env vars on the web app: the bundled backup
Copilot (`/api/ask`, used when the worker is unreachable) runs server-side in
Next.js and reads them at request time.

Processes: the single default web process. The image binds `$PORT`
automatically.

### Order of operations

1. Deploy **policyai-api** first, note its public URL.
2. Set that URL as `NEXT_PUBLIC_API_URL` on **policyai-web**, deploy it,
   note the web URL.
3. Go back to policyai-api and set `FRONTEND_ORIGINS` to the web URL,
   redeploy (restart is enough; it is read at runtime).
4. Configure Supabase Auth (Dashboard -> Authentication -> URL
   Configuration) or signup confirmation emails will dead-end:
   - **Site URL** = `https://<web-app>.sevalla.app` (or the custom domain).
   - **Redirect URLs**: add `https://<web-app>.sevalla.app/auth/callback`
     and, for local dev, `http://localhost:3001/auth/callback`.
   - The frontend sends `emailRedirectTo = <origin>/auth/callback`; that
     route handles both `?code=` and `?token_hash=` link styles and lands
     the user in the app (or on /login with a clear notice).
   - Supabase's built-in SMTP allows only a couple of mails per hour and
     every resend INVALIDATES earlier links (users clicking an older email
     see "link expired"). For real customers set up custom SMTP (e.g.
     Resend) under Authentication -> Emails -> SMTP settings.
   - A stuck unconfirmed user can be unblocked from Authentication ->
     Users -> "..." -> Confirm email.
   - NOTE (2026-08-14): signup no longer depends on these emails. The login
     page calls the worker's `POST /public/signup`, which creates the user
     pre-confirmed via the service-role admin API and signs straight in;
     the confirmation-email flow is only the fallback when that endpoint is
     unavailable. Email verification can be reinstated once real SMTP works.
5. Email via Resend (account: nishantkumar1799@gmail.com). Set
   `RESEND_API_KEY` and `ALERT_EMAIL_TO` on the API app: enables ops mails
   for contact-form submissions and obligation/scan alerts, plus a welcome
   mail on signup. `policyai.com` is added as a Resend domain; until its
   DNS records (DKIM TXT `resend._domainkey`, MX + TXT on `send`) are added
   at the DNS host and verified, Resend only delivers to the account owner,
   so keep the default `onboarding@resend.dev` sender. After verification:
   - set `ALERT_EMAIL_FROM="PolicyAI <noreply@policyai.com>"` on the API app
   - configure Supabase custom SMTP (Authentication -> Emails -> SMTP):
     host `smtp.resend.com`, port `465`, user `resend`, password = the
     Resend API key, sender `noreply@policyai.com`.
6. Check `/ready` on the API, then sign in on the web app.

The database is the existing cloud Supabase project (already at Alembic head
`0013`), so there is nothing to migrate for a fresh Sevalla deploy. For future
migrations, open the API app's Web Terminal and run:

```bash
cd packages/graph && uv run --no-sync alembic upgrade head
```

## Server deployment (Docker)

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

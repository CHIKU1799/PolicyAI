#!/usr/bin/env bash
# Native Postgres logical backup via pg_dump -> backups/db-<timestamp>.sql.gz
#
# Companion to the portable JSON export (`make export-graph`). Use this when you
# want a dump you can restore straight back into Postgres with psql/pg_restore.
#
# Connection: pass a libpq URI in BACKUP_DATABASE_URL (preferred) or DATABASE_URL.
# For Supabase, use the DIRECT connection string (Project Settings -> Database ->
# Connection string -> URI), NOT the pooler — pg_dump needs a session, and the
# pooler rejects some dump operations. Percent-encode special chars in the
# password (e.g. '@' -> %40), otherwise the URI mis-parses the host.
#
# Restore:  gunzip -c backups/db-<ts>.sql.gz | psql "$DIRECT_DATABASE_URL"
set -euo pipefail

URL="${BACKUP_DATABASE_URL:-${DATABASE_URL:-}}"
if [[ -z "$URL" ]]; then
  echo "error: set BACKUP_DATABASE_URL (or DATABASE_URL) to a libpq URI" >&2
  exit 1
fi
if ! command -v pg_dump >/dev/null 2>&1; then
  echo "error: pg_dump not found. Install the Postgres client tools (e.g. 'brew install libpq')." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT/backups"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$OUT_DIR/db-$STAMP.sql.gz"

echo "dumping -> $OUT"
# --no-owner/--no-acl keep the dump portable across roles (Supabase vs local).
pg_dump --no-owner --no-acl --format=plain "$URL" | gzip -9 > "$OUT"
echo "done: $(du -h "$OUT" | cut -f1) $OUT"

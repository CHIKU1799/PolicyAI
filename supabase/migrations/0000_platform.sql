-- Supabase platform-level setup. Owned by Supabase, NOT Alembic.
-- Alembic owns tables/columns/indexes; this file owns extensions, Realtime, and
-- (later) RLS. Run this once against the Supabase project before `alembic upgrade head`.
--
--   supabase db push        # if using the Supabase CLI
--   -- or paste into the SQL editor in the Supabase dashboard

-- pgvector for embeddings (Supabase installs it into the `extensions` schema).
create extension if not exists vector with schema extensions;

-- Scheduling + outbound HTTP, used for the event-driven "new regulation -> map
-- obligations" hook in 0001_triggers.sql (added in Phase 5).
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

-- Realtime: the dashboard subscribes to these tables for the live alert feed and
-- task board. The tables themselves are created by Alembic (migration 0002); this
-- statement is safe to run after that migration. Re-running is idempotent because
-- `add table` errors if already a member — guard with a DO block.
do $$
begin
  begin
    alter publication supabase_realtime add table public.alerts;
  exception when duplicate_object then null;
  end;
  begin
    alter publication supabase_realtime add table public.tasks;
  exception when duplicate_object then null;
  end;
end $$;

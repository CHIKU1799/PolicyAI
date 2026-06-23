-- Event-driven obligation mapping + Realtime wiring. Owned by Supabase, not Alembic.
-- Run after Alembic migration 0002 (which creates nodes/alerts/tasks) and after
-- 0000_platform.sql (which enables pg_net). Idempotent.

-- Where to reach the Render worker, and the shared secret guarding /internal/*.
-- Kept in a private table so the trigger function can read them without hardcoding.
create schema if not exists private;

create table if not exists private.app_config (
  key   text primary key,
  value text not null
);

-- Set these once (replace with your real values):
--   insert into private.app_config(key, value)
--   values ('worker_url', 'https://policyai-worker.onrender.com'),
--          ('internal_secret', '<INTERNAL_API_SECRET>')
--   on conflict (key) do update set value = excluded.value;

-- Fire a non-blocking POST to the worker when a new regulation node is inserted.
-- pg_net is fire-and-forget; the worker endpoint is idempotent and a reconciliation
-- cron re-maps anything this misses, so a dropped delivery is not data loss.
create or replace function private.map_new_regulation()
returns trigger
language plpgsql
security definer
as $$
declare
  v_url    text;
  v_secret text;
begin
  if new.node_type <> 'regulation' then
    return new;
  end if;

  select value into v_url    from private.app_config where key = 'worker_url';
  select value into v_secret from private.app_config where key = 'internal_secret';
  if v_url is null then
    return new;  -- not configured yet; reconciliation cron will pick it up
  end if;

  perform extensions.net.http_post(
    url     := v_url || '/internal/map-obligations',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'x-internal-secret', coalesce(v_secret, '')
    ),
    body    := jsonb_build_object('regulation_node_id', new.id)
  );
  return new;
end;
$$;

drop trigger if exists trg_map_new_regulation on public.nodes;
create trigger trg_map_new_regulation
  after insert on public.nodes
  for each row
  when (new.node_type = 'regulation')
  execute function private.map_new_regulation();

-- Realtime: the dashboard subscribes to these for the live alert feed and task board.
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

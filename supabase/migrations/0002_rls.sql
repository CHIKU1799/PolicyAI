-- Single-org MVP access control. Owned by Supabase, not Alembic.
-- Run AFTER Alembic migration 0002 creates the app tables.
--
-- The dashboard reads/writes through the Supabase anon key (PostgREST + Realtime).
-- Alembic-created tables have no PostgREST grants or RLS policies by default, so
-- without this the dashboard returns zero rows and the realtime alert feed stays
-- silent. RLS is enabled with permissive (USING true) policies now so multi-tenant
-- can tighten them to `org_id = auth.jwt()->>'org'` later without restructuring.
-- The worker uses the service-role key and bypasses RLS entirely.

grant usage on schema public to anon, authenticated;
grant select on
  public.obligations, public.tasks, public.alerts,
  public.company_documents, public.scan_runs,
  public.monitoring_sources, public.company_profiles
  to anon, authenticated;
grant update on public.tasks to anon, authenticated;  -- task board status changes

-- Enable RLS + permissive read policies (idempotent). Realtime honors RLS, so the
-- SELECT policy is what lets the anon alert-feed subscription receive rows.
do $$
declare t text;
begin
  foreach t in array array[
    'obligations','tasks','alerts','company_documents',
    'scan_runs','monitoring_sources','company_profiles'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_select', t);
    execute format(
      'create policy %I on public.%I for select to anon, authenticated using (true)',
      t || '_anon_select', t
    );
  end loop;

  drop policy if exists tasks_anon_update on public.tasks;
  create policy tasks_anon_update on public.tasks
    for update to anon, authenticated using (true) with check (true);
end $$;

-- Knowledge-base storage bucket + upload policy (browser uploads directly here;
-- the worker reads back with the service-role key, so no anon read policy needed).
insert into storage.buckets (id, name, public)
values ('company-documents', 'company-documents', false)
on conflict (id) do nothing;

drop policy if exists "kb anon upload" on storage.objects;
create policy "kb anon upload" on storage.objects
  for insert to anon, authenticated
  with check (bucket_id = 'company-documents');

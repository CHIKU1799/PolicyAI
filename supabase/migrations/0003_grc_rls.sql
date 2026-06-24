-- RLS grants for the GRC tables (single-org MVP). Run after Alembic migration 0003.
-- Mirrors 0002_rls.sql: anon/authenticated can read; permissive policies now,
-- tightened to org_id when multi-tenant Auth lands. Service role bypasses RLS.

grant usage on schema public to anon, authenticated;
grant select on
  public.policies, public.policy_versions, public.controls, public.control_tests,
  public.products, public.gaps, public.audit_events,
  public.obligation_controls, public.obligation_policies, public.obligation_products
  to anon, authenticated;
-- Operational writes from the UI (gap status, control test results, policy edits).
grant insert, update on public.gaps, public.control_tests, public.controls, public.policies
  to anon, authenticated;

do $$
declare t text;
begin
  foreach t in array array[
    'policies','policy_versions','controls','control_tests','products',
    'gaps','audit_events','obligation_controls','obligation_policies','obligation_products'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_select', t);
    execute format(
      'create policy %I on public.%I for select to anon, authenticated using (true)',
      t || '_anon_select', t
    );
  end loop;

  foreach t in array array['gaps','control_tests','controls','policies'] loop
    execute format('drop policy if exists %I on public.%I', t || '_anon_write', t);
    execute format(
      'create policy %I on public.%I for all to anon, authenticated using (true) with check (true)',
      t || '_anon_write', t
    );
  end loop;
end $$;

-- Realtime for the live controls/gap boards.
do $$
begin
  begin alter publication supabase_realtime add table public.gaps; exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.control_tests; exception when duplicate_object then null; end;
end $$;

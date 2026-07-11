-- Multi-tenant RLS. Run after Alembic migration 0004.
-- After this, ONLY authenticated users see data, and only their org's rows.
-- The worker uses the service-role key and bypasses all of this.

-- 1. Orgs the current user belongs to (security definer: bypasses memberships RLS,
--    so policies can call it without recursion).
create or replace function public.user_org_ids()
returns setof uuid language sql security definer stable set search_path = public as $$
  select org_id from public.memberships where user_id = auth.uid()
$$;

-- 2. Auto-enroll every new Auth user into the default org as admin.
--    (For true per-firm isolation later, create a fresh org here instead.)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.memberships (id, user_id, org_id, role)
  values (gen_random_uuid(), new.id, '00000000-0000-0000-0000-000000000001', 'admin')
  on conflict (user_id, org_id) do nothing;
  return new;
end$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users for each row execute function public.handle_new_user();

-- 3. memberships + organizations: a user can read their own.
grant usage on schema public to authenticated;
grant select on public.memberships, public.organizations to authenticated;
alter table public.memberships enable row level security;
drop policy if exists memberships_self on public.memberships;
create policy memberships_self on public.memberships
  for select to authenticated using (user_id = auth.uid());
alter table public.organizations enable row level security;
drop policy if exists organizations_member on public.organizations;
create policy organizations_member on public.organizations
  for select to authenticated using (id in (select public.user_org_ids()));

-- 4. Org-scoped read on every data table (replaces the permissive anon policies).
--    `org_id is null` keeps global rows (e.g. monitoring sources) visible.
do $$
declare t text;
begin
  foreach t in array array[
    'obligations','tasks','alerts','company_documents','company_profiles',
    'monitoring_sources','gaps','controls','control_tests','products','policies',
    'audit_events','obligation_controls','obligation_policies','obligation_products'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_select', t);
    execute format('drop policy if exists %I on public.%I', t || '_org_select', t);
    execute format('grant select on public.%I to authenticated', t);
    execute format(
      'create policy %I on public.%I for select to authenticated '
      'using (org_id is null or org_id in (select public.user_org_ids()))',
      t || '_org_select', t
    );
  end loop;
end $$;

-- scan_runs is global infra (no org_id) — readable by any authenticated user.
alter table public.scan_runs enable row level security;
grant select on public.scan_runs to authenticated;
drop policy if exists scan_runs_anon_select on public.scan_runs;
drop policy if exists scan_runs_auth_select on public.scan_runs;
create policy scan_runs_auth_select on public.scan_runs
  for select to authenticated using (true);

-- policy_versions has no org_id — scope it through its parent policy's RLS.
alter table public.policy_versions enable row level security;
grant select on public.policy_versions to authenticated;
drop policy if exists policy_versions_anon_select on public.policy_versions;
drop policy if exists policy_versions_org_select on public.policy_versions;
create policy policy_versions_org_select on public.policy_versions
  for select to authenticated using (policy_id in (select id from public.policies));

-- 5. Org-scoped writes from the UI (task/gap/control/policy edits).
do $$
declare t text;
begin
  foreach t in array array['gaps','control_tests','controls','policies','tasks'] loop
    execute format('drop policy if exists %I on public.%I', t || '_anon_write', t);
    execute format('drop policy if exists %I on public.%I', t || '_anon_update', t);
    execute format('drop policy if exists %I on public.%I', t || '_org_write', t);
    execute format('grant insert, update on public.%I to authenticated', t);
    execute format(
      'create policy %I on public.%I for all to authenticated '
      'using (org_id is null or org_id in (select public.user_org_ids())) '
      'with check (org_id is null or org_id in (select public.user_org_ids()))',
      t || '_org_write', t
    );
  end loop;
end $$;

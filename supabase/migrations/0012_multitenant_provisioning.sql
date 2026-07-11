-- Multi-tenant provisioning + platform admin. Run in Supabase AFTER alembic 0012.
--
-- What changes vs 0004_tenancy_rls.sql:
--   * A new Auth user no longer joins the shared demo org. Instead a FRESH org is
--     created from their signup company name, and they become its admin. This is
--     what gives each firm its own isolated login + dashboard.
--   * Platform admins (rows in platform_admins) can read across ALL orgs, powering
--     the /admin console. Regular users still see only their own org (+ global rows).
--
-- Idempotent: safe to re-run. The default demo org and its data are untouched.

-- 1. Slugify helper: "Acme Finance Ltd." -> "acme-finance-ltd".
create or replace function public.slugify(txt text)
returns text language sql immutable as $$
  select trim(both '-' from regexp_replace(lower(coalesce(txt,'')), '[^a-z0-9]+', '-', 'g'))
$$;

-- 2. Is the current user a platform-level super-admin? (security definer: reads
--    platform_admins regardless of that table's own RLS.)
create or replace function public.is_platform_admin()
returns boolean language sql security definer stable set search_path = public as $$
  select exists (select 1 from public.platform_admins where user_id = auth.uid())
$$;

-- 3. Per-firm provisioning on signup. Company name comes from the signup metadata
--    (auth.users.raw_user_meta_data->>'company_name'); falls back to the email local
--    part. Platform admins are pre-seeded and skip org creation (they access all).
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  firm      text := coalesce(nullif(trim(new.raw_user_meta_data->>'company_name'), ''),
                             split_part(new.email, '@', 1));
  new_org   uuid := gen_random_uuid();
  base_slug text := coalesce(nullif(public.slugify(firm), ''), 'firm');
  final_slug text := base_slug;
begin
  -- Pre-seeded platform admins do not get an org; they oversee every org.
  if exists (select 1 from public.platform_admins where user_id = new.id
             or lower(email) = lower(new.email)) then
    insert into public.platform_admins (user_id, email)
    values (new.id, new.email) on conflict (user_id) do nothing;
    return new;
  end if;

  -- Ensure a unique slug.
  while exists (select 1 from public.organizations where slug = final_slug) loop
    final_slug := base_slug || '-' || substr(new_org::text, 1, 4);
  end loop;

  insert into public.organizations (id, name, slug, created_by)
  values (new_org, firm, final_slug, new.id);
  insert into public.memberships (id, user_id, org_id, role)
  values (gen_random_uuid(), new.id, new_org, 'admin')
  on conflict (user_id, org_id) do nothing;
  return new;
end$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users for each row execute function public.handle_new_user();

-- 4. platform_admins table: readable by the admin themself; writes via service role.
alter table public.platform_admins enable row level security;
grant select on public.platform_admins to authenticated;
drop policy if exists platform_admins_self on public.platform_admins;
create policy platform_admins_self on public.platform_admins
  for select to authenticated using (user_id = auth.uid());

-- 5. Extend every org-scoped read policy so platform admins see all orgs.
--    (Rebuilds the policies created in 0004_tenancy_rls.sql with the extra clause.)
do $$
declare t text;
begin
  foreach t in array array[
    'obligations','tasks','alerts','company_documents','company_profiles',
    'gaps','controls','control_tests','products','policies',
    'audit_events','obligation_controls','obligation_policies','obligation_products'
  ] loop
    execute format('drop policy if exists %I on public.%I', t || '_org_select', t);
    execute format(
      'create policy %I on public.%I for select to authenticated '
      'using (org_id is null or org_id in (select public.user_org_ids()) '
      'or public.is_platform_admin())',
      t || '_org_select', t
    );
  end loop;
end $$;

-- organizations: a user reads their own orgs; a platform admin reads all.
drop policy if exists organizations_member on public.organizations;
create policy organizations_member on public.organizations
  for select to authenticated
  using (id in (select public.user_org_ids()) or public.is_platform_admin());

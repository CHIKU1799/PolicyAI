-- Org invites: RLS + invite-aware signup provisioning. Run in Supabase AFTER
-- alembic 0014 (which creates public.org_invites).
--
-- What changes vs 0012_multitenant_provisioning.sql:
--   * org_invites gets RLS: an org's own admins can read that org's invites
--     (platform admins read all). All writes go through the worker's service
--     role, which bypasses RLS.
--   * handle_new_user() now checks org_invites FIRST: a user signing up with an
--     invited email joins the inviting org with the invited role, and no fresh
--     org is provisioned for them. Everyone else gets the existing per-firm
--     provisioning from 0012, unchanged.
--
-- Idempotent: safe to re-run.

-- 1. RLS on org_invites: readable by the target org's admins only.
alter table public.org_invites enable row level security;
grant select on public.org_invites to authenticated;
drop policy if exists org_invites_admin_select on public.org_invites;
create policy org_invites_admin_select on public.org_invites
  for select to authenticated
  using (
    org_id in (select m.org_id from public.memberships m
               where m.user_id = auth.uid() and m.role = 'admin')
    or public.is_platform_admin()
  );

-- 2. Invite-aware signup provisioning. Invite match first; then the 0012 logic
--    verbatim (platform-admin short-circuit, slugged per-firm org creation).
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  inv        public.org_invites%rowtype;
  firm       text := coalesce(nullif(trim(new.raw_user_meta_data->>'company_name'), ''),
                              split_part(new.email, '@', 1));
  new_org    uuid := gen_random_uuid();
  base_slug  text := coalesce(nullif(public.slugify(firm), ''), 'firm');
  final_slug text := base_slug;
begin
  -- 0. Invited users join the inviting org with the invited role. Oldest
  --    pending invite wins; no fresh org is created for them.
  select * into inv from public.org_invites
   where lower(email) = lower(new.email) and accepted_at is null
   order by created_at asc limit 1;
  if found then
    insert into public.memberships (id, user_id, org_id, role)
    values (gen_random_uuid(), new.id, inv.org_id,
            case when inv.role = 'admin' then 'admin' else 'member' end)
    on conflict (user_id, org_id) do nothing;
    update public.org_invites set accepted_at = now() where id = inv.id;
    return new;
  end if;

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

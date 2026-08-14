-- 0018: platform admins can READ every org's rows through RLS.
--
-- The admin console already sees cross-org data because the worker uses the
-- service role, but the platform admin's own browser session could only see
-- org_id-null rows (they hold no memberships). This adds an additive
-- SELECT-only policy per org-scoped table, keyed on membership of
-- public.platform_admins. Read-only on purpose: writes into customer data
-- stay impossible from the admin's browser session.

create or replace function public.is_platform_admin()
returns boolean language sql security definer stable set search_path = public as $$
  select exists (select 1 from public.platform_admins where user_id = auth.uid())
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'obligations','gaps','controls','control_tests','policies','policy_versions',
    'tasks','alerts','products','audit_events','obligation_controls',
    'obligation_policies','obligation_products','company_documents',
    'company_profiles','requirements','memberships','organizations'
  ] loop
    if to_regclass('public.' || t) is null then
      continue;
    end if;
    execute format('drop policy if exists %I on public.%I', t || '_platform_admin_read', t);
    execute format(
      'create policy %I on public.%I for select to authenticated using (public.is_platform_admin())',
      t || '_platform_admin_read', t
    );
  end loop;
end $$;

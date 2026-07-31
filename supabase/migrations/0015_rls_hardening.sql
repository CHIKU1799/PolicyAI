-- 0015: RLS hardening from the security audit (Jul 2026). NOT YET APPLIED.
--
-- Findings this fixes (verified live with scripts/rls_spot_check.py using the
-- public ANON key, no user session):
--   1. demo_requests, llm_cache, raw_documents, nodes, edges were created by
--      Alembic and never had RLS enabled. Supabase grants privileges on new
--      public tables to anon/authenticated by default, so an unauthenticated
--      caller could SELECT, UPDATE and DELETE all of them via REST: contact
--      form PII (demo_requests), the LLM cache, the raw document lake, and
--      the shared knowledge graph itself.
--   2. obligations_anon_update (from 0009) let ANY anonymous caller update
--      any org's obligations (confirmed live: anon PATCH returned 204).
--   3. The kb storage upload policy allowed anonymous uploads to any path;
--      uploads are now authenticated-only and confined to the caller's own
--      org folder (the worker enforces the same prefix on processing).
--
-- Idempotent: safe to re-run. The worker/service role bypasses RLS throughout.

-- ---------------------------------------------------------------------------
-- 1a. Tables that must be service-role only: enable RLS, no policies at all,
--     and strip the default REST grants.
do $$
declare t text;
begin
  foreach t in array array['demo_requests', 'llm_cache', 'raw_documents'] loop
    if to_regclass('public.' || t) is not null then
      execute format('alter table public.%I enable row level security', t);
      execute format('revoke all on public.%I from anon, authenticated', t);
    end if;
  end loop;
end $$;

-- 1b. Shared knowledge graph: public READ is intentional (graph explorer,
--     the serverless /api/ask grounding); everything else denied.
do $$
declare t text;
begin
  foreach t in array array['nodes', 'edges'] loop
    if to_regclass('public.' || t) is not null then
      execute format('alter table public.%I enable row level security', t);
      execute format('revoke insert, update, delete on public.%I from anon, authenticated', t);
      execute format('drop policy if exists %I on public.%I', t || '_public_select', t);
      execute format(
        'create policy %I on public.%I for select to anon, authenticated using (true)',
        t || '_public_select', t
      );
    end if;
  end loop;
end $$;

-- Alembic bookkeeping table: nobody's business over REST.
do $$
begin
  if to_regclass('public.alembic_version') is not null then
    alter table public.alembic_version enable row level security;
    revoke all on public.alembic_version from anon, authenticated;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 2. obligations: replace the anonymous free-for-all update policy with an
--    org-scoped authenticated one (UI triage: open -> in_review -> ...).
drop policy if exists obligations_anon_update on public.obligations;
revoke update on public.obligations from anon;
grant update on public.obligations to authenticated;
drop policy if exists obligations_org_update on public.obligations;
create policy obligations_org_update on public.obligations
  for update to authenticated
  using (org_id in (select public.user_org_ids()) or public.is_platform_admin())
  with check (org_id in (select public.user_org_ids()) or public.is_platform_admin());

-- ---------------------------------------------------------------------------
-- 3. Belt and braces: the anon role never writes anything in public, and any
--    table created in the future starts without anon write grants.
revoke insert, update, delete on all tables in schema public from anon;
alter default privileges in schema public
  revoke insert, update, delete on tables from anon;

-- ---------------------------------------------------------------------------
-- 4. Storage: knowledge-base uploads are authenticated-only and must land in
--    the caller's own org folder ("<org_id>/<file>"). The worker refuses to
--    process any path outside the caller's org, so both ends now agree.
drop policy if exists "kb anon upload" on storage.objects;
drop policy if exists "kb org upload" on storage.objects;
create policy "kb org upload" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'company-documents'
    and (storage.foldername(name))[1] in (
      select m.org_id::text from public.memberships m where m.user_id = auth.uid()
    )
  );

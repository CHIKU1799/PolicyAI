-- RLS for the requirements table (atomic compliance requirements per regulation).
-- Reference data: readable by the app; writes happen only from the worker via the
-- service role (which bypasses RLS). Mirrors the read-only grant used for the graph
-- reference tables.

grant usage on schema public to anon, authenticated;
grant select on public.requirements to anon, authenticated;

alter table public.requirements enable row level security;
drop policy if exists requirements_anon_select on public.requirements;
create policy requirements_anon_select
  on public.requirements for select to anon, authenticated using (true);

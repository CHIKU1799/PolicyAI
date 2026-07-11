-- Let the UI triage obligations (open -> in_review -> addressed / dismissed / reopen),
-- mirroring the existing task-board update grant. Status changes are written directly
-- to Supabase from the obligations page.

grant update on public.obligations to anon, authenticated;

drop policy if exists obligations_anon_update on public.obligations;
create policy obligations_anon_update on public.obligations
  for update to anon, authenticated using (true) with check (true);

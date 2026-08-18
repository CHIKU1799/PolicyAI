-- 0016: let org members manage control-to-obligation links from the browser.
--
-- The Controls page now creates controls (C-004 etc.) and links them to the
-- obligations they satisfy. controls/control_tests were already browser-
-- writable (0003, org-scoped in 0004); obligation_controls was select-only,
-- so the link insert had no grant and no write policy. Same org-scoping rule
-- as the other GRC tables; delete allowed so a mis-link can be removed.

grant insert, delete on public.obligation_controls to authenticated;

drop policy if exists obligation_controls_org_insert on public.obligation_controls;
create policy obligation_controls_org_insert on public.obligation_controls
  for insert to authenticated
  with check (org_id is null or org_id in (select public.user_org_ids()));

drop policy if exists obligation_controls_org_delete on public.obligation_controls;
create policy obligation_controls_org_delete on public.obligation_controls
  for delete to authenticated
  using (org_id is null or org_id in (select public.user_org_ids()));

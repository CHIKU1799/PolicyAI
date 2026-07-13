-- 0013: alert the moment a control fails.
--
-- Control tests are written from the browser straight to Supabase (no worker in
-- the path), so the alert has to be raised in the database itself. Two triggers:
--   1. control_tests: a recorded test with result 'failed'/'ineffective' raises
--      an alert and flips the control's effectiveness to 'ineffective'.
--   2. controls: any transition of effectiveness to 'ineffective' (manual edits
--      included) raises an alert, deduped so trigger 1 doesn't double-fire.

create extension if not exists pgcrypto;

create or replace function public.policyai_alert_on_failed_test()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  ctl record;
begin
  if new.result is null or lower(new.result) not in ('failed', 'fail', 'ineffective') then
    return new;
  end if;
  select id, org_id, title, effectiveness into ctl from public.controls where id = new.control_id;
  if ctl.id is null then
    return new;
  end if;
  insert into public.alerts (id, org_id, kind, message, created_at)
  values (
    gen_random_uuid(),
    ctl.org_id,
    'control_failed',
    'Control failed testing: ' || ctl.title,
    now()
  );
  -- Reflect the failure on the control itself; suppress trigger 2's duplicate
  -- alert by doing it inside the same statement chain (see pg_trigger_depth).
  update public.controls
     set effectiveness = 'ineffective', last_tested_at = coalesce(new.performed_at, now())
   where id = ctl.id;
  return new;
end;
$$;

create or replace function public.policyai_alert_on_ineffective_control()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Skip when the flip came from the failed-test trigger (already alerted).
  if pg_trigger_depth() > 1 then
    return new;
  end if;
  if new.effectiveness = 'ineffective' and coalesce(old.effectiveness, '') <> 'ineffective' then
    insert into public.alerts (id, org_id, kind, message, created_at)
    values (
      gen_random_uuid(),
      new.org_id,
      'control_failed',
      'Control marked ineffective: ' || new.title,
      now()
    );
  end if;
  return new;
end;
$$;

drop trigger if exists trg_policyai_failed_test on public.control_tests;
create trigger trg_policyai_failed_test
  after insert or update of result on public.control_tests
  for each row execute function public.policyai_alert_on_failed_test();

drop trigger if exists trg_policyai_ineffective_control on public.controls;
create trigger trg_policyai_ineffective_control
  after update of effectiveness on public.controls
  for each row execute function public.policyai_alert_on_ineffective_control();

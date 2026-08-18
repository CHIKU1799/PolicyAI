-- 0017: DB-side id defaults for tables the browser inserts into.
--
-- The SQLAlchemy models generate UUIDs in Python (default=uuid4, no
-- server_default), which works for the worker but leaves PostgREST inserts
-- from the Controls page failing with "null value in column id". pgcrypto is
-- already present (0013).

alter table public.controls alter column id set default gen_random_uuid();
alter table public.control_tests alter column id set default gen_random_uuid();
alter table public.obligation_controls alter column id set default gen_random_uuid();

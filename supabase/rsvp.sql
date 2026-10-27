-- RSVP storage for the invitation (Supabase project: mustafa-joudy-wedding-rsvp).
-- Run once in the SQL editor. Guests can only add a reply; reading the list
-- goes through list_rsvps(), which checks the passcode set with set_rsvp_passcode().

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.rsvps (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  name text not null check (char_length(btrim(name)) between 1 and 120),
  attending boolean not null,
  guests smallint not null default 1 check (guests between 0 and 10),
  message text check (char_length(message) <= 1000)
);

alter table public.rsvps enable row level security;

-- guests: insert only, no reading, editing or deleting
revoke all on public.rsvps from anon, authenticated;
grant insert (name, attending, guests, message) on public.rsvps to anon;
drop policy if exists "guests can reply" on public.rsvps;
create policy "guests can reply" on public.rsvps for insert to anon with check (true);

-- the passcode lives outside the API-exposed schema, stored as a bcrypt hash
create schema if not exists private;
revoke all on schema private from anon, authenticated;
create table if not exists private.settings (key text primary key, value text not null);

create or replace function public.set_rsvp_passcode(passcode text)
returns void language sql security definer set search_path = '' as $$
  insert into private.settings (key, value)
  values ('rsvp_passcode', extensions.crypt(passcode, extensions.gen_salt('bf')))
  on conflict (key) do update set value = excluded.value;
$$;
-- only the SQL editor (postgres role) may set it
revoke all on function public.set_rsvp_passcode(text) from public, anon, authenticated;

create or replace function public.list_rsvps(passcode text)
returns setof public.rsvps language plpgsql stable security definer set search_path = '' as $$
begin
  if not exists (
    select 1 from private.settings s
    where s.key = 'rsvp_passcode' and s.value = extensions.crypt(passcode, s.value)
  ) then
    raise exception 'wrong passcode' using errcode = '28P01';
  end if;
  return query select * from public.rsvps r order by r.created_at desc;
end;
$$;
revoke all on function public.list_rsvps(text) from public;
grant execute on function public.list_rsvps(text) to anon;

-- then, with your own passcode:
--   select public.set_rsvp_passcode('your passcode');

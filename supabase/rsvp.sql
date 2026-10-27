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

-- failed passcode tries, for the lockout in list_rsvps()
create table if not exists private.login_attempts (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  client text not null
);
alter table private.login_attempts enable row level security;
create index if not exists login_attempts_at on private.login_attempts (at);

create or replace function public.set_rsvp_passcode(passcode text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if char_length(passcode) < 6 then
    raise exception 'use a passcode of at least 6 characters';
  end if;
  insert into private.settings (key, value)
  values ('rsvp_passcode', extensions.crypt(passcode, extensions.gen_salt('bf', 10)))
  on conflict (key) do update set value = excluded.value;
  delete from private.login_attempts;  -- a new passcode clears any lockout
end;
$$;
-- only the SQL editor (postgres role) may set it
revoke all on function public.set_rsvp_passcode(text) from public, anon, authenticated;

-- Returns {"ok": true, "rows": [...]} or {"ok": false, "error": "passcode" | "locked"}.
-- It answers instead of raising so that a failed try is recorded, not rolled back.
-- Limits: 5 wrong tries per client and 20 overall in any 15 minutes (the overall
-- cap holds even if a client fakes its address).
drop function if exists public.list_rsvps(text);
create function public.list_rsvps(passcode text)
returns jsonb language plpgsql volatile security definer set search_path = '' as $$
declare
  headers jsonb := coalesce(nullif(current_setting('request.headers', true), '')::jsonb, '{}'::jsonb);
  who text := coalesce(headers ->> 'cf-connecting-ip', btrim(split_part(headers ->> 'x-forwarded-for', ',', 1)), 'unknown');
  since timestamptz := now() - interval '15 minutes';
begin
  if (select count(*) from private.login_attempts a where a.at > since and a.client = who) >= 5
     or (select count(*) from private.login_attempts a where a.at > since) >= 20 then
    return jsonb_build_object('ok', false, 'error', 'locked');
  end if;

  if not exists (
    select 1 from private.settings s
    where s.key = 'rsvp_passcode' and s.value = extensions.crypt(passcode, s.value)
  ) then
    insert into private.login_attempts (client) values (who);
    delete from private.login_attempts a where a.at < now() - interval '1 day';
    return jsonb_build_object('ok', false, 'error', 'passcode');
  end if;

  return jsonb_build_object('ok', true, 'rows', coalesce(
    (select jsonb_agg(to_jsonb(r) order by r.created_at desc) from public.rsvps r), '[]'::jsonb));
end;
$$;
revoke all on function public.list_rsvps(text) from public;
grant execute on function public.list_rsvps(text) to anon;

-- then, with your own passcode (6+ characters):
--   select public.set_rsvp_passcode('your passcode');
-- if the page says it's locked and you need in sooner than 15 minutes:
--   delete from private.login_attempts;

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

-- addresses that have opened the list; they still get in when the overall ceiling is hit
create table if not exists private.trusted_clients (
  client text primary key,
  last_ok timestamptz not null default now()
);
alter table private.trusted_clients enable row level security;

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

-- Returns {"ok": true, "rows": [...]} or {"ok": false, "error": "passcode" | "locked" | "busy"}.
-- It answers instead of raising so that a failed try is recorded, not rolled back.
-- The client is the address Cloudflare puts in cf-connecting-ip (Cloudflare rejects
-- requests that set it themselves; X-Forwarded-For is ignored because callers can
-- fake it). IPv6 addresses count per /64, the block one subscriber usually holds.
--   locked: 5 wrong tries from this client in 15 minutes.
--   busy:   30 wrong tries from all clients in 15 minutes, and this client has
--           never opened the list. Clients that have get through, so a flood of
--           failures can't lock the couple out.
drop function if exists public.list_rsvps(text);
create function public.list_rsvps(passcode text)
returns jsonb language plpgsql volatile security definer
set search_path = '' set lock_timeout = '3s' as $$
declare
  headers jsonb := coalesce(nullif(current_setting('request.headers', true), '')::jsonb, '{}'::jsonb);
  who text;
  since timestamptz := now() - interval '15 minutes';
begin
  begin
    who := case when family((headers ->> 'cf-connecting-ip')::inet) = 6
      then host(network(set_masklen((headers ->> 'cf-connecting-ip')::inet, 64))) || '/64'
      else host((headers ->> 'cf-connecting-ip')::inet) end;
  exception when others then
    who := null;
  end;
  who := coalesce(who, 'unknown');

  -- one check at a time per client, so its parallel requests can't slip past the count
  perform pg_advisory_xact_lock(hashtext('public.list_rsvps:' || who));

  if (select count(*) from private.login_attempts a where a.client = who and a.at > since) >= 5 then
    return jsonb_build_object('ok', false, 'error', 'locked');
  end if;

  if (select count(*) from private.login_attempts a where a.at > since) >= 30
     and not exists (select 1 from private.trusted_clients t
                     where t.client = who and t.last_ok > now() - interval '90 days') then
    return jsonb_build_object('ok', false, 'error', 'busy');
  end if;

  if not exists (
    select 1 from private.settings s
    where s.key = 'rsvp_passcode' and s.value = extensions.crypt(passcode, s.value)
  ) then
    insert into private.login_attempts (client) values (who);
    delete from private.login_attempts a where a.at < now() - interval '1 day';
    return jsonb_build_object('ok', false, 'error', 'passcode');
  end if;

  insert into private.trusted_clients (client) values (who)
  on conflict (client) do update set last_ok = now();

  return jsonb_build_object('ok', true, 'rows', coalesce(
    (select jsonb_agg(to_jsonb(r) order by r.created_at desc) from public.rsvps r), '[]'::jsonb));
end;
$$;
revoke all on function public.list_rsvps(text) from public;
grant execute on function public.list_rsvps(text) to anon;

-- then, with your own passcode (6+ characters):
--   select public.set_rsvp_passcode('your passcode');
-- if the page says it's locked or busy and you need in sooner than 15 minutes:
--   delete from private.login_attempts;

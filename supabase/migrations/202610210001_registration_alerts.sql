-- File d'alertes des nouvelles inscriptions. Aucun envoi réseau dans la transaction d'inscription.
-- Aucune reprise des comptes existants, ni modification des rôles ou validations.
begin;
create table public.urgent_registration_alerts (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null unique references public.profiles(id) on delete cascade,
 created_at timestamptz not null default now(),
 status text not null default 'pending' check(status in ('pending','sent','failed')),
 attempts integer not null default 0 check(attempts between 0 and 8),
 next_attempt_at timestamptz not null default now(),
 lease_token uuid,
 locked_until timestamptz,
 sent_at timestamptz,
 provider_id text,
 last_error_code text
);
alter table public.urgent_registration_alerts enable row level security;
revoke all on public.urgent_registration_alerts from public,anon,authenticated;
create index urgent_registration_alerts_pending on public.urgent_registration_alerts(next_attempt_at) where status='pending';
create function public.urgent_queue_registration_alert()
returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.role in ('client','carrier') then
  insert into public.urgent_registration_alerts(user_id) values(new.id) on conflict(user_id) do nothing;
 end if;
 return new;
end;
$$;
revoke all on function public.urgent_queue_registration_alert() from public,anon,authenticated;
create trigger urgent_queue_registration_alert after insert on public.profiles
for each row execute function public.urgent_queue_registration_alert();

-- Réservé au worker serveur : verrous SKIP LOCKED + bail pour ne pas doubler les envois concurrents.
create function public.urgent_claim_registration_alerts()
returns table(alert_id uuid,lease_token uuid,user_id uuid,company_id uuid,company_name text,account_type text,email text,siret text,email_confirmed boolean,registered_at timestamptz)
language plpgsql security definer set search_path='' as $$
begin
 update public.urgent_registration_alerts a set status='failed',last_error_code=case when a.attempts>=8 then 'attempts_exhausted' else 'delivery_window_expired' end
 where a.status='pending' and (a.attempts>=8 or a.created_at<now()-interval '23 hours') and coalesce(a.locked_until,'-infinity'::timestamptz)<=now();
 return query
 with due as (
  select a.id from public.urgent_registration_alerts a
  where a.status='pending' and a.attempts<8 and a.next_attempt_at<=now()
   and coalesce(a.locked_until,'-infinity'::timestamptz)<=now()
  order by a.created_at,a.id limit 5 for update skip locked
 ), claimed as (
  update public.urgent_registration_alerts a set attempts=a.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval '5 minutes'
  from due where a.id=due.id returning a.*
 )
 select a.id,a.lease_token,a.user_id,p.company_id,c.name::text,p.role::text,u.email::text,
  u.raw_user_meta_data->>'business_siret',u.email_confirmed_at is not null,a.created_at
 from claimed a join public.profiles p on p.id=a.user_id
 join auth.users u on u.id=a.user_id left join public.companies c on c.id=p.company_id;
end;
$$;
create function public.urgent_finish_registration_alert(p_alert_id uuid,p_lease_token uuid,p_success boolean,p_provider_id text default null,p_error_code text default null)
returns boolean language plpgsql security definer set search_path='' as $$
declare changed integer;
begin
 update public.urgent_registration_alerts a set
 status=case when p_success then 'sent' when a.attempts>=8 then 'failed' else 'pending' end,
 sent_at=case when p_success then now() else null end,
 provider_id=case when p_success then left(p_provider_id,200) else null end,
 last_error_code=case when p_success then null else left(coalesce(p_error_code,'send_error'),80) end,
 next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(a.attempts-1))::integer)),
 lease_token=null,locked_until=null
 where a.id=p_alert_id and a.lease_token=p_lease_token and a.status='pending';
 get diagnostics changed=row_count;
 return changed=1;
end;
$$;
revoke all on function public.urgent_claim_registration_alerts(),public.urgent_finish_registration_alert(uuid,uuid,boolean,text,text) from public,anon,authenticated;
grant execute on function public.urgent_claim_registration_alerts(),public.urgent_finish_registration_alert(uuid,uuid,boolean,text,text) to service_role;
commit;

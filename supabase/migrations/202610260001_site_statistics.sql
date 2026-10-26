-- Mesure facultative minimale et rapport privé quotidien à 08:00 Paris.
-- Nécessite le schéma professionnel et la marketplace déjà installés.
begin;
create table public.urgent_site_stats_settings (
 id boolean primary key default true check(id),
 enabled boolean not null default true,
 first_day date not null default (now() at time zone 'Europe/Paris')::date
);
insert into public.urgent_site_stats_settings(id) values(true);
create table public.urgent_site_events (
 id bigint generated always as identity primary key,
 occurred_at timestamptz not null default now(),
 kind text not null check(kind in ('page_view','account_seen')),
 page text not null,
 source text not null,medium text not null,campaign text not null,
 user_id uuid references auth.users(id) on delete set null,
 company_id uuid references public.companies(id) on delete set null
);
create index urgent_site_events_time on public.urgent_site_events(occurred_at);
create table public.urgent_site_event_limits(day date primary key,events integer not null);
create table public.urgent_site_reports (
 id uuid primary key default gen_random_uuid(),day date not null unique,snapshot jsonb not null,
 created_at timestamptz not null default now(),
 status text not null default 'pending' check(status in ('pending','sent','failed')),
 attempts integer not null default 0 check(attempts between 0 and 8),
 next_attempt_at timestamptz not null default now(),
 lease_token uuid,locked_until timestamptz,sent_at timestamptz,provider_id text,last_error_code text
);
alter table public.urgent_site_stats_settings enable row level security;
alter table public.urgent_site_events enable row level security;
alter table public.urgent_site_event_limits enable row level security;
alter table public.urgent_site_reports enable row level security;
revoke all on public.urgent_site_stats_settings,public.urgent_site_events,public.urgent_site_event_limits,public.urgent_site_reports from public,anon,authenticated,service_role;
revoke all on sequence public.urgent_site_events_id_seq from public,anon,authenticated,service_role;

create function public.urgent_site_stats_public_status()returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('enabled',coalesce((select enabled from public.urgent_site_stats_settings where id),false));
$$;
revoke all on function public.urgent_site_stats_public_status()from public;
grant execute on function public.urgent_site_stats_public_status()to anon,authenticated;

create function public.urgent_record_site_event(p_page text,p_source text default 'direct',p_medium text default 'direct',p_campaign text default 'aucune',p_kind text default 'page_view',p_consent boolean default false)
returns void language plpgsql security definer set search_path='' as $$
declare actor uuid:=auth.uid();company uuid;today date:=(now() at time zone 'Europe/Paris')::date;accepted integer;
begin
 if p_consent is distinct from true or not coalesce((select enabled from public.urgent_site_stats_settings where id),false) then return;end if;
 if p_page not in ('/','/mentions-legales.html','/confidentialite.html','/conditions-professionnelles.html','/conditions-professionnelles-v3.html','/conditions-professionnelles-v4.html') or p_page is null then return;end if;
 if p_kind not in ('page_view','account_seen') or p_kind is null or (p_kind='account_seen' and actor is null) then return;end if;
 if exists(select 1 from public.profiles where id=actor and role::text='admin') then return;end if;
 select company_id into company from public.profiles where id=actor;
 -- Plafond atomique de protection du volume ; aucune IP ou empreinte de navigateur stockée.
 insert into public.urgent_site_event_limits as limits(day,events)values(today,1)
 on conflict(day)do update set events=limits.events+1 where limits.events<10000 returning events into accepted;
 if not found then return;end if;
 insert into public.urgent_site_events(kind,page,source,medium,campaign,user_id,company_id)
 values(p_kind,p_page,
 case when p_source in ('direct','google','bing','linkedin','instagram','tiktok','facebook') then p_source else 'autre' end,
 case when p_medium in ('direct','organic','referral','paid_social','organic_social','email') then p_medium else 'autre' end,
 case when p_campaign in ('lancement_local','premieres_demandes','linkedin_contacts') then p_campaign else 'aucune' end,actor,company);
end;
$$;

create function public.urgent_build_site_report(p_day date)returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare begin_at timestamptz;end_at timestamptz;views integer;accounts integer;new_accounts integer;requests integer;sources jsonb;pages jsonb;people jsonb;
begin
 if p_day is null or p_day>=(now() at time zone 'Europe/Paris')::date then raise exception 'Journée clôturée requise';end if;
 begin_at:=p_day::timestamp at time zone 'Europe/Paris';end_at:=(p_day+1)::timestamp at time zone 'Europe/Paris';
 select count(*) filter(where kind='page_view'),count(distinct user_id) into views,accounts from public.urgent_site_events where occurred_at>=begin_at and occurred_at<end_at;
 select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc,x.source),'[]'::jsonb)into sources from(select source,count(*)::integer as count from public.urgent_site_events where kind='page_view' and occurred_at>=begin_at and occurred_at<end_at group by source)x;
 select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc,x.page),'[]'::jsonb)into pages from(select page,count(*)::integer as count from public.urgent_site_events where kind='page_view' and occurred_at>=begin_at and occurred_at<end_at group by page)x;
 select coalesce(jsonb_agg(to_jsonb(x) order by x.last_seen desc,x.user_id),'[]'::jsonb)into people from(
  select e.user_id,u.email,c.name as company_name,p.role::text as role,max(e.occurred_at)as last_seen,count(*)filter(where e.kind='page_view')::integer as page_views
  from public.urgent_site_events e join auth.users u on u.id=e.user_id left join public.profiles p on p.id=e.user_id left join public.companies c on c.id=p.company_id
  where e.occurred_at>=begin_at and e.occurred_at<end_at group by e.user_id,u.email,c.name,p.role order by max(e.occurred_at)desc,e.user_id limit 50
 )x;
 select count(*) into new_accounts from auth.users u where u.created_at>=begin_at and u.created_at<end_at;
 select count(*) into requests from public.urgent_shipments s where s.created_at>=begin_at and s.created_at<end_at and not s.is_test;
 return jsonb_build_object('day',p_day,'generated_at',now(),'timezone','Europe/Paris','page_views',views,'known_accounts',accounts,'new_accounts',new_accounts,'new_requests',requests,'sources',sources,'pages',pages,'people',people,'people_limit',50);
end;
$$;
create function public.urgent_purge_site_stats()returns void language plpgsql security definer set search_path='' as $$
begin
 delete from public.urgent_site_events where occurred_at<now()-interval '30 days';
 delete from public.urgent_site_event_limits where day<(now() at time zone 'Europe/Paris')::date-31;
 delete from public.urgent_site_reports where created_at<now()-interval '90 days';
end;
$$;
create function public.urgent_claim_site_report()
returns table(report_id uuid,lease_token uuid,day date,snapshot jsonb)
language plpgsql security definer set search_path='' as $$
begin
 perform public.urgent_purge_site_stats();
 if not coalesce((select enabled from public.urgent_site_stats_settings where id),false)then return;end if;
 -- Pas de rattrapage en masse : au maximum les sept journées clôturées récentes.
 insert into public.urgent_site_reports(day,snapshot)
 select d::date,public.urgent_build_site_report(d::date)
 from generate_series(greatest((select first_day from public.urgent_site_stats_settings where id),(now() at time zone 'Europe/Paris')::date-7)::timestamp,((now() at time zone 'Europe/Paris')::date-1)::timestamp,interval '1 day') d
 where now()>=((d+interval '1 day'+interval '8 hours')at time zone 'Europe/Paris')
 on conflict on constraint urgent_site_reports_day_key do nothing;
 update public.urgent_site_reports r set status='failed',last_error_code=case when r.attempts>=8 then 'attempts_exhausted' else 'delivery_window_expired' end
 where r.status='pending' and(r.attempts>=8 or r.created_at<now()-interval '23 hours')and coalesce(r.locked_until,'-infinity'::timestamptz)<=now();
 return query with due as(
 select r.id from public.urgent_site_reports r where r.status='pending' and r.attempts<8 and r.next_attempt_at<=now() and coalesce(r.locked_until,'-infinity'::timestamptz)<=now()order by r.day limit 1 for update skip locked
 ),claimed as(update public.urgent_site_reports r set attempts=r.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval '5 minutes' from due where r.id=due.id returning r.*)
 select r.id,r.lease_token,r.day,r.snapshot from claimed r;
end;
$$;
create function public.urgent_finish_site_report(p_report_id uuid,p_lease_token uuid,p_success boolean,p_provider_id text default null,p_error_code text default null,p_permanent boolean default false)
returns boolean language plpgsql security definer set search_path='' as $$
declare changed integer;
begin
 update public.urgent_site_reports r set status=case when p_success then 'sent' when p_permanent or r.attempts>=8 then 'failed' else 'pending' end,
 sent_at=case when p_success then now()else null end,provider_id=case when p_success then left(p_provider_id,200)else null end,last_error_code=case when p_success then null else left(coalesce(p_error_code,'send_error'),80)end,
 next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(r.attempts-1))::integer)),lease_token=null,locked_until=null
 where r.id=p_report_id and r.lease_token=p_lease_token and r.status='pending';get diagnostics changed=row_count;return changed=1;
end;
$$;
revoke all on function public.urgent_record_site_event(text,text,text,text,text,boolean)from public;
grant execute on function public.urgent_record_site_event(text,text,text,text,text,boolean)to anon,authenticated;
revoke all on function public.urgent_build_site_report(date),public.urgent_purge_site_stats(),public.urgent_claim_site_report(),public.urgent_finish_site_report(uuid,uuid,boolean,text,text,boolean)from public,anon,authenticated;
grant execute on function public.urgent_build_site_report(date),public.urgent_purge_site_stats(),public.urgent_claim_site_report(),public.urgent_finish_site_report(uuid,uuid,boolean,text,text,boolean)to service_role;
-- Le cron d'e-mails existant est réutilisé ; cette tâche distincte assure la purge même si les envois sont suspendus.
do $maintenance$
begin
 if to_regclass('cron.job')is not null then
  execute $cron$select cron.schedule('urgent-site-stats-retention','15 2 * * *','select public.urgent_purge_site_stats();')$cron$;
 end if;
end;
$maintenance$;
commit;
select enabled,first_day,'08:00 Europe/Paris' as report_time,to_regclass('cron.job')is not null as retention_scheduler_available from public.urgent_site_stats_settings;

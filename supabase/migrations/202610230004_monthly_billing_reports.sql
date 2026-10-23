-- Relevés mensuels privés de préparation à la facturation. Aucune facture ni frais créé.
begin;
create table public.urgent_monthly_report_settings (
 id boolean primary key default true check(id),
 first_month date not null check(extract(day from first_month)=1)
);
insert into public.urgent_monthly_report_settings(id,first_month)
values(true,date_trunc('month',now() at time zone 'Europe/Paris')::date);
create table public.urgent_monthly_reports (
 id uuid primary key default gen_random_uuid(),
 month date not null unique check(extract(day from month)=1),
 snapshot jsonb not null,
 created_at timestamptz not null default now(),
 status text not null default 'pending' check(status in ('pending','sent','failed')),
 attempts integer not null default 0 check(attempts between 0 and 8),
 next_attempt_at timestamptz not null default now(),
 lease_token uuid,locked_until timestamptz,sent_at timestamptz,provider_id text,last_error_code text
);
alter table public.urgent_monthly_report_settings enable row level security;
alter table public.urgent_monthly_reports enable row level security;
revoke all on public.urgent_monthly_report_settings,public.urgent_monthly_reports from public,anon,authenticated;

create function public.urgent_build_monthly_report(p_month date) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare start_at timestamptz;end_at timestamptz;entries jsonb;subscriptions jsonb;
begin
 if p_month is null or extract(day from p_month)<>1 or p_month>=date_trunc('month',now() at time zone 'Europe/Paris')::date then
  raise exception 'Mois civil clôturé requis';
 end if;
 start_at:=p_month::timestamp at time zone 'Europe/Paris';
 end_at:=(p_month+interval '1 month')::timestamp at time zone 'Europe/Paris';
 select coalesce(jsonb_agg(to_jsonb(r) order by r.company_id,r.occurred_at,r.entry_id),'[]'::jsonb) into entries from (
  select e.id as entry_id,e.company_id,c.name as company_name,a.siret,e.shipment_id,e.offer_id,e.kind,
   e.transport_ht,e.amount_ht_cents,e.occurred_at,e.reason,e.external_invoice_reference as invoice_reference,
   e.parent_id,(select original.external_invoice_reference from public.urgent_service_entries original where original.id=e.parent_id) as original_invoice_reference,
   s.origin,s.destination
  from public.urgent_service_entries e join public.companies c on c.id=e.company_id
  join public.urgent_shipments s on s.id=e.shipment_id
  left join public.urgent_business_access a on a.company_id=e.company_id
  where e.occurred_at>=start_at and e.occurred_at<end_at and not s.is_test
 ) r;
 select coalesce(jsonb_agg(to_jsonb(r) order by r.company_id,r.recorded_at,r.period_id),'[]'::jsonb) into subscriptions from (
  select p.id as period_id,p.company_id,c.name as company_name,p.plan,p.starts_at,p.ends_at,
   p.recorded_at,p.received_cents,p.invoice_reference,p.revoked_at
  from public.urgent_manual_subscriptions p join public.companies c on c.id=p.company_id
  where (p.recorded_at>=start_at and p.recorded_at<end_at) or (p.revoked_at>=start_at and p.revoked_at<end_at)
 ) r;
 return jsonb_build_object('month',p_month,'generated_at',now(),'timezone','Europe/Paris','entries',entries,'subscriptions',subscriptions);
end;
$$;
create function public.urgent_claim_monthly_report()
returns table(report_id uuid,lease_token uuid,month date,snapshot jsonb)
language plpgsql security definer set search_path='' as $$
begin
 -- Chaque mois est figé au premier traitement après le 1er à 08:00 Paris.
 insert into public.urgent_monthly_reports(month,snapshot)
 select m::date,public.urgent_build_monthly_report(m::date)
 from generate_series((select first_month from public.urgent_monthly_report_settings where id)::timestamp,
  date_trunc('month',now() at time zone 'Europe/Paris')-interval '1 month',interval '1 month') m
 where now()>=((m+interval '1 month'+interval '8 hours') at time zone 'Europe/Paris')
 and not exists(select 1 from public.urgent_monthly_reports r where r.month=m::date)
 order by m limit 12 on conflict on constraint urgent_monthly_reports_month_key do nothing;
 update public.urgent_monthly_reports r set status='failed',last_error_code=case when r.attempts>=8 then 'attempts_exhausted' else 'delivery_window_expired' end
 where r.status='pending' and (r.attempts>=8 or r.created_at<now()-interval '23 hours')
 and coalesce(r.locked_until,'-infinity'::timestamptz)<=now();
 return query with due as (
  select r.id from public.urgent_monthly_reports r where r.status='pending' and r.attempts<8
   and r.next_attempt_at<=now() and coalesce(r.locked_until,'-infinity'::timestamptz)<=now()
  order by r.month limit 1 for update skip locked
 ),claimed as (
  update public.urgent_monthly_reports r set attempts=r.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval '5 minutes'
  from due where r.id=due.id returning r.*
 ) select r.id,r.lease_token,r.month,r.snapshot from claimed r;
end;
$$;
create function public.urgent_finish_monthly_report(p_report_id uuid,p_lease_token uuid,p_success boolean,p_provider_id text default null,p_error_code text default null,p_permanent boolean default false)
returns boolean language plpgsql security definer set search_path='' as $$
declare changed integer;
begin
 update public.urgent_monthly_reports r set
 status=case when p_success then 'sent' when p_permanent or r.attempts>=8 then 'failed' else 'pending' end,
 sent_at=case when p_success then now() else null end,
 provider_id=case when p_success then left(p_provider_id,200) else null end,
 last_error_code=case when p_success then null else left(coalesce(p_error_code,'send_error'),80) end,
 next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(r.attempts-1))::integer)),
 lease_token=null,locked_until=null
 where r.id=p_report_id and r.lease_token=p_lease_token and r.status='pending';
 get diagnostics changed=row_count;return changed=1;
end;
$$;
revoke all on function public.urgent_build_monthly_report(date),public.urgent_claim_monthly_report(),public.urgent_finish_monthly_report(uuid,uuid,boolean,text,text,boolean) from public,anon,authenticated;
grant execute on function public.urgent_build_monthly_report(date),public.urgent_claim_monthly_report(),public.urgent_finish_monthly_report(uuid,uuid,boolean,text,text,boolean) to service_role;
commit;

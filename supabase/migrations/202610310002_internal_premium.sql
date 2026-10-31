-- Accès Premium interne offert, distinct des règlements et souscriptions payées.
-- Prérequis : commerce manuel et droits transporteur déjà installés.
begin;
create table public.urgent_internal_premium_periods(
 id uuid primary key,company_id uuid not null references public.companies(id),
 starts_at timestamptz not null,ends_at timestamptz not null check(ends_at>starts_at),
 reason text not null check(length(trim(reason))between 10 and 1000),
 granted_by uuid not null references auth.users(id),recorded_at timestamptz not null default now(),
 revoked_at timestamptz,revoked_by uuid references auth.users(id),revocation_reason text
);
alter table public.urgent_internal_premium_periods enable row level security;
revoke all on public.urgent_internal_premium_periods from public,anon,authenticated;
grant select on public.urgent_internal_premium_periods to authenticated;
create policy urgent_internal_premium_read on public.urgent_internal_premium_periods for select to authenticated
 using(company_id=public.urgent_actor_company()or public.urgent_is_admin());
create index urgent_internal_premium_active_idx on public.urgent_internal_premium_periods(company_id,starts_at,ends_at)where revoked_at is null;
create function public.urgent_internal_premium_active(p_company uuid)returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_internal_premium_periods p where p.company_id=p_company and p.revoked_at is null and p.starts_at<=now()and p.ends_at>now());
$$;
revoke all on function public.urgent_internal_premium_active(uuid)from public,anon,authenticated;

create function public.urgent_grant_internal_premium(p_id uuid,p_company uuid,p_first_day date,p_last_day date,p_reason text,p_confirm boolean)returns uuid
language plpgsql security definer set search_path='' as $$
declare previous public.urgent_internal_premium_periods;first_at timestamptz;end_at timestamptz;today date:=(now()at time zone'Europe/Paris')::date;
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_confirm is distinct from true or p_id is null or p_company is null or p_reason is null or length(trim(p_reason))not between 10 and 1000 or p_first_day is null or p_last_day is null then raise exception 'Complétez et confirmez la décision d’accès interne offert';end if;
 perform 1 from public.urgent_business_access where company_id=p_company and registry_checked and pilot_enabled for update;
 if not found or not exists(select 1 from public.profiles where company_id=p_company and role::text='carrier')then raise exception 'Entreprise transporteur autorisée requise';end if;
 first_at:=p_first_day::timestamp at time zone'Europe/Paris';end_at:=(p_last_day+1)::timestamp at time zone'Europe/Paris';
 select * into previous from public.urgent_internal_premium_periods where id=p_id;
 if found then
  if previous.company_id=p_company and previous.starts_at=first_at and previous.ends_at=end_at and previous.reason=trim(p_reason)and previous.granted_by=auth.uid()and previous.revoked_at is null then return previous.id;end if;
  raise exception 'Référence de décision déjà utilisée';
 end if;
 if p_first_day<today or p_first_day>today+366 or p_last_day<p_first_day or p_last_day>p_first_day+365 then raise exception 'Choisissez une période future ou débutant aujourd’hui, de 366 jours maximum';end if;
 if not public.urgent_carrier_documents_ready(p_company)then raise exception 'Dossier documentaire valide requis pour un accès interne';end if;
 if public.urgent_commercial_enabled()and not exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config c on c.id and c.terms_version=t.version where t.company_id=p_company)then raise exception 'Conditions actuelles à accepter par le transporteur';end if;
 if exists(select 1 from public.urgent_internal_premium_periods p where p.company_id=p_company and p.revoked_at is null and p.starts_at<end_at and p.ends_at>first_at)then raise exception 'Une période interne existe déjà sur ces dates';end if;
 insert into public.urgent_internal_premium_periods(id,company_id,starts_at,ends_at,reason,granted_by)values(p_id,p_company,first_at,end_at,trim(p_reason),auth.uid());
 insert into public.urgent_commercial_audit(actor_id,action,target_id,details)values(auth.uid(),'internal_premium_granted',p_id,'Premium interne offert — sans règlement : '||trim(p_reason));
 return p_id;
end;$$;
create function public.urgent_revoke_internal_premium(p_id uuid,p_reason text)returns boolean
language plpgsql security definer set search_path='' as $$
declare p public.urgent_internal_premium_periods;
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_reason is null or length(trim(p_reason))not between 10 and 1000 then raise exception 'Motif de retrait requis (10 à 1000 caractères)';end if;
 select * into p from public.urgent_internal_premium_periods where id=p_id;
 if not found then raise exception 'Période interne introuvable';end if;
 perform 1 from public.urgent_business_access where company_id=p.company_id for update;
 update public.urgent_internal_premium_periods set revoked_at=now(),revoked_by=auth.uid(),revocation_reason=trim(p_reason)where id=p_id and revoked_at is null;
 if found then insert into public.urgent_commercial_audit(actor_id,action,target_id,details)values(auth.uid(),'internal_premium_revoked',p_id,trim(p_reason));end if;
 return true;
end;$$;
create function public.urgent_internal_premium_status(p_company uuid default null)returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare company uuid:=coalesce(p_company,public.urgent_actor_company());periods jsonb;
begin
 if auth.uid()is null or company is null or not(public.urgent_is_admin()or company=public.urgent_actor_company())then raise exception 'Accès réservé à votre entreprise ou à l’administration';end if;
 select coalesce(jsonb_agg(to_jsonb(p)order by p.recorded_at desc,p.id),'[]'::jsonb)into periods from(select * from public.urgent_internal_premium_periods x where x.company_id=company order by x.recorded_at desc,x.id limit 100)p;
 return jsonb_build_object('company_id',company,'active',public.urgent_internal_premium_active(company),'plan','gold','carrier_ready',public.urgent_carrier_ready(company),'periods',periods);
end;$$;
create function public.urgent_internal_premium_directory(p_query text default '',p_offset integer default 0)
returns table(company_id uuid,company_name text,emails text,siret text,establishment_ready boolean,documents_ready boolean,terms_accepted boolean,internal_active boolean)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_query is null or length(p_query)>100 or p_offset is null or p_offset<0 or p_offset>100000 then raise exception 'Recherche invalide';end if;
 return query select c.id,c.name::text,(select string_agg(u.email::text,', ' order by u.email)from public.profiles p join auth.users u on u.id=p.id where p.company_id=c.id),a.siret,
 coalesce(a.registry_checked and a.pilot_enabled,false),public.urgent_carrier_documents_ready(c.id),exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config conf on conf.id and conf.terms_version=t.version where t.company_id=c.id),public.urgent_internal_premium_active(c.id)
 from public.companies c left join public.urgent_business_access a on a.company_id=c.id
 where exists(select 1 from public.profiles p where p.company_id=c.id and p.role::text='carrier')and(position(lower(trim(p_query))in lower(c.name))>0 or exists(select 1 from public.profiles p join auth.users u on u.id=p.id where p.company_id=c.id and position(lower(trim(p_query))in lower(u.email))>0))
 order by c.name,c.id limit 100 offset p_offset;
end;$$;
create or replace function public.urgent_carrier_ready(p_company uuid)returns boolean language sql stable security definer set search_path='' as $$
 select public.urgent_carrier_documents_ready(p_company) and (
 not public.urgent_commercial_enabled() or (
 exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config c on c.terms_version=t.version and c.id where t.company_id=p_company)
 and (public.urgent_internal_premium_active(p_company)or exists(select 1 from public.urgent_manual_subscriptions s where s.company_id=p_company and s.revoked_at is null and s.starts_at<=now() and s.ends_at>now())
 or (exists(select 1 from public.urgent_business_access a where a.company_id=p_company and a.plan='basics') and not exists(select 1 from public.urgent_manual_subscriptions s where s.company_id=p_company)))
 ))
$$;
create or replace function public.urgent_accept_offer_pilot_only(p_offer uuid,p_pilot_ack boolean,p_expected_amount numeric) returns void
language plpgsql security definer set search_path='' as $$
declare offer public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;max_courses integer;used integer;
begin
 if p_pilot_ack is distinct from true then raise exception 'Confirmation du pilote gratuit requise';end if;
 select * into offer from public.urgent_offers where id=p_offer;
 if not found then raise exception 'Offre introuvable';end if;
 select * into s from public.urgent_shipments where id=offer.shipment_id for update;
 if s.owner_company_id is distinct from public.urgent_actor_company() or coalesce(public.urgent_actor_role() not in ('client','carrier','admin'),true) then raise exception 'Seul le donneur d’ordre peut sélectionner';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled) and not (s.is_test and public.urgent_is_admin()) then raise exception 'Accès pilote du donneur d’ordre suspendu';end if;
 if s.status<>'open' or s.pickup<now() then raise exception 'Course non ouverte';end if;
 -- Relire après verrouillage pour éviter une offre retirée ou modifiée entre-temps.
 select * into offer from public.urgent_offers where id=p_offer;
 if offer.status<>'submitted' then raise exception 'Offre non disponible';end if;
 if p_expected_amount is null or offer.amount_ht is distinct from p_expected_amount then raise exception 'Le prix a changé. Actualisez les offres avant de confirmer.';end if;
 select * into access from public.urgent_business_access where company_id=offer.carrier_company_id for update;
 if not public.urgent_carrier_ready(offer.carrier_company_id) and not (s.is_test and public.urgent_test_exception_active(offer.carrier_company_id)) then raise exception 'Dossier transporteur non valide';end if;
 max_courses:=case when public.urgent_internal_premium_active(offer.carrier_company_id)then null else case access.plan when 'basics'then 1 when 'bronze'then 5 when 'silver'then 30 else null end end;
 select count(*) into used from public.urgent_offers o join public.urgent_shipments course on course.id=o.shipment_id where not course.is_test and o.carrier_company_id=offer.carrier_company_id and o.accepted_at>=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris';
 if not s.is_test and max_courses is not null and used>=max_courses then raise exception 'Quota mensuel de courses attribuées atteint';end if;
 update public.urgent_offers set status=case when id=p_offer then 'accepted' else 'not_selected' end,accepted_at=case when id=p_offer then now() else accepted_at end where shipment_id=s.id and status='submitted';
 update public.urgent_shipments set status='assigned',assigned_company_id=offer.carrier_company_id,accepted_offer_id=p_offer,updated_at=now() where id=s.id;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'assigned_pilot_no_charge');
end;
$$;

create or replace function public.urgent_accept_commercial_offer(p_offer uuid,p_expected_amount numeric,p_expected_fee_cents integer,p_terms_version text,p_fee_consent boolean)returns void
language plpgsql security definer set search_path='' as $$
declare o public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;period public.urgent_manual_subscriptions;internal_period public.urgent_internal_premium_periods;effective_plan text;period_start timestamptz;period_end timestamptz;max_courses integer;used integer;fee integer;
begin
 if not public.urgent_commercial_enabled() then raise exception 'Service commercial non ouvert';end if;
 if p_fee_consent is distinct from true or p_terms_version is distinct from (select terms_version from public.urgent_commercial_config where id) then raise exception 'Conditions et frais à confirmer';end if;
 if not exists(select 1 from public.urgent_terms_acceptances where user_id=auth.uid() and company_id=public.urgent_actor_company() and version=p_terms_version) then raise exception 'Conditions à accepter';end if;
 select * into o from public.urgent_offers where id=p_offer;
 select * into s from public.urgent_shipments where id=o.shipment_id for update;
 if not found or s.is_test or s.status<>'open' or s.pickup<now() then raise exception 'Course commerciale non disponible';end if;
 if s.owner_company_id is distinct from public.urgent_actor_company() or coalesce(public.urgent_actor_role() not in ('client','carrier','admin'),true) then raise exception 'Donneur d’ordre requis';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled) then raise exception 'Établissement non autorisé';end if;
 select * into o from public.urgent_offers where id=p_offer;
 fee:=round(o.amount_ht*100*0.015)::integer;
 if o.status<>'submitted' or o.amount_ht is distinct from p_expected_amount or fee is distinct from p_expected_fee_cents then raise exception 'Prix ou frais modifiés : actualiser avant confirmation';end if;
 select * into access from public.urgent_business_access where company_id=o.carrier_company_id for update;
 if not public.urgent_carrier_ready(o.carrier_company_id) then raise exception 'Abonnement/période, conditions ou documents transporteur non valides';end if;
 select * into period from public.urgent_manual_subscriptions where company_id=o.carrier_company_id and revoked_at is null and starts_at<=now() and ends_at>now() order by starts_at desc limit 1;
 select * into internal_period from public.urgent_internal_premium_periods where company_id=o.carrier_company_id and revoked_at is null and starts_at<=now()and ends_at>now()order by starts_at desc,id limit 1;
 if internal_period.id is not null then effective_plan:='gold';period_start:=greatest(internal_period.starts_at,internal_period.recorded_at);period_end:=internal_period.ends_at;
 elsif period.id is not null then effective_plan:=period.plan;period_start:=greatest(period.starts_at,period.recorded_at);period_end:=period.ends_at;
 else effective_plan:='basics';period_start:=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris';period_end:=(date_trunc('month',now() at time zone 'Europe/Paris')+interval '1 month') at time zone 'Europe/Paris';end if;
 max_courses:=case effective_plan when 'basics' then 1 when 'bronze' then 5 when 'silver' then 30 else null end;
 select count(*) into used from public.urgent_offers offer join public.urgent_shipments course on course.id=offer.shipment_id where not course.is_test and offer.carrier_company_id=o.carrier_company_id and offer.accepted_at>=period_start and offer.accepted_at<period_end and exists(select 1 from public.urgent_service_entries e where e.offer_id=offer.id and e.kind='fee' and (e.amount_ht_cents=0 or e.amount_ht_cents+coalesce((select sum(cr.amount_ht_cents) from public.urgent_service_entries cr where cr.parent_id=e.id),0)>0));
 if max_courses is not null and used>=max_courses then raise exception 'Quota de la période atteint';end if;
 update public.urgent_offers set status=case when id=p_offer then 'accepted' else 'not_selected' end,accepted_at=case when id=p_offer then now() else accepted_at end where shipment_id=s.id and status='submitted';
 update public.urgent_shipments set status='assigned',assigned_company_id=o.carrier_company_id,accepted_offer_id=p_offer,updated_at=now() where id=s.id;
 insert into public.urgent_service_entries(request_key,company_id,shipment_id,offer_id,kind,transport_ht,amount_ht_cents,reason,terms_version,created_by)
 values(o.id,s.owner_company_id,s.id,o.id,'fee',o.amount_ht,fee,'Mise en relation confirmée et coordonnées accessibles',p_terms_version,auth.uid());
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'assigned_commercial_manual');
end;
$$;
create function public.urgent_internal_premium_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'version','20261031-internal-premium','admin_only',true,'bank_payment',false);$$;
revoke all on function public.urgent_grant_internal_premium(uuid,uuid,date,date,text,boolean),public.urgent_revoke_internal_premium(uuid,text),public.urgent_internal_premium_status(uuid),public.urgent_internal_premium_directory(text,integer)from public,anon;
grant execute on function public.urgent_grant_internal_premium(uuid,uuid,date,date,text,boolean),public.urgent_revoke_internal_premium(uuid,text),public.urgent_internal_premium_status(uuid),public.urgent_internal_premium_directory(text,integer)to authenticated;
revoke all on function public.urgent_internal_premium_policy()from public;
grant execute on function public.urgent_internal_premium_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_internal_premium_policy()as acces_premium_interne;

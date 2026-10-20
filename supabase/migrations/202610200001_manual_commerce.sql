-- Virements rapprochés manuellement, frais exportés vers la facturation CHRONOSS.
-- Dépend des migrations pilote et correctifs 202610190001 à 003 (pas de Stripe).
-- Installation sans ouverture commerciale : enabled=false.
begin;
create table public.urgent_commercial_config (
 id boolean primary key default true check(id),
 enabled boolean not null default false,
 terms_version text not null default 'PRO-B2B-2026-10-20-v3',
 document_sha256 text not null default '458c1bb0596eec98c3b0c342474added2c127570dbe9cc7b4dbc491130d75648',
 document_url text not null default 'conditions-professionnelles-v3.html'
);
insert into public.urgent_commercial_config(id)values(true);
create table public.urgent_terms_acceptances (
 user_id uuid not null references auth.users(id),
 company_id uuid not null references public.companies(id),
 version text not null,
 document_sha256 text not null,
 accepted_at timestamptz not null default now(),
 primary key(user_id,company_id,version)
);
create table public.urgent_manual_subscriptions (
 id uuid primary key default gen_random_uuid(),
 company_id uuid not null references public.companies(id),
 plan text not null check(plan in ('bronze','silver','gold')),
 starts_at timestamptz not null,
 ends_at timestamptz not null check(ends_at>starts_at),
 expected_ttc_cents integer not null check(expected_ttc_cents>0),
 received_cents integer not null check(received_cents=expected_ttc_cents),
 bank_reference text not null unique check(length(trim(bank_reference)) between 3 and 120),
 invoice_reference text not null unique check(length(trim(invoice_reference)) between 1 and 120),
 recorded_by uuid not null references auth.users(id),
 recorded_at timestamptz not null default now(),
 revoked_at timestamptz,
 revocation_reason text
);
create index on public.urgent_manual_subscriptions(company_id,starts_at,ends_at);
create table public.urgent_service_entries (
 id uuid primary key default gen_random_uuid(),
 request_key uuid not null unique,
 company_id uuid not null references public.companies(id),
 shipment_id uuid not null references public.urgent_shipments(id),
 offer_id uuid not null references public.urgent_offers(id),
 parent_id uuid references public.urgent_service_entries(id),
 kind text not null check(kind in ('fee','credit')),
 transport_ht numeric(12,2) not null,
 amount_ht_cents integer not null,
 reason text not null,
 terms_version text not null,
 created_by uuid not null references auth.users(id),
 occurred_at timestamptz not null default now(),
 external_invoice_reference text,
 invoiced_at timestamptz,
 check((kind='fee' and parent_id is null and amount_ht_cents>=0) or (kind='credit' and parent_id is not null and amount_ht_cents<0))
);
create unique index urgent_one_fee_per_offer on public.urgent_service_entries(offer_id) where kind='fee';
create index on public.urgent_service_entries(company_id,occurred_at);
create table public.urgent_external_invoice_registry (
 reference text primary key,
 company_id uuid not null references public.companies(id)
);
alter table public.urgent_external_invoice_registry enable row level security;
revoke all on public.urgent_external_invoice_registry from public,anon,authenticated;
create table public.urgent_commercial_audit (
 id uuid primary key default gen_random_uuid(),
 actor_id uuid not null references auth.users(id),
 action text not null,
 target_id uuid,
 details text not null,
 created_at timestamptz not null default now()
);
alter table public.urgent_commercial_config enable row level security;
alter table public.urgent_terms_acceptances enable row level security;
alter table public.urgent_manual_subscriptions enable row level security;
alter table public.urgent_service_entries enable row level security;
alter table public.urgent_commercial_audit enable row level security;
revoke all on public.urgent_commercial_config,public.urgent_terms_acceptances,public.urgent_manual_subscriptions,public.urgent_service_entries,public.urgent_commercial_audit from anon,authenticated;
grant select on public.urgent_manual_subscriptions,public.urgent_service_entries to authenticated;
create policy urgent_manual_subscriptions_read on public.urgent_manual_subscriptions for select to authenticated using(company_id=public.urgent_actor_company() or public.urgent_is_admin());
create policy urgent_service_entries_read on public.urgent_service_entries for select to authenticated using(company_id=public.urgent_actor_company() or public.urgent_is_admin());

create function public.urgent_commercial_enabled()returns boolean language sql stable security definer set search_path='' as $$
 select coalesce((select enabled from public.urgent_commercial_config where id),false)
$$;
create function public.urgent_commercial_status()returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('enabled',c.enabled,'terms_version',c.terms_version,'document_sha256',c.document_sha256,'document_url',c.document_url,'terms_accepted',exists(select 1 from public.urgent_terms_acceptances a where a.user_id=auth.uid() and a.company_id=public.urgent_actor_company() and a.version=c.terms_version)) from public.urgent_commercial_config c where id
$$;
create function public.urgent_accept_terms(p_version text)returns void language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or public.urgent_actor_company() is null then raise exception 'Compte professionnel requis';end if;
 if p_version is distinct from (select terms_version from public.urgent_commercial_config where id) then raise exception 'Version des conditions non actuelle';end if;
 insert into public.urgent_terms_acceptances(user_id,company_id,version,document_sha256)select auth.uid(),public.urgent_actor_company(),p_version,document_sha256 from public.urgent_commercial_config where id on conflict do nothing;
end;
$$;
create function public.urgent_set_commercial_mode(p_enabled boolean,p_confirmation text)returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_enabled is null or p_confirmation is distinct from 'CHRONOSS - VIREMENTS ET FACTURATION MANUELLE' then raise exception 'Confirmation du mode de facturation requise';end if;
 update public.urgent_commercial_config set enabled=p_enabled where id;
 insert into public.urgent_commercial_audit(actor_id,action,details)values(auth.uid(),'mode_changed',p_enabled::text);
end;
$$;

-- La fonction historique reste le contrôle documentaire ; aucun accès direct à son alias.
create function public.urgent_carrier_documents_ready(p_company uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_business_access a where a.company_id=p_company and a.registry_checked and a.pilot_enabled)
 and not exists(
  select 1 from (values('registration'),('transport_licence'),('insurance_rc'),('insurance_goods')) required(kind)
  where not coalesce((select d.review_status='approved'
   and (required.kind='registration' or d.expires_on is not null)
   and (d.expires_on is null or d.expires_on>=(now() at time zone 'Europe/Paris')::date)
   from public.carrier_documents d where d.company_id=p_company and d.document_type=required.kind
   order by d.created_at desc,d.id desc limit 1),false)
 )
$$;
revoke all on function public.urgent_carrier_documents_ready(uuid) from public,anon,authenticated;
create or replace function public.urgent_carrier_ready(p_company uuid)returns boolean language sql stable security definer set search_path='' as $$
 select public.urgent_carrier_documents_ready(p_company) and (
 not public.urgent_commercial_enabled() or (
 exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config c on c.terms_version=t.version and c.id where t.company_id=p_company)
 and (exists(select 1 from public.urgent_manual_subscriptions s where s.company_id=p_company and s.revoked_at is null and s.starts_at<=now() and s.ends_at>now())
 or (exists(select 1 from public.urgent_business_access a where a.company_id=p_company and a.plan='basics') and not exists(select 1 from public.urgent_manual_subscriptions s where s.company_id=p_company)))
 ))
$$;
create function public.urgent_record_bank_subscription(p_company uuid,p_plan text,p_start date,p_expected_ttc_cents integer,p_received_cents integer,p_bank_reference text,p_invoice_reference text,p_bank_checked boolean)returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;minimum_ht integer;end_at timestamptz;start_at timestamptz;previous public.urgent_manual_subscriptions;
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_bank_checked is distinct from true then raise exception 'Vérifier le crédit effectif sur le compte bancaire CHRONOSS';end if;
 minimum_ht:=case p_plan when 'bronze' then 1250 when 'silver' then 3333 when 'gold' then 6250 else null end;
 if minimum_ht is null or p_expected_ttc_cents is null or p_expected_ttc_cents<minimum_ht or p_received_cents is distinct from p_expected_ttc_cents then raise exception 'Forfait ou montant rapproché incorrect. Utiliser le TTC de la facture CHRONOSS.';end if;
 perform 1 from public.urgent_business_access where company_id=p_company and registry_checked and pilot_enabled for update;
 if not found or not exists(select 1 from public.profiles where company_id=p_company and role::text='carrier') then raise exception 'Transporteur professionnel à autoriser avant activation';end if;
 select * into previous from public.urgent_manual_subscriptions where bank_reference=trim(p_bank_reference);
 if found then
  if previous.company_id=p_company and previous.plan=p_plan and previous.invoice_reference=trim(p_invoice_reference) and previous.received_cents=p_received_cents and (previous.starts_at at time zone 'Europe/Paris')::date=p_start and previous.revoked_at is null then return previous.id;end if;
  raise exception 'Référence bancaire déjà utilisée';
 end if;
 if p_start is null or p_start<(now() at time zone 'Europe/Paris')::date or p_start>(now() at time zone 'Europe/Paris')::date+366 then raise exception 'Début requis aujourd’hui ou dans les 12 prochains mois ; pas de perte rétroactive de période';end if;
 if exists(select 1 from public.urgent_document_checklist(p_company) where reason<>'valid') then raise exception 'Documents approuvés et valides requis';end if;
 if not exists(select 1 from public.urgent_terms_acceptances a join public.urgent_commercial_config c on c.id and c.terms_version=a.version where a.company_id=p_company) then raise exception 'Conditions à accepter par le transporteur';end if;
 start_at:=p_start::timestamp at time zone 'Europe/Paris';end_at:=(p_start+interval '1 month') at time zone 'Europe/Paris';
 if exists(select 1 from public.urgent_manual_subscriptions where company_id=p_company and revoked_at is null and starts_at<end_at and ends_at>start_at) then raise exception 'Une période existe déjà sur ces dates';end if;
 insert into public.urgent_manual_subscriptions(company_id,plan,starts_at,ends_at,expected_ttc_cents,received_cents,bank_reference,invoice_reference,recorded_by)
 values(p_company,p_plan,start_at,end_at,p_expected_ttc_cents,p_received_cents,trim(p_bank_reference),trim(p_invoice_reference),auth.uid())returning id into result;
 insert into public.urgent_commercial_audit(actor_id,action,target_id,details)values(auth.uid(),'bank_period_recorded',result,'Crédit bancaire rapproché ; facture externe enregistrée');
 return result;
end;
$$;
create function public.urgent_revoke_bank_subscription(p_subscription uuid,p_reason text)returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_reason is null or length(trim(p_reason)) not between 10 and 1000 then raise exception 'Motif de 10 à 1000 caractères requis';end if;
 update public.urgent_manual_subscriptions set revoked_at=now(),revocation_reason=trim(p_reason) where id=p_subscription and revoked_at is null;
 if not found then raise exception 'Période absente ou déjà révoquée';end if;
 insert into public.urgent_commercial_audit(actor_id,action,target_id,details)values(auth.uid(),'bank_period_revoked',p_subscription,trim(p_reason));
end;
$$;

-- Aucun ancien écran de pilote ne peut créer de frais sans la confirmation commerciale.
create function public.urgent_accept_offer_pilot_only(p_offer uuid,p_pilot_ack boolean,p_expected_amount numeric) returns void
language plpgsql security definer set search_path='' as $$
declare offer public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;max_courses integer;used integer;
begin
 if p_pilot_ack is distinct from true then raise exception 'Confirmation du pilote gratuit requise';end if;
 select * into offer from public.urgent_offers where id=p_offer;
 if not found then raise exception 'Offre introuvable';end if;
 select * into s from public.urgent_shipments where id=offer.shipment_id for update;
 if s.owner_company_id is distinct from public.urgent_actor_company() or public.urgent_actor_role() not in ('client','admin') then raise exception 'Seul le donneur d’ordre peut sélectionner';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled) and not (s.is_test and public.urgent_is_admin()) then raise exception 'Accès pilote du donneur d’ordre suspendu';end if;
 if s.status<>'open' or s.pickup<now() then raise exception 'Course non ouverte';end if;
 -- Relire après verrouillage pour éviter une offre retirée ou modifiée entre-temps.
 select * into offer from public.urgent_offers where id=p_offer;
 if offer.status<>'submitted' then raise exception 'Offre non disponible';end if;
 if p_expected_amount is null or offer.amount_ht is distinct from p_expected_amount then raise exception 'Le prix a changé. Actualisez les offres avant de confirmer.';end if;
 select * into access from public.urgent_business_access where company_id=offer.carrier_company_id for update;
 if not public.urgent_carrier_ready(offer.carrier_company_id) and not (s.is_test and public.urgent_test_exception_active(offer.carrier_company_id)) then raise exception 'Dossier transporteur non valide';end if;
 max_courses:=case access.plan when 'basics' then 1 when 'bronze' then 5 when 'silver' then 30 else null end;
 select count(*) into used from public.urgent_offers o join public.urgent_shipments course on course.id=o.shipment_id where not course.is_test and o.carrier_company_id=offer.carrier_company_id and o.accepted_at>=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris';
 if not s.is_test and max_courses is not null and used>=max_courses then raise exception 'Quota mensuel de courses attribuées atteint';end if;
 update public.urgent_offers set status=case when id=p_offer then 'accepted' else 'not_selected' end,accepted_at=case when id=p_offer then now() else accepted_at end where shipment_id=s.id and status='submitted';
 update public.urgent_shipments set status='assigned',assigned_company_id=offer.carrier_company_id,accepted_offer_id=p_offer,updated_at=now() where id=s.id;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'assigned_pilot_no_charge');
end;
$$;
revoke all on function public.urgent_accept_offer_pilot_only(uuid,boolean,numeric) from public,anon,authenticated;
create or replace function public.urgent_accept_offer(p_offer uuid,p_pilot_ack boolean,p_expected_amount numeric)returns void language plpgsql security definer set search_path='' as $$
begin
 if public.urgent_commercial_enabled() and not coalesce((select s.is_test from public.urgent_shipments s join public.urgent_offers o on o.shipment_id=s.id where o.id=p_offer),false) then raise exception 'Utiliser la confirmation des frais de mise en relation';end if;
 perform public.urgent_accept_offer_pilot_only(p_offer,p_pilot_ack,p_expected_amount);
end;
$$;
create function public.urgent_accept_commercial_offer(p_offer uuid,p_expected_amount numeric,p_expected_fee_cents integer,p_terms_version text,p_fee_consent boolean)returns void
language plpgsql security definer set search_path='' as $$
declare o public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;period public.urgent_manual_subscriptions;effective_plan text;period_start timestamptz;period_end timestamptz;max_courses integer;used integer;fee integer;
begin
 if not public.urgent_commercial_enabled() then raise exception 'Service commercial non ouvert';end if;
 if p_fee_consent is distinct from true or p_terms_version is distinct from (select terms_version from public.urgent_commercial_config where id) then raise exception 'Conditions et frais à confirmer';end if;
 if not exists(select 1 from public.urgent_terms_acceptances where user_id=auth.uid() and company_id=public.urgent_actor_company() and version=p_terms_version) then raise exception 'Conditions à accepter';end if;
 select * into o from public.urgent_offers where id=p_offer;
 select * into s from public.urgent_shipments where id=o.shipment_id for update;
 if not found or s.is_test or s.status<>'open' or s.pickup<now() then raise exception 'Course commerciale non disponible';end if;
 if s.owner_company_id is distinct from public.urgent_actor_company() or public.urgent_actor_role() not in ('client','admin') then raise exception 'Donneur d’ordre requis';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled) then raise exception 'Établissement non autorisé';end if;
 select * into o from public.urgent_offers where id=p_offer;
 fee:=round(o.amount_ht*100*0.015)::integer;
 if o.status<>'submitted' or o.amount_ht is distinct from p_expected_amount or fee is distinct from p_expected_fee_cents then raise exception 'Prix ou frais modifiés : actualiser avant confirmation';end if;
 select * into access from public.urgent_business_access where company_id=o.carrier_company_id for update;
 if not public.urgent_carrier_ready(o.carrier_company_id) then raise exception 'Abonnement/période, conditions ou documents transporteur non valides';end if;
 select * into period from public.urgent_manual_subscriptions where company_id=o.carrier_company_id and revoked_at is null and starts_at<=now() and ends_at>now() order by starts_at desc limit 1;
 if found then effective_plan:=period.plan;period_start:=greatest(period.starts_at,period.recorded_at);period_end:=period.ends_at;
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
create function public.urgent_credit_service_fee(p_entry uuid,p_cents integer,p_reason text,p_request uuid)returns uuid language plpgsql security definer set search_path='' as $$
declare base public.urgent_service_entries;previous public.urgent_service_entries;credited bigint;result uuid;
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_cents is null or p_cents<=0 or p_reason is null or length(trim(p_reason)) not between 10 and 1000 or p_request is null then raise exception 'Montant positif et motif détaillé requis';end if;
 select * into base from public.urgent_service_entries where id=p_entry and kind='fee' for update;
 if not found then raise exception 'Frais d’origine introuvables';end if;
 select * into previous from public.urgent_service_entries where request_key=p_request;
 if found then
  if previous.kind='credit' and previous.parent_id=p_entry and previous.amount_ht_cents=-p_cents and previous.reason=trim(p_reason) then return previous.id;end if;
  raise exception 'Identifiant de correction déjà utilisé';
 end if;
 select coalesce(-sum(amount_ht_cents),0) into credited from public.urgent_service_entries where parent_id=p_entry;
 if credited+p_cents>base.amount_ht_cents then raise exception 'Correction supérieure aux frais restants';end if;
 insert into public.urgent_service_entries(request_key,company_id,shipment_id,offer_id,parent_id,kind,transport_ht,amount_ht_cents,reason,terms_version,created_by)
 values(p_request,base.company_id,base.shipment_id,base.offer_id,p_entry,'credit',base.transport_ht,-p_cents,trim(p_reason),base.terms_version,auth.uid())returning id into result;
 return result;
end;
$$;
create function public.urgent_monthly_service_report(p_month date)returns table(entry_id uuid,company_id uuid,company_name text,siret text,shipment_id uuid,offer_id uuid,kind text,transport_ht numeric,amount_ht_cents integer,occurred_at timestamptz,reason text,invoice_reference text,parent_entry_id uuid,original_invoice_reference text)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_month is null or extract(day from p_month)<>1 then raise exception 'Premier jour du mois requis';end if;
 return query select e.id,e.company_id,c.name::text,a.siret,e.shipment_id,e.offer_id,e.kind,e.transport_ht,e.amount_ht_cents,e.occurred_at,e.reason,e.external_invoice_reference,e.parent_id,(select original.external_invoice_reference from public.urgent_service_entries original where original.id=e.parent_id) from public.urgent_service_entries e join public.companies c on c.id=e.company_id left join public.urgent_business_access a on a.company_id=c.id
 where e.occurred_at>=p_month::timestamp at time zone 'Europe/Paris' and e.occurred_at<(p_month+interval '1 month') at time zone 'Europe/Paris' order by e.company_id,e.occurred_at,e.id;
end;
$$;
create function public.urgent_mark_external_invoice(p_entries uuid[],p_reference text)returns void language plpgsql security definer set search_path='' as $$
declare qty integer;companies integer;prior integer;
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_reference is null or length(trim(p_reference)) not between 1 and 120 or coalesce(cardinality(p_entries),0)=0 then raise exception 'Lignes et référence de facture/avoir CHRONOSS requises';end if;
 perform 1 from public.urgent_service_entries where id=any(p_entries) order by id for update;
 select count(*),count(distinct company_id),count(*) filter(where external_invoice_reference is not null and external_invoice_reference<>trim(p_reference)) into qty,companies,prior from public.urgent_service_entries where id=any(p_entries);
 if qty<>cardinality(p_entries) or companies<>1 or prior<>0 then raise exception 'Lignes manquantes, plusieurs clients ou lignes déjà facturées ailleurs';end if;
 insert into public.urgent_external_invoice_registry(reference,company_id)select trim(p_reference),company_id from public.urgent_service_entries where id=p_entries[1] on conflict do nothing;
 if not exists(select 1 from public.urgent_external_invoice_registry where reference=trim(p_reference) and company_id=(select company_id from public.urgent_service_entries where id=p_entries[1])) then raise exception 'Référence déjà utilisée pour un autre client';end if;
 update public.urgent_service_entries set external_invoice_reference=trim(p_reference),invoiced_at=coalesce(invoiced_at,now()) where id=any(p_entries);
 insert into public.urgent_commercial_audit(actor_id,action,details)values(auth.uid(),'external_invoice_recorded',trim(p_reference));
end;
$$;

create function public.urgent_own_monthly_total(p_month date)returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if auth.uid() is null or public.urgent_actor_company() is null or p_month is null or extract(day from p_month)<>1 then raise exception 'Compte et premier jour du mois requis';end if;
 return (select jsonb_build_object('month',p_month,'amount_ht_cents',coalesce(sum(e.amount_ht_cents),0),'unbilled_ht_cents',coalesce(sum(e.amount_ht_cents)filter(where e.external_invoice_reference is null),0),'entries_count',count(*)) from public.urgent_service_entries e where e.company_id=public.urgent_actor_company() and e.occurred_at>=p_month::timestamp at time zone 'Europe/Paris' and e.occurred_at<(p_month+interval '1 month') at time zone 'Europe/Paris');
end;
$$;
revoke all on function public.urgent_own_monthly_total(date) from public,anon;
grant execute on function public.urgent_own_monthly_total(date) to authenticated;

-- La fiche ne transforme jamais une attribution pilote antérieure en prestation payante.
create or replace function public.urgent_assignment_details(p_shipment uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.urgent_shipments;o public.urgent_offers;fee integer;result jsonb;
begin
 if not public.urgent_is_party(p_shipment) then raise exception 'Accès aux parties uniquement';end if;
 select * into s from public.urgent_shipments where id=p_shipment;
 if s.accepted_offer_id is null then raise exception 'Course non attribuée';end if;
 select * into o from public.urgent_offers where id=s.accepted_offer_id;
 select amount_ht_cents into fee from public.urgent_service_entries where offer_id=o.id and kind='fee';
 select jsonb_build_object('shipment_id',s.id,'carrier_company',c.name,'carrier_email',u.email,'amount_ht',o.amount_ht,'fee_preview_ht',round(o.amount_ht*0.015,2),'fee_due_ht',coalesce(fee,0)/100.0,'charged_ht',0,'mode',case when s.is_test then 'fictitious_exercise' when fee is not null then 'commercial_manual' else 'pilot_free' end,'is_test',s.is_test,'assigned_at',o.accepted_at)into result from public.companies c join auth.users u on u.id=o.carrier_id where c.id=o.carrier_company_id;
 return result;
end;
$$;
-- Expliciter chaque droit : les fonctions SECURITY DEFINER ne sont pas publiques.
revoke all on function public.urgent_commercial_enabled(),public.urgent_commercial_status(),public.urgent_accept_terms(text),public.urgent_set_commercial_mode(boolean,text),public.urgent_carrier_ready(uuid),public.urgent_record_bank_subscription(uuid,text,date,integer,integer,text,text,boolean),public.urgent_revoke_bank_subscription(uuid,text),public.urgent_accept_offer(uuid,boolean,numeric),public.urgent_accept_commercial_offer(uuid,numeric,integer,text,boolean),public.urgent_credit_service_fee(uuid,integer,text,uuid),public.urgent_monthly_service_report(date),public.urgent_mark_external_invoice(uuid[],text) from public,anon;
grant execute on function public.urgent_commercial_enabled(),public.urgent_commercial_status(),public.urgent_accept_terms(text),public.urgent_set_commercial_mode(boolean,text),public.urgent_carrier_ready(uuid),public.urgent_record_bank_subscription(uuid,text,date,integer,integer,text,text,boolean),public.urgent_revoke_bank_subscription(uuid,text),public.urgent_accept_offer(uuid,boolean,numeric),public.urgent_accept_commercial_offer(uuid,numeric,integer,text,boolean),public.urgent_credit_service_fee(uuid,integer,text,uuid),public.urgent_monthly_service_report(date),public.urgent_mark_external_invoice(uuid[],text) to authenticated;
grant execute on function public.urgent_commercial_status() to anon;
commit;

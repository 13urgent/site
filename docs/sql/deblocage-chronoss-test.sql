-- Exception temporaire pour exercices fictifs uniquement, sans valider les pièces.
begin;
alter table public.urgent_business_access add column if not exists test_exception_until timestamptz;
alter table public.urgent_shipments add column if not exists is_test boolean not null default false;
create or replace function public.urgent_test_exception_active(p_company uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_business_access where company_id=p_company and registry_checked and pilot_enabled and test_exception_until>now())
$$;
create or replace function public.urgent_publish_test_shipment(p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text) returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;company uuid:=public.urgent_actor_company();
begin
 if not public.urgent_is_admin() then raise exception 'Création des exercices réservée à l’administration';end if;
 if company is null or p_pickup<now() then raise exception 'Entreprise administrateur et date future requises';end if;
 insert into public.urgent_shipments(owner_id,owner_company_id,origin,destination,pickup,vehicle,pallets,weight,is_test)
 values(auth.uid(),company,trim(p_origin),trim(p_destination),p_pickup,p_vehicle,p_pallets,p_weight,true) returning id into result;
 insert into public.urgent_shipment_private values(result,trim(p_company_name),trim(p_email),coalesce(p_instructions,''));
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(result,auth.uid(),'test_exercise_created');
 return result;
end;
$$;
create or replace function public.urgent_submit_offer(p_shipment uuid,p_amount numeric) returns uuid
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;company uuid:=public.urgent_actor_company();result uuid;
begin
 if auth.uid() is null or public.urgent_actor_role()<>'carrier' then raise exception 'Compte transporteur requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.status<>'open' or s.pickup<now() then raise exception 'Course non disponible';end if;
 if s.owner_company_id=company then raise exception 'Offre sur sa propre entreprise interdite';end if;
 if not public.urgent_carrier_ready(company) and not (s.is_test and public.urgent_test_exception_active(company)) then raise exception 'Accès pilote et documents valides requis';end if;
 insert into public.urgent_offers(shipment_id,carrier_id,carrier_company_id,amount_ht)
 values(p_shipment,auth.uid(),company,p_amount)
 on conflict(shipment_id,carrier_company_id) do update set amount_ht=excluded.amount_ht,status='submitted'
 returning id into result;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'offer_submitted');
 return result;
end;
$$;
create or replace function public.urgent_accept_offer(p_offer uuid,p_pilot_ack boolean,p_expected_amount numeric) returns void
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
create or replace function public.urgent_assignment_details(p_shipment uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.urgent_shipments;offer public.urgent_offers;result jsonb;
begin
 if not public.urgent_is_party(p_shipment) then raise exception 'Accès aux parties uniquement';end if;
 select * into s from public.urgent_shipments where id=p_shipment;
 if s.accepted_offer_id is null then raise exception 'Course non attribuée';end if;
 select * into offer from public.urgent_offers where id=s.accepted_offer_id;
 select jsonb_build_object('shipment_id',s.id,'carrier_company',c.name,'carrier_email',u.email,'amount_ht',offer.amount_ht,'fee_preview_ht',round(offer.amount_ht*0.015,2),'charged_ht',0,'mode',case when s.is_test then 'fictitious_exercise' else 'pilot_free' end,'is_test',s.is_test,'assigned_at',offer.accepted_at)
 into result from public.companies c join auth.users u on u.id=offer.carrier_id where c.id=offer.carrier_company_id;
 return result;
end;
$$;
revoke all on function public.urgent_test_exception_active(uuid),public.urgent_publish_test_shipment(text,text,timestamptz,text,integer,numeric,text,text,text) from public,anon;
grant execute on function public.urgent_test_exception_active(uuid),public.urgent_publish_test_shipment(text,text,timestamptz,text,integer,numeric,text,text,text) to authenticated;

-- Autorisation ciblée demandée par le propriétaire, limitée à 48 heures.
do $$
begin
 update public.urgent_business_access set test_exception_until=now()+interval '48 hours'
 where company_id='f414dd52-352d-43ba-9995-354bb7d01aa3'
 and siret='91871039300052' and pilot_enabled and registry_checked;
 if not found then raise exception 'CHRONOSS : autorisation pilote et SIRET attendus introuvables. Aucun déblocage effectué.';end if;
end;
$$;
commit;
select company_id,test_exception_until at time zone 'Europe/Paris' as fin_exception_heure_paris,
 'EXERCICES FICTIFS UNIQUEMENT — DOCUMENTS NON VALIDÉS' as portee
from public.urgent_business_access where company_id='f414dd52-352d-43ba-9995-354bb7d01aa3';

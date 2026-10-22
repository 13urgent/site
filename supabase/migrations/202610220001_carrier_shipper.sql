-- Un transporteur peut agir comme donneur d’ordre pour ses propres demandes.
-- Prérequis : migration 202610200001_manual_commerce.sql.
-- Aucun changement de rôle, de tarif, de paiement, de contrôle documentaire ou de confidentialité.
begin;
create or replace function public.urgent_publish_shipment(p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text) returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;company uuid:=public.urgent_actor_company();
begin
 if coalesce(public.urgent_actor_role() not in ('client','carrier','admin'),true) or auth.uid() is null then raise exception 'Compte professionnel requis';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=company and registry_checked and pilot_enabled) then raise exception 'Établissement à faire vérifier par 13 URGENT';end if;
 if p_pickup<now() then raise exception 'Date d’enlèvement passée';end if;
 insert into public.urgent_shipments(owner_id,owner_company_id,origin,destination,pickup,vehicle,pallets,weight)
 values(auth.uid(),company,trim(p_origin),trim(p_destination),p_pickup,p_vehicle,p_pallets,p_weight) returning id into result;
 insert into public.urgent_shipment_private values(result,trim(p_company_name),trim(p_email),coalesce(p_instructions,''));
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(result,auth.uid(),'published');
 return result;
end;
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
 max_courses:=case access.plan when 'basics' then 1 when 'bronze' then 5 when 'silver' then 30 else null end;
 select count(*) into used from public.urgent_offers o join public.urgent_shipments course on course.id=o.shipment_id where not course.is_test and o.carrier_company_id=offer.carrier_company_id and o.accepted_at>=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris';
 if not s.is_test and max_courses is not null and used>=max_courses then raise exception 'Quota mensuel de courses attribuées atteint';end if;
 update public.urgent_offers set status=case when id=p_offer then 'accepted' else 'not_selected' end,accepted_at=case when id=p_offer then now() else accepted_at end where shipment_id=s.id and status='submitted';
 update public.urgent_shipments set status='assigned',assigned_company_id=offer.carrier_company_id,accepted_offer_id=p_offer,updated_at=now() where id=s.id;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'assigned_pilot_no_charge');
end;
$$;

create or replace function public.urgent_accept_commercial_offer(p_offer uuid,p_expected_amount numeric,p_expected_fee_cents integer,p_terms_version text,p_fee_consent boolean)returns void
language plpgsql security definer set search_path='' as $$
declare o public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;period public.urgent_manual_subscriptions;effective_plan text;period_start timestamptz;period_end timestamptz;max_courses integer;used integer;fee integer;
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
commit;

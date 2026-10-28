-- Modification par l'entreprise propriétaire, avant attribution uniquement.
-- Les anciennes offres restent archivées mais ne valent pas pour une course modifiée.
begin;
alter table public.urgent_shipments add column if not exists revision integer not null default 0 check(revision>=0);

create or replace function public.urgent_shipment_edit_policy()returns jsonb
language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'revision',true);$$;
grant execute on function public.urgent_shipment_edit_policy()to anon,authenticated;

create or replace function public.urgent_update_shipment(p_shipment uuid,p_expected_revision integer,p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text,p_acknowledge_offers boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;private_data public.urgent_shipment_private;offers_count integer;withdrawn integer;
begin
 if auth.uid() is null or coalesce(public.urgent_actor_role() not in('client','carrier','admin'),true) then raise exception 'Compte professionnel requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company() then raise exception 'Seule l’entreprise propriétaire peut modifier cette course';end if;
 if s.status<>'open' or s.accepted_offer_id is not null or s.assigned_company_id is not null then raise exception 'La course ne peut plus être modifiée après attribution ou clôture';end if;
 if p_expected_revision is distinct from s.revision then raise exception 'La course a changé depuis son ouverture. Actualisez avant de modifier';end if;
 if not(s.is_test and public.urgent_is_admin()) and not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled)then raise exception 'Autorisation de l’établissement requise';end if;
 if p_pickup is null or p_pickup<now() then raise exception 'Choisissez une date d’enlèvement future';end if;
 if p_email is null or p_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$' then raise exception 'Adresse e-mail invalide';end if;
 if p_origin is null or p_destination is null or p_vehicle is null or p_pallets is null or p_weight is null or p_company_name is null then raise exception 'Complétez les informations obligatoires';end if;
 select * into private_data from public.urgent_shipment_private where shipment_id=s.id;
 if row(s.origin,s.destination,s.pickup,s.vehicle,s.pallets,s.weight,private_data.company_name,private_data.contact_email,private_data.instructions)
 is not distinct from row(trim(p_origin),trim(p_destination),p_pickup,p_vehicle,p_pallets,p_weight,trim(p_company_name),trim(p_email),coalesce(p_instructions,''))then return jsonb_build_object('revision',s.revision,'withdrawn_offers',0,'changed',false);end if;
 select count(*)into offers_count from public.urgent_offers where shipment_id=s.id and status='submitted';
 if offers_count>0 and p_acknowledge_offers is distinct from true then raise exception 'Des offres ont déjà été reçues. Confirmez leur retrait avant de modifier';end if;
 update public.urgent_shipments set origin=trim(p_origin),destination=trim(p_destination),pickup=p_pickup,vehicle=p_vehicle,pallets=p_pallets,weight=p_weight,revision=revision+1,updated_at=now()where id=s.id;
 insert into public.urgent_shipment_private(shipment_id,company_name,contact_email,instructions)values(s.id,trim(p_company_name),trim(p_email),coalesce(p_instructions,''))on conflict(shipment_id)do update set company_name=excluded.company_name,contact_email=excluded.contact_email,instructions=excluded.instructions;
 update public.urgent_offers set status='withdrawn'where shipment_id=s.id and status='submitted';get diagnostics withdrawn=row_count;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'shipment_updated');
 return jsonb_build_object('revision',s.revision+1,'withdrawn_offers',withdrawn,'changed',true);
end;$$;
revoke all on function public.urgent_update_shipment(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,boolean)from public,anon;
grant execute on function public.urgent_update_shipment(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,boolean)to authenticated;

-- Les anciens clients restent compatibles sur une course jamais modifiée.
-- Une offre sur une course révisée doit porter la révision effectivement consultée.
drop function if exists public.urgent_submit_offer(uuid,numeric);
create or replace function public.urgent_submit_offer(p_shipment uuid,p_amount numeric,p_expected_revision integer default null)returns uuid
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;company uuid:=public.urgent_actor_company();result uuid;
begin
 if auth.uid() is null or public.urgent_actor_role() is distinct from 'carrier'then raise exception 'Compte transporteur requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.status<>'open' or s.pickup<now() then raise exception 'Course non disponible';end if;
 if coalesce(p_expected_revision,0)<>s.revision then raise exception 'La course a été modifiée. Actualisez ses informations avant de proposer';end if;
 if s.owner_company_id=company then raise exception 'Offre sur sa propre entreprise interdite';end if;
 if not public.urgent_carrier_ready(company)and not(s.is_test and public.urgent_test_exception_active(company))then raise exception 'Accès pilote et documents valides requis';end if;
 if p_amount is null or p_amount<0.01 or p_amount>1000000 or p_amount<>round(p_amount,2)then raise exception 'Tarif invalide : deux décimales maximum';end if;
 insert into public.urgent_offers(shipment_id,carrier_id,carrier_company_id,amount_ht)values(p_shipment,auth.uid(),company,p_amount)
 on conflict(shipment_id,carrier_company_id)do update set amount_ht=excluded.amount_ht,status='submitted'returning id into result;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'offer_submitted');
 return result;
end;$$;
revoke all on function public.urgent_submit_offer(uuid,numeric,integer)from public,anon;
grant execute on function public.urgent_submit_offer(uuid,numeric,integer)to authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_shipment_edit_policy()as modification_des_courses;

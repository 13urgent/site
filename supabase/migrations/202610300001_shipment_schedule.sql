-- Horaires prévus, distincts des déclarations réelles de chargement/livraison.
-- Aucune heure d’arrivée n’est inventée pour les anciennes courses.
begin;
alter table public.urgent_shipments add column if not exists delivery_at timestamptz;
do $$begin
 if not exists(select 1 from pg_constraint where conname='urgent_delivery_after_pickup' and conrelid='public.urgent_shipments'::regclass)then
  alter table public.urgent_shipments add constraint urgent_delivery_after_pickup check(delivery_at is null or delivery_at>pickup);
 end if;
end;$$;

create or replace function public.urgent_shipment_schedule_policy()returns jsonb
language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'version','20261030-shipment-schedule','timezone','Europe/Paris');$$;
revoke all on function public.urgent_shipment_schedule_policy()from public;
grant execute on function public.urgent_shipment_schedule_policy()to anon,authenticated;

create or replace function public.urgent_publish_scheduled_shipment(p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text,p_delivery_at timestamptz,p_is_test boolean default false)returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if p_pickup is null or p_delivery_at is null or p_delivery_at<=p_pickup then raise exception 'Renseignez un départ et une arrivée prévue postérieure au départ';end if;
 if p_is_test is null then raise exception 'Type de course requis';end if;
 if p_is_test then
  result:=public.urgent_publish_test_shipment(p_origin,p_destination,p_pickup,p_vehicle,p_pallets,p_weight,p_company_name,p_email,p_instructions);
 else
  result:=public.urgent_publish_shipment(p_origin,p_destination,p_pickup,p_vehicle,p_pallets,p_weight,p_company_name,p_email,p_instructions);
 end if;
 update public.urgent_shipments set delivery_at=p_delivery_at where id=result;
 return result;
end;$$;
revoke all on function public.urgent_publish_scheduled_shipment(text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,boolean)from public,anon;
grant execute on function public.urgent_publish_scheduled_shipment(text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,boolean)to authenticated;

create or replace function public.urgent_update_scheduled_shipment(p_shipment uuid,p_expected_revision integer,p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text,p_delivery_at timestamptz,p_acknowledge_offers boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;private_data public.urgent_shipment_private;offers_count integer;withdrawn integer;
begin
 if auth.uid() is null or coalesce(public.urgent_actor_role() not in('client','carrier','admin'),true) then raise exception 'Compte professionnel requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company() then raise exception 'Seule l’entreprise propriétaire peut modifier cette course';end if;
 if s.status<>'open' or s.accepted_offer_id is not null or s.assigned_company_id is not null then raise exception 'La course ne peut plus être modifiée après attribution ou clôture';end if;
 if p_expected_revision is distinct from s.revision then raise exception 'La course a changé depuis son ouverture. Actualisez avant de modifier';end if;
 if not(s.is_test and public.urgent_is_admin()) and not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled)then raise exception 'Autorisation de l’établissement requise';end if;
 if p_delivery_at is null or p_delivery_at<=p_pickup then raise exception 'L’arrivée prévue doit être postérieure au départ';end if;
 if p_pickup is null or p_pickup<now() then raise exception 'Choisissez une date d’enlèvement future';end if;
 if p_email is null or p_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$' then raise exception 'Adresse e-mail invalide';end if;
 if p_origin is null or p_destination is null or p_vehicle is null or p_pallets is null or p_weight is null or p_company_name is null then raise exception 'Complétez les informations obligatoires';end if;
 select * into private_data from public.urgent_shipment_private where shipment_id=s.id;
 if row(s.origin,s.destination,s.pickup,s.delivery_at,s.vehicle,s.pallets,s.weight,private_data.company_name,private_data.contact_email,private_data.instructions)
 is not distinct from row(trim(p_origin),trim(p_destination),p_pickup,p_delivery_at,p_vehicle,p_pallets,p_weight,trim(p_company_name),trim(p_email),coalesce(p_instructions,''))then return jsonb_build_object('revision',s.revision,'withdrawn_offers',0,'changed',false);end if;
 select count(*)into offers_count from public.urgent_offers where shipment_id=s.id and status='submitted';
 if offers_count>0 and p_acknowledge_offers is distinct from true then raise exception 'Des offres ont déjà été reçues. Confirmez leur retrait avant de modifier';end if;
 update public.urgent_shipments set origin=trim(p_origin),destination=trim(p_destination),pickup=p_pickup,delivery_at=p_delivery_at,vehicle=p_vehicle,pallets=p_pallets,weight=p_weight,revision=revision+1,updated_at=now()where id=s.id;
 insert into public.urgent_shipment_private(shipment_id,company_name,contact_email,instructions)values(s.id,trim(p_company_name),trim(p_email),coalesce(p_instructions,''))on conflict(shipment_id)do update set company_name=excluded.company_name,contact_email=excluded.contact_email,instructions=excluded.instructions;
 update public.urgent_offers set status='withdrawn'where shipment_id=s.id and status='submitted';get diagnostics withdrawn=row_count;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'shipment_updated');
 return jsonb_build_object('revision',s.revision+1,'withdrawn_offers',withdrawn,'changed',true);
end;$$;
revoke all on function public.urgent_update_scheduled_shipment(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,boolean)from public,anon;
grant execute on function public.urgent_update_scheduled_shipment(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,boolean)to authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_shipment_schedule_policy()as horaires_des_courses;

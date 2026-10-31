-- Conserver l'identité du donneur d'ordre dans chaque nouvelle version documentaire.
begin;
create function public.urgent_capture_shipper_branding()returns trigger
language plpgsql security definer set search_path='' as $$
declare company uuid;identity_data jsonb;
begin
 select owner_company_id into company from public.urgent_shipments where id=new.shipment_id;
 select data into identity_data from public.urgent_document_branding where company_id=company;
 new.snapshot:=jsonb_set(new.snapshot,'{owner}',coalesce(new.snapshot->'owner','{}'::jsonb)||jsonb_build_object('logo',coalesce(identity_data->>'logo',''),'address',coalesce(identity_data->>'address','')));
 return new;
end;$$;
revoke all on function public.urgent_capture_shipper_branding()from public,anon,authenticated;
create trigger urgent_capture_shipper_branding before insert on public.urgent_transport_documents for each row execute function public.urgent_capture_shipper_branding();
create or replace function public.urgent_transport_dossier(p_shipment uuid)returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.urgent_shipments;details public.urgent_shipment_private;offer public.urgent_offers;own_brand public.urgent_document_branding;docs jsonb;owner_name text;carrier_name text;
begin
 if auth.uid()is null or not public.urgent_is_party(p_shipment)then raise exception 'Dossier réservé aux parties';end if;
 select * into s from public.urgent_shipments where id=p_shipment;
 if s.accepted_offer_id is null then raise exception 'Course attribuée requise';end if;
 select * into details from public.urgent_shipment_private where shipment_id=s.id;
 select * into offer from public.urgent_offers where id=s.accepted_offer_id;
 select name into owner_name from public.companies where id=s.owner_company_id;
 select name into carrier_name from public.companies where id=s.assigned_company_id;
 select * into own_brand from public.urgent_document_branding where company_id=public.urgent_actor_company();
 select coalesce(jsonb_agg((to_jsonb(d) - 'request_data') #- '{snapshot,issuer,logo}' #- '{snapshot,owner,logo}' order by d.created_at desc,d.version desc),'[]')into docs
 from public.urgent_transport_documents d where d.shipment_id=s.id and(d.state='issued'or d.issuer_company_id=public.urgent_actor_company()or public.urgent_is_admin()or d.kind='waybill');
 return jsonb_build_object('shipment',jsonb_build_object('id',s.id,'origin',s.origin,'destination',s.destination,'pickup',s.pickup,'delivery_at',s.delivery_at,'vehicle',s.vehicle,'pallets',s.pallets,'weight',s.weight,'is_test',s.is_test,'status',s.status,'archived',s.archived_at is not null,'owner_company_id',s.owner_company_id,'assigned_company_id',s.assigned_company_id),'owner_name',owner_name,'carrier_name',carrier_name,'amount_ht',offer.amount_ht,'can_prepare',public.urgent_document_prepare_enabled(),'branding',coalesce(to_jsonb(own_brand),'{}'::jsonb),'defaults',jsonb_build_object('consignor_name',owner_name,'consignor_address',coalesce(details.pickup_address,''),'consignee_name','','consignee_address',coalesce(details.delivery_address,''),'goods_description',coalesce(details.instructions,''),'pallets',s.pallets,'weight_kg',s.weight),'documents',docs);
end;$$;

create function public.urgent_shipper_logo_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'version','20261031-shipper-logo','existing_versions_changed',false);$$;
revoke all on function public.urgent_shipper_logo_policy()from public;
grant execute on function public.urgent_shipper_logo_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_shipper_logo_policy()as logo_donneur_ordre;

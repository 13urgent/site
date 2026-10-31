-- Préparation de la lettre par le donneur d'ordre et partage d'un lot privé.
-- Prérequis : dossiers transport 310001 et services/messages privés 300002.
begin;
create or replace function public.urgent_save_transport_document(p_id uuid,p_shipment uuid,p_kind text,p_expected_version integer,p_state text,p_data jsonb,p_acknowledge boolean default false)returns jsonb
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;previous public.urgent_transport_documents;current_version integer;company uuid:=public.urgent_actor_company();issuer uuid;data jsonb;brand jsonb;offer public.urgent_offers;picture jsonb;owner_name text;carrier_name text;
begin
 if auth.uid()is null or not public.urgent_is_party(p_shipment)then raise exception 'Dossier réservé aux parties';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.accepted_offer_id is null then raise exception 'Course attribuée requise';end if;
 if p_id is null or p_kind is null or p_kind not in('confirmation','waybill')or p_state is null or p_state not in('draft','issued')or(p_kind='waybill'and p_state<>'draft')then raise exception 'Type de document invalide';end if;
 issuer:=case p_kind when 'confirmation'then s.owner_company_id else s.assigned_company_id end;
 if coalesce(public.urgent_actor_role()not in('client','carrier','admin'),true)or(p_kind='confirmation'and company is distinct from s.owner_company_id)or(p_kind='waybill'and not(company=s.owner_company_id or(company=s.assigned_company_id and public.urgent_actor_role()='carrier')))then raise exception 'Seule l’entreprise émettrice peut préparer ce document';end if;
 data:=public.urgent_validate_transport_document(p_data);
 select * into previous from public.urgent_transport_documents where id=p_id;
 if found then
  if previous.shipment_id=s.id and previous.kind=p_kind and previous.state=p_state and previous.created_by=auth.uid()and previous.request_data=data then return jsonb_build_object('id',previous.id,'version',previous.version,'state',previous.state);end if;
  raise exception 'Référence de document déjà utilisée';
 end if;
 if not public.urgent_document_prepare_enabled()then raise exception 'Module documentaire : accès de test à activer par l’administration';end if;
 if s.archived_at is not null or s.status in('completed','cancelled')then raise exception 'Dossier clôturé : création de version impossible';end if;
 if not(s.is_test and public.urgent_is_admin())and not exists(select 1 from public.urgent_business_access a where a.company_id=company and a.registry_checked and a.pilot_enabled)then raise exception 'Autorisation de l’établissement requise';end if;
 select coalesce(max(version),0)into current_version from public.urgent_transport_documents where shipment_id=s.id and kind=p_kind;
 if p_expected_version is distinct from current_version then raise exception 'Une nouvelle version existe. Rechargez le dossier avant de modifier';end if;
 if current_version>=200 then raise exception 'Limite de versions atteinte. Contactez l’administration';end if;
 select coalesce(b.data,'{}'::jsonb)into brand from public.urgent_document_branding b where b.company_id=case p_kind when 'waybill'then s.assigned_company_id else company end;
 brand:=coalesce(brand,'{}'::jsonb);
 if p_state='issued'then
  if p_acknowledge is distinct from true then raise exception 'Vérifiez et confirmez les informations avant émission';end if;
  if length(coalesce(brand->>'address',''))<5 or length(data->>'consignor_name')<2 or length(data->>'consignee_name')<2 or length(data->>'consignor_address')<5 or length(data->>'consignee_address')<5 or length(data->>'goods_description')<3 then raise exception 'Complétez l’adresse de votre entreprise, les parties, les adresses et la marchandise avant émission';end if;
 end if;
 select * into offer from public.urgent_offers where id=s.accepted_offer_id;
 select name into owner_name from public.companies where id=s.owner_company_id;
 select name into carrier_name from public.companies where id=s.assigned_company_id;
 picture:=jsonb_build_object('shipment_id',s.id,'is_test',s.is_test,'origin',s.origin,'destination',s.destination,'pickup',s.pickup,'delivery_at',s.delivery_at,'vehicle_type',s.vehicle,'original_pallets',s.pallets,'original_weight',s.weight,'owner',jsonb_build_object('id',s.owner_company_id,'name',owner_name,'siret',(select a.siret from public.urgent_business_access a where a.company_id=s.owner_company_id)),'carrier',jsonb_build_object('id',s.assigned_company_id,'name',carrier_name,'siret',(select a.siret from public.urgent_business_access a where a.company_id=s.assigned_company_id)),'issuer',brand||jsonb_build_object('company_id',case p_kind when 'waybill'then s.assigned_company_id else company end,'name',case p_kind when 'confirmation'then owner_name else carrier_name end),'prepared_by',jsonb_build_object('company_id',company,'name',case when company=s.owner_company_id then owner_name else carrier_name end),'data',data);
 if p_kind='confirmation'then picture:=picture||jsonb_build_object('amount_ht',offer.amount_ht);end if;
 insert into public.urgent_transport_documents(id,shipment_id,kind,version,state,issuer_company_id,created_by,request_data,snapshot)values(p_id,s.id,p_kind,current_version+1,p_state,company,auth.uid(),data,picture);
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),case when p_kind='confirmation'and p_state='issued'then 'affreightment_issued'when p_kind='confirmation'then 'affreightment_draft_saved'else 'waybill_prepared'end);
 return jsonb_build_object('id',p_id,'version',current_version+1,'state',p_state);
end;$$;

create table public.urgent_transport_document_deliveries(
 id uuid primary key,shipment_id uuid not null references public.urgent_shipments(id),
 confirmation_id uuid not null references public.urgent_transport_documents(id),waybill_id uuid not null references public.urgent_transport_documents(id),
 shared_by uuid not null references auth.users(id),recipient_id uuid not null references auth.users(id),created_at timestamptz not null default now(),
 unique(shipment_id,confirmation_id,waybill_id)
);
alter table public.urgent_transport_document_deliveries enable row level security;
revoke all on public.urgent_transport_document_deliveries from public,anon,authenticated;
grant select on public.urgent_transport_document_deliveries to authenticated;
create policy urgent_transport_document_deliveries_read on public.urgent_transport_document_deliveries for select to authenticated using(public.urgent_is_party(shipment_id));
create function public.urgent_share_transport_documents(p_id uuid,p_shipment uuid,p_confirmation uuid,p_waybill uuid)returns jsonb
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;o public.urgent_offers;prior public.urgent_transport_document_deliveries;begin
 if auth.uid()is null or coalesce(public.urgent_actor_role()not in('client','carrier','admin'),true)or not public.urgent_document_prepare_enabled()then raise exception 'Module documentaire autorisé requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company()then raise exception 'Entreprise donneur d’ordre requise';end if;
 if p_id is null or p_confirmation is null or p_waybill is null or s.accepted_offer_id is null then raise exception 'Course attribuée et deux documents requis';end if;
 select * into o from public.urgent_offers where id=s.accepted_offer_id;
 select * into prior from public.urgent_transport_document_deliveries where id=p_id;
 if found then
  if prior.shipment_id=s.id and prior.confirmation_id=p_confirmation and prior.waybill_id=p_waybill then return jsonb_build_object('shared',true,'id',prior.id,'reused',true);end if;
  raise exception 'Référence de partage déjà utilisée';end if;
 select * into prior from public.urgent_transport_document_deliveries where shipment_id=s.id and confirmation_id=p_confirmation and waybill_id=p_waybill;
 if found then return jsonb_build_object('shared',true,'id',prior.id,'reused',true);end if;
 if s.archived_at is not null or s.status in('cancelled','completed')then raise exception 'Dossier clôturé : nouveau partage impossible';end if;
 if p_confirmation is distinct from(select id from public.urgent_transport_documents where shipment_id=s.id and kind='confirmation'and state='issued'order by version desc limit 1)or p_waybill is distinct from(select id from public.urgent_transport_documents where shipment_id=s.id and kind='waybill'order by version desc limit 1)then raise exception 'Vérifiez les dernières versions : confirmation émise et lettre de voiture enregistrée';end if;
 if not exists(select 1 from public.profiles where id=o.carrier_id and company_id=s.assigned_company_id and role::text='carrier')then raise exception 'Rattachement du transporteur à vérifier';end if;
 insert into public.urgent_transport_document_deliveries(id,shipment_id,confirmation_id,waybill_id,shared_by,recipient_id)values(p_id,s.id,p_confirmation,p_waybill,auth.uid(),o.carrier_id);
 perform public.urgent_send_course_message(p_id,s.id,'Votre confirmation d’affrètement et votre lettre de voiture sont disponibles dans le dossier transport de cette course. Ouvrez les deux documents pour les vérifier et les imprimer. Confirmation : '||p_confirmation::text||' ; lettre de voiture : '||p_waybill::text||'.');
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'transport_documents_shared');
 return jsonb_build_object('shared',true,'id',p_id,'reused',false);
end;$$;
revoke all on function public.urgent_share_transport_documents(uuid,uuid,uuid,uuid)from public,anon;
grant execute on function public.urgent_share_transport_documents(uuid,uuid,uuid,uuid)to authenticated;
create or replace function public.urgent_transport_dossier_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'rollout','admin_controlled_pilot','version','20261031-document-delivery','confirmation',true,'waybill_preparation',true,'shipper_waybill',true,'document_delivery',true,'electronic_signature',false);$$;
commit;
notify pgrst,'reload schema';
select public.urgent_transport_dossier_policy()as partage_documents;

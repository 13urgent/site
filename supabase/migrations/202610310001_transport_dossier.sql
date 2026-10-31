-- Première étape : confirmations d'affrètement et préparations de lettres de voiture.
-- Prérequis : pilote, archivage, missions mobiles et horaires déjà activés.
-- Aucune facture, signature électronique, e-CMR ou nouvelle tarification n'est créée.
begin;
create table public.urgent_transport_document_access(
 company_id uuid primary key references public.companies(id),enabled boolean not null default false,
 reviewed_by uuid not null references auth.users(id),reviewed_at timestamptz not null default now()
);
alter table public.urgent_transport_document_access enable row level security;
revoke all on public.urgent_transport_document_access from public,anon,authenticated;
grant select on public.urgent_transport_document_access to authenticated;
create policy urgent_transport_access_read on public.urgent_transport_document_access for select to authenticated
 using(company_id=public.urgent_actor_company()or public.urgent_is_admin());
create function public.urgent_document_prepare_enabled()returns boolean
language sql stable security definer set search_path='' as $$
 select auth.uid()is not null and(public.urgent_is_admin()or exists(select 1 from public.urgent_transport_document_access a where a.company_id=public.urgent_actor_company()and a.enabled));
$$;
create function public.urgent_review_transport_document_access(p_company uuid,p_enabled boolean)returns void
language plpgsql security definer set search_path='' as $$
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_company is null or p_enabled is null or not exists(select 1 from public.companies where id=p_company)then raise exception 'Entreprise ou décision invalide';end if;
 insert into public.urgent_transport_document_access(company_id,enabled,reviewed_by)values(p_company,p_enabled,auth.uid())
 on conflict(company_id)do update set enabled=excluded.enabled,reviewed_by=auth.uid(),reviewed_at=now();
end;$$;
create function public.urgent_transport_document_directory(p_query text default '',p_offset integer default 0)
returns table(company_id uuid,company_name text,enabled boolean)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_query is null or length(p_query)>100 or p_offset is null or p_offset<0 or p_offset>100000 then raise exception 'Recherche invalide';end if;
 return query select c.id,c.name::text,coalesce(a.enabled,false)from public.companies c
 left join public.urgent_transport_document_access a on a.company_id=c.id
 where exists(select 1 from public.profiles p where p.company_id=c.id)and position(lower(trim(p_query))in lower(c.name))>0
 order by c.name,c.id limit 100 offset p_offset;
end;$$;
create table public.urgent_document_branding(
 company_id uuid primary key references public.companies(id),
 data jsonb not null default '{}'::jsonb,
 revision integer not null default 1,
 updated_by uuid not null references auth.users(id),updated_at timestamptz not null default now()
);
create table public.urgent_transport_documents(
 id uuid primary key,shipment_id uuid not null references public.urgent_shipments(id),
 kind text not null check(kind in('confirmation','waybill')),
 version integer not null check(version between 1 and 200),
 state text not null check(state in('draft','issued')),
 issuer_company_id uuid not null references public.companies(id),
 created_by uuid not null references auth.users(id),created_at timestamptz not null default now(),
 request_data jsonb not null,snapshot jsonb not null,
 unique(shipment_id,kind,version),check(kind<>'waybill' or state='draft')
);
alter table public.urgent_document_branding enable row level security;
alter table public.urgent_transport_documents enable row level security;
revoke all on public.urgent_document_branding,public.urgent_transport_documents from public,anon,authenticated;
grant select on public.urgent_document_branding,public.urgent_transport_documents to authenticated;
create policy urgent_branding_own_read on public.urgent_document_branding for select to authenticated
 using(company_id=public.urgent_actor_company()or public.urgent_is_admin());
create policy urgent_transport_document_read on public.urgent_transport_documents for select to authenticated
 using(public.urgent_is_party(shipment_id)and(state='issued'or issuer_company_id=public.urgent_actor_company()or public.urgent_is_admin()or kind='waybill'));

create function public.urgent_validate_document_branding(p_data jsonb)returns jsonb
language plpgsql immutable set search_path='' as $$
declare result jsonb:='{}';key text;value text;logo bytea;width bigint;height bigint;
begin
 if p_data is null or jsonb_typeof(p_data)<>'object' or octet_length(p_data::text)>120000 then raise exception 'Identité ou logo trop volumineux';end if;
 if exists(select 1 from jsonb_object_keys(p_data)k where k not in('address','contact_email','phone','logo'))then raise exception 'Champ identité inconnu';end if;
 foreach key in array array['address','contact_email','phone','logo']loop
  if p_data?key and jsonb_typeof(p_data->key)<>'string'then raise exception 'Champ identité invalide';end if;
  value:=trim(coalesce(p_data->>key,''));
  if key<>'logo'and(length(value)>case key when 'address'then 500 when 'contact_email'then 254 else 40 end or value~'[[:cntrl:]]'and key<>'address')then raise exception 'Coordonnées invalides';end if;
  if key='contact_email'and value<>''and value!~'^[^[:space:]<>@]+@[^[:space:]<>@]+[.][^[:space:]<>@]+$'then raise exception 'E-mail invalide';end if;
  if key='logo'and value<>''then
   if length(value)>110000 or value!~'^data:image/png;base64,[A-Za-z0-9+/=]+$'then raise exception 'Logo PNG requis (80 Ko maximum)';end if;
   begin logo:=decode(substring(value from 23),'base64');exception when others then raise exception 'Logo invalide';end;
   if octet_length(logo)<33 or octet_length(logo)>81920 or substring(logo from 1 for 8)<>decode('89504e470d0a1a0a','hex')or substring(logo from 13 for 4)<>decode('49484452','hex')then raise exception 'Logo PNG invalide';end if;
   width:=get_byte(logo,16)::bigint*16777216+get_byte(logo,17)*65536+get_byte(logo,18)*256+get_byte(logo,19);
   height:=get_byte(logo,20)::bigint*16777216+get_byte(logo,21)*65536+get_byte(logo,22)*256+get_byte(logo,23);
   if width not between 1 and 1024 or height not between 1 and 1024 then raise exception 'Dimensions du logo invalides';end if;
  end if;
  result:=result||jsonb_build_object(key,value);
 end loop;
 return result;
end;$$;
create function public.urgent_save_document_branding(p_expected_revision integer,p_data jsonb)returns integer
language plpgsql security definer set search_path='' as $$
declare company uuid:=public.urgent_actor_company();previous public.urgent_document_branding;data jsonb;
begin
 if auth.uid()is null or company is null or coalesce(public.urgent_actor_role()not in('client','carrier','admin'),true)then raise exception 'Compte professionnel requis';end if;
 if not public.urgent_document_prepare_enabled()then raise exception 'Module documentaire : accès de test à activer par l’administration';end if;
 perform pg_advisory_xact_lock(hashtextextended('document-branding/'||company::text,0));
 data:=public.urgent_validate_document_branding(p_data);
 select * into previous from public.urgent_document_branding where company_id=company;
 if found and previous.data=data then return previous.revision;end if;
 if p_expected_revision is distinct from coalesce(previous.revision,0)then raise exception 'Identité modifiée depuis son ouverture. Rechargez avant de modifier';end if;
 insert into public.urgent_document_branding(company_id,data,revision,updated_by)values(company,data,1,auth.uid())
 on conflict(company_id)do update set data=excluded.data,revision=urgent_document_branding.revision+1,updated_by=auth.uid(),updated_at=now()
 returning revision into p_expected_revision;
 return p_expected_revision;
end;$$;

create function public.urgent_validate_transport_document(p_data jsonb)returns jsonb
language plpgsql immutable set search_path='' as $$
declare result jsonb:='{}';key text;value text;number numeric;
begin
 if p_data is null or jsonb_typeof(p_data)<>'object'or octet_length(p_data::text)>20000 then raise exception 'Document invalide ou trop volumineux';end if;
 if exists(select 1 from jsonb_object_keys(p_data)k where k not in('consignor_name','consignor_address','consignee_name','consignee_address','goods_description','units','pallets','weight_kg','instructions','payment_terms','vehicle_plate','trailer_plate','driver_name','driver_phone','pickup_reservations','delivery_reservations','order_reference','customer_reference','external_ecmr_reference'))then raise exception 'Champ document inconnu';end if;
 foreach key in array array['consignor_name','consignor_address','consignee_name','consignee_address','goods_description','units','pallets','weight_kg','instructions','payment_terms','vehicle_plate','trailer_plate','driver_name','driver_phone','pickup_reservations','delivery_reservations','order_reference','customer_reference','external_ecmr_reference']loop
  if p_data?key and jsonb_typeof(p_data->key)not in('string','number')then raise exception 'Champ document invalide';end if;
  value:=trim(coalesce(p_data->>key,''));
  if length(value)>(case when key in('instructions','pickup_reservations','delivery_reservations')then 2000 when key in('consignor_address','consignee_address','goods_description','payment_terms')then 1000 else 120 end)then raise exception 'Champ document trop long';end if;
  if key in('units','pallets','weight_kg')and value<>''then
   if value!~'^[0-9]{1,6}([.][0-9]{1,2})?$'then raise exception 'Quantité ou poids invalide';end if;
   number:=value::numeric;
   if number>100000 or(key<>'weight_kg'and number<>trunc(number))then raise exception 'Quantité ou poids hors limites';end if;
   result:=result||jsonb_build_object(key,number);
  else result:=result||jsonb_build_object(key,value);end if;
 end loop;
 return result;
end;$$;

create function public.urgent_transport_dossier(p_shipment uuid)returns jsonb
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
 select coalesce(jsonb_agg((to_jsonb(d) - 'request_data') #- '{snapshot,issuer,logo}' order by d.created_at desc,d.version desc),'[]')into docs
 from public.urgent_transport_documents d where d.shipment_id=s.id and(d.state='issued'or d.issuer_company_id=public.urgent_actor_company()or public.urgent_is_admin()or d.kind='waybill');
 return jsonb_build_object('shipment',jsonb_build_object('id',s.id,'origin',s.origin,'destination',s.destination,'pickup',s.pickup,'delivery_at',s.delivery_at,'vehicle',s.vehicle,'pallets',s.pallets,'weight',s.weight,'is_test',s.is_test,'status',s.status,'archived',s.archived_at is not null,'owner_company_id',s.owner_company_id,'assigned_company_id',s.assigned_company_id),'owner_name',owner_name,'carrier_name',carrier_name,'amount_ht',offer.amount_ht,'can_prepare',public.urgent_document_prepare_enabled(),'branding',coalesce(to_jsonb(own_brand),'{}'::jsonb),'defaults',jsonb_build_object('consignor_name',owner_name,'consignor_address',coalesce(details.pickup_address,''),'consignee_name','','consignee_address',coalesce(details.delivery_address,''),'goods_description',coalesce(details.instructions,''),'pallets',s.pallets,'weight_kg',s.weight),'documents',docs);
end;$$;

create function public.urgent_transport_document(p_id uuid)returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare d public.urgent_transport_documents;
begin
 select * into d from public.urgent_transport_documents where id=p_id;
 if auth.uid()is null or not found or not public.urgent_is_party(d.shipment_id)or not(d.state='issued'or d.issuer_company_id=public.urgent_actor_company()or public.urgent_is_admin()or d.kind='waybill')then raise exception 'Document réservé aux parties autorisées';end if;
 return to_jsonb(d)-'request_data';
end;$$;

create function public.urgent_save_transport_document(p_id uuid,p_shipment uuid,p_kind text,p_expected_version integer,p_state text,p_data jsonb,p_acknowledge boolean default false)returns jsonb
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;previous public.urgent_transport_documents;current_version integer;company uuid:=public.urgent_actor_company();issuer uuid;data jsonb;brand jsonb;offer public.urgent_offers;picture jsonb;owner_name text;carrier_name text;
begin
 if auth.uid()is null or not public.urgent_is_party(p_shipment)then raise exception 'Dossier réservé aux parties';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.accepted_offer_id is null then raise exception 'Course attribuée requise';end if;
 if p_id is null or p_kind is null or p_kind not in('confirmation','waybill')or p_state is null or p_state not in('draft','issued')or(p_kind='waybill'and p_state<>'draft')then raise exception 'Type de document invalide';end if;
 issuer:=case p_kind when 'confirmation'then s.owner_company_id else s.assigned_company_id end;
 if company is distinct from issuer or coalesce(public.urgent_actor_role()not in('client','carrier','admin'),true)or(p_kind='waybill'and public.urgent_actor_role()<>'carrier')then raise exception 'Seule l’entreprise émettrice peut préparer ce document';end if;
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
 select coalesce(b.data,'{}'::jsonb)into brand from public.urgent_document_branding b where b.company_id=company;
 brand:=coalesce(brand,'{}'::jsonb);
 if p_state='issued'then
  if p_acknowledge is distinct from true then raise exception 'Vérifiez et confirmez les informations avant émission';end if;
  if length(coalesce(brand->>'address',''))<5 or length(data->>'consignor_name')<2 or length(data->>'consignee_name')<2 or length(data->>'consignor_address')<5 or length(data->>'consignee_address')<5 or length(data->>'goods_description')<3 then raise exception 'Complétez l’adresse de votre entreprise, les parties, les adresses et la marchandise avant émission';end if;
 end if;
 select * into offer from public.urgent_offers where id=s.accepted_offer_id;
 select name into owner_name from public.companies where id=s.owner_company_id;
 select name into carrier_name from public.companies where id=s.assigned_company_id;
 picture:=jsonb_build_object('shipment_id',s.id,'is_test',s.is_test,'origin',s.origin,'destination',s.destination,'pickup',s.pickup,'delivery_at',s.delivery_at,'vehicle_type',s.vehicle,'original_pallets',s.pallets,'original_weight',s.weight,'owner',jsonb_build_object('id',s.owner_company_id,'name',owner_name,'siret',(select a.siret from public.urgent_business_access a where a.company_id=s.owner_company_id)),'carrier',jsonb_build_object('id',s.assigned_company_id,'name',carrier_name,'siret',(select a.siret from public.urgent_business_access a where a.company_id=s.assigned_company_id)),'issuer',brand||jsonb_build_object('company_id',company,'name',case p_kind when 'confirmation'then owner_name else carrier_name end),'data',data);
 if p_kind='confirmation'then picture:=picture||jsonb_build_object('amount_ht',offer.amount_ht);end if;
 insert into public.urgent_transport_documents(id,shipment_id,kind,version,state,issuer_company_id,created_by,request_data,snapshot)values(p_id,s.id,p_kind,current_version+1,p_state,company,auth.uid(),data,picture);
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),case when p_kind='confirmation'and p_state='issued'then 'affreightment_issued'when p_kind='confirmation'then 'affreightment_draft_saved'else 'waybill_prepared'end);
 return jsonb_build_object('id',p_id,'version',current_version+1,'state',p_state);
end;$$;
create function public.urgent_transport_dossier_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'rollout','admin_controlled_pilot','version','20261031-transport-dossier','confirmation',true,'waybill_preparation',true,'electronic_signature',false);$$;
revoke all on function public.urgent_validate_document_branding(jsonb),public.urgent_validate_transport_document(jsonb)from public,anon,authenticated;
revoke all on function public.urgent_transport_document_directory(text,integer),public.urgent_document_prepare_enabled(),public.urgent_review_transport_document_access(uuid,boolean),public.urgent_save_document_branding(integer,jsonb),public.urgent_transport_dossier(uuid),public.urgent_transport_document(uuid),public.urgent_save_transport_document(uuid,uuid,text,integer,text,jsonb,boolean)from public,anon;
grant execute on function public.urgent_transport_document_directory(text,integer),public.urgent_document_prepare_enabled(),public.urgent_review_transport_document_access(uuid,boolean),public.urgent_save_document_branding(integer,jsonb),public.urgent_transport_dossier(uuid),public.urgent_transport_document(uuid),public.urgent_save_transport_document(uuid,uuid,text,integer,text,jsonb,boolean)to authenticated;
revoke all on function public.urgent_transport_dossier_policy()from public;
grant execute on function public.urgent_transport_dossier_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_transport_dossier_policy()as dossier_transport;

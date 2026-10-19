-- Outils administrateur pour éviter les corrections SQL manuelles de documents.
-- Dépend de la migration pilote et de 202610190001_document_categories.sql.
begin;
create table public.urgent_document_review_events (
 id uuid primary key default gen_random_uuid(),
 document_id uuid not null references public.carrier_documents(id),
 actor_id uuid not null references auth.users(id),
 previous_type text not null,
 new_type text not null,
 previous_expiry date,
 new_expiry date,
 created_at timestamptz not null default now()
);
alter table public.urgent_document_review_events enable row level security;
revoke all on public.urgent_document_review_events from anon,authenticated;
grant select on public.urgent_document_review_events to authenticated;
create policy urgent_document_review_admin_read on public.urgent_document_review_events
for select to authenticated using(public.urgent_is_admin());
create function public.urgent_correct_document(p_document uuid,p_kind text,p_expiry date) returns void
language plpgsql security definer set search_path='' as $$
declare old_doc public.carrier_documents;
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_kind is null or p_kind not in ('registration','transport_licence','insurance_rc','insurance_goods','other') then raise exception 'Catégorie non autorisée';end if;
 select * into old_doc from public.carrier_documents where id=p_document for update;
 if not found then raise exception 'Document introuvable';end if;
 if old_doc.document_type=p_kind and old_doc.expires_on is not distinct from p_expiry then return;end if;
 update public.carrier_documents set document_type=p_kind,expires_on=p_expiry,review_status='pending',reviewed_at=null,reviewed_by=null where id=p_document;
 insert into public.urgent_document_review_events(document_id,actor_id,previous_type,new_type,previous_expiry,new_expiry)
 values(p_document,auth.uid(),old_doc.document_type,p_kind,old_doc.expires_on,p_expiry);
end;
$$;
create function public.urgent_document_checklist(p_company uuid)
returns table(document_type text,document_id uuid,review_status text,expires_on date,reason text)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() and p_company is distinct from public.urgent_actor_company() then raise exception 'Accès au dossier non autorisé';end if;
 return query select required.kind,d.id,d.review_status::text,d.expires_on,
 case when d.id is null then 'missing'
 when d.review_status is distinct from 'approved' then 'not_approved'
 when required.kind<>'registration' and d.expires_on is null then 'expiry_missing'
 when d.expires_on<(now() at time zone 'Europe/Paris')::date then 'expired'
 else 'valid' end
 from (values('registration'),('transport_licence'),('insurance_rc'),('insurance_goods')) required(kind)
 left join lateral(select cd.id,cd.review_status,cd.expires_on from public.carrier_documents cd
 where cd.company_id=p_company and cd.document_type=required.kind order by cd.created_at desc,cd.id desc limit 1) d on true;
end;
$$;
create or replace function public.urgent_carrier_ready(p_company uuid)
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
revoke all on function public.urgent_correct_document(uuid,text,date),public.urgent_document_checklist(uuid),public.urgent_carrier_ready(uuid) from public,anon;
grant execute on function public.urgent_correct_document(uuid,text,date),public.urgent_document_checklist(uuid),public.urgent_carrier_ready(uuid) to authenticated;

-- Signalements de prestation, privés entre parties et administration.
create table public.urgent_shipment_incidents (
 id uuid primary key default gen_random_uuid(),
 shipment_id uuid not null references public.urgent_shipments(id),
 reported_by uuid not null references auth.users(id),
 description text not null check(length(trim(description)) between 10 and 2000),
 status text not null default 'open' check(status in ('open','resolved')),
 resolution text,
 resolved_by uuid references auth.users(id),
 resolved_at timestamptz,
 created_at timestamptz not null default now()
);
create unique index on public.urgent_shipment_incidents(shipment_id,reported_by) where status='open';
alter table public.urgent_shipment_incidents enable row level security;
revoke all on public.urgent_shipment_incidents from anon,authenticated;
grant select on public.urgent_shipment_incidents to authenticated;
create policy urgent_incidents_party_read on public.urgent_shipment_incidents for select to authenticated using(public.urgent_is_party(shipment_id));
create function public.urgent_report_incident(p_shipment uuid,p_description text) returns uuid
language plpgsql security definer set search_path='' as $$
declare shipment public.urgent_shipments;result uuid;
begin
 if not public.urgent_is_party(p_shipment) then raise exception 'Accès réservé aux parties';end if;
 select * into shipment from public.urgent_shipments where id=p_shipment for update;
 if shipment.accepted_offer_id is null then raise exception 'Signalement réservé aux courses attribuées';end if;
 if exists(select 1 from public.urgent_shipment_incidents where shipment_id=p_shipment and reported_by=auth.uid() and status='open') then raise exception 'Un signalement de votre compte est déjà ouvert pour cette course';end if;
 insert into public.urgent_shipment_incidents(shipment_id,reported_by,description)values(p_shipment,auth.uid(),trim(p_description))returning id into result;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'incident_reported');
 return result;
end;
$$;
create function public.urgent_resolve_incident(p_incident uuid,p_resolution text) returns void
language plpgsql security definer set search_path='' as $$
declare shipment uuid;
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_resolution is null or length(trim(p_resolution)) not between 10 and 2000 then raise exception 'Décrivez le traitement du signalement (10 à 2000 caractères)';end if;
 select shipment_id into shipment from public.urgent_shipment_incidents where id=p_incident;
 if not found then raise exception 'Signalement introuvable';end if;
 perform 1 from public.urgent_shipments where id=shipment for update;
 update public.urgent_shipment_incidents set status='resolved',resolution=trim(p_resolution),resolved_by=auth.uid(),resolved_at=now() where id=p_incident and status='open';
 if not found then raise exception 'Signalement déjà clôturé';end if;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(shipment,auth.uid(),'incident_resolved');
end;
$$;
revoke all on function public.urgent_report_incident(uuid,text),public.urgent_resolve_incident(uuid,text) from public,anon;
grant execute on function public.urgent_report_incident(uuid,text),public.urgent_resolve_incident(uuid,text) to authenticated;

create or replace function public.urgent_progress_shipment(p_shipment uuid,p_next text) returns void
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;expected text;
begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found then raise exception 'Course introuvable';end if;
 if p_next='completed' then
  if exists(select 1 from public.urgent_shipment_incidents where shipment_id=p_shipment and status='open') then raise exception 'Un signalement est encore ouvert. Contactez 13 URGENT avant de confirmer la réalisation.';end if;
  if s.owner_company_id is distinct from public.urgent_actor_company() or s.status<>'delivery_reported' then raise exception 'Confirmation du client requise après déclaration de livraison';end if;
 else
  if public.urgent_actor_role()<>'carrier' or s.assigned_company_id is distinct from public.urgent_actor_company() then raise exception 'Transporteur attribué requis';end if;
  expected:=case s.status when 'assigned' then 'heading_pickup' when 'heading_pickup' then 'at_pickup' when 'at_pickup' then 'loaded' when 'loaded' then 'delivery_reported' else null end;
  if expected is null or p_next is distinct from expected then raise exception 'Transition non autorisée';end if;
 end if;
 update public.urgent_shipments set status=p_next,updated_at=now() where id=p_shipment;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),p_next);
end;
$$;
commit;

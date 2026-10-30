-- Services nationaux, projets réguliers, capacités, messagerie et demandes de devis.
-- Aucun droit transporteur, abonnement, tarif ou validation existant n'est assoupli.
begin;
create table public.urgent_transport_details(
 shipment_id uuid primary key references public.urgent_shipments(id),
 origin_postcode text not null check(origin_postcode~'^[0-9]{5}$'),
 destination_postcode text not null check(destination_postcode~'^[0-9]{5}$'),
 service text not null check(service in('express','regular','moving','bulky')),
 stops jsonb not null default '[]' check(jsonb_typeof(stops)='array'and jsonb_array_length(stops)<=8),
 frequency text not null default 'once'check(frequency in('once','daily','weekly','monthly')),
 until_on date,return_trip boolean not null default false,volume_m3 numeric check(volume_m3>0 and volume_m3<=200),
 updated_at timestamptz not null default now()
);
alter table public.urgent_transport_details enable row level security;
revoke all on public.urgent_transport_details from public,anon,authenticated;
grant select on public.urgent_transport_details to authenticated;
create policy urgent_transport_details_read on public.urgent_transport_details for select to authenticated
 using(exists(select 1 from public.urgent_shipments s where s.id=shipment_id));

create function public.urgent_validate_transport_details(p_details jsonb,p_pickup timestamptz)returns jsonb
language plpgsql immutable set search_path='' as $$
declare d jsonb;v jsonb;stops jsonb:='[]';volume numeric;ending date;
begin
 if p_details is null or jsonb_typeof(p_details)<>'object' then raise exception 'Informations de transport requises';end if;
 if coalesce(p_details->>'origin_postcode','')!~'^[0-9]{5}$'or coalesce(p_details->>'destination_postcode','')!~'^[0-9]{5}$'then raise exception 'Codes postaux français à cinq chiffres requis';end if;
 if coalesce(p_details->>'service','')not in('express','regular','moving','bulky')or coalesce(p_details->>'frequency','once')not in('once','daily','weekly','monthly')then raise exception 'Service ou fréquence invalide';end if;
 if p_details->>'service'='regular'and coalesce(p_details->>'frequency','once')='once'then raise exception 'Précisez la fréquence du trajet régulier';end if;
 if p_details->>'service'<>'regular'and coalesce(p_details->>'frequency','once')<>'once'then raise exception 'La récurrence est réservée au trajet régulier';end if;
 if p_details?'stops'and(jsonb_typeof(p_details->'stops')<>'array'or jsonb_array_length(p_details->'stops')>8)then raise exception 'Huit arrêts intermédiaires maximum';end if;
 for v in select value from jsonb_array_elements(coalesce(p_details->'stops','[]'))loop
  if jsonb_typeof(v)<>'object'or length(trim(coalesce(v->>'city','')))not between 1 and 100 or coalesce(v->>'postcode','')!~'^[0-9]{5}$'then raise exception 'Ville et code postal requis pour chaque arrêt';end if;
  stops:=stops||jsonb_build_array(jsonb_build_object('city',trim(v->>'city'),'postcode',v->>'postcode'));
 end loop;
 volume:=nullif(p_details->>'volume_m3','')::numeric;ending:=nullif(p_details->>'until_on','')::date;
 if volume is not null and(volume<=0 or volume>200)then raise exception 'Volume compris entre 0 et 200 m³';end if;
 if ending is not null and ending<(p_pickup at time zone 'Europe/Paris')::date then raise exception 'La fin de récurrence précède le départ';end if;
 return jsonb_build_object('origin_postcode',p_details->>'origin_postcode','destination_postcode',p_details->>'destination_postcode','service',p_details->>'service','stops',stops,'frequency',coalesce(p_details->>'frequency','once'),'until_on',ending,'return_trip',coalesce((p_details->>'return_trip')::boolean,false),'volume_m3',volume);
end;$$;
revoke all on function public.urgent_validate_transport_details(jsonb,timestamptz)from public,anon,authenticated;

create function public.urgent_publish_transport_request(p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text,p_delivery_at timestamptz,p_details jsonb,p_is_test boolean default false)returns uuid
language plpgsql security definer set search_path='' as $$declare sid uuid;d jsonb;begin
 d:=public.urgent_validate_transport_details(p_details,p_pickup);
 sid:=public.urgent_publish_scheduled_shipment(p_origin,p_destination,p_pickup,p_vehicle,p_pallets,p_weight,p_company_name,p_email,p_instructions,p_delivery_at,p_is_test);
 insert into public.urgent_transport_details values(sid,d->>'origin_postcode',d->>'destination_postcode',d->>'service',d->'stops',d->>'frequency',(d->>'until_on')::date,(d->>'return_trip')::boolean,(d->>'volume_m3')::numeric,now());return sid;
end;$$;
create function public.urgent_update_transport_request(p_shipment uuid,p_expected_revision integer,p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text,p_delivery_at timestamptz,p_details jsonb,p_acknowledge_offers boolean default false)returns jsonb
language plpgsql security definer set search_path='' as $$declare d jsonb;old_details jsonb;r jsonb;s public.urgent_shipments;n integer;begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company()then raise exception 'Entreprise propriétaire requise';end if;
 d:=public.urgent_validate_transport_details(p_details,p_pickup);
 select to_jsonb(t)-'shipment_id'-'updated_at'into old_details from public.urgent_transport_details t where shipment_id=p_shipment;
 r:=public.urgent_update_scheduled_shipment(p_shipment,p_expected_revision,p_origin,p_destination,p_pickup,p_vehicle,p_pallets,p_weight,p_company_name,p_email,p_instructions,p_delivery_at,p_acknowledge_offers);
 if old_details is distinct from d and not(r->>'changed')::boolean then
  if exists(select 1 from public.urgent_offers where shipment_id=p_shipment and status='submitted')and p_acknowledge_offers is distinct from true then raise exception 'Confirmez le retrait des offres avant de modifier';end if;
  update public.urgent_offers set status='withdrawn'where shipment_id=p_shipment and status='submitted';get diagnostics n=row_count;
  update public.urgent_shipments set revision=revision+1,updated_at=now()where id=p_shipment;
  insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'shipment_updated');r:=jsonb_build_object('revision',s.revision+1,'changed',true,'withdrawn_offers',n);
 end if;
 insert into public.urgent_transport_details values(p_shipment,d->>'origin_postcode',d->>'destination_postcode',d->>'service',d->'stops',d->>'frequency',(d->>'until_on')::date,(d->>'return_trip')::boolean,(d->>'volume_m3')::numeric,now())on conflict(shipment_id)do update set origin_postcode=excluded.origin_postcode,destination_postcode=excluded.destination_postcode,service=excluded.service,stops=excluded.stops,frequency=excluded.frequency,until_on=excluded.until_on,return_trip=excluded.return_trip,volume_m3=excluded.volume_m3,updated_at=now();return r;
end;$$;

create table public.urgent_carrier_alert_preferences(user_id uuid primary key references auth.users(id),enabled boolean not null default false,origin_departments text[]not null default '{}',destination_departments text[]not null default '{}',vehicles text[]not null default '{}',updated_at timestamptz not null default now());
alter table public.urgent_carrier_alert_preferences enable row level security;
revoke all on public.urgent_carrier_alert_preferences from public,anon,authenticated;
grant select on public.urgent_carrier_alert_preferences to authenticated;
create policy urgent_alert_preferences_read on public.urgent_carrier_alert_preferences for select to authenticated using(user_id=auth.uid());
create function public.urgent_save_alert_preferences(p_enabled boolean,p_origins text[],p_destinations text[],p_vehicles text[])returns void language plpgsql security definer set search_path='' as $$begin
 if public.urgent_actor_role()is distinct from'carrier'or auth.uid()is null then raise exception 'Compte transporteur requis';end if;
 if p_enabled is null or p_origins is null or p_destinations is null or p_vehicles is null or cardinality(p_origins)>102 or cardinality(p_destinations)>102 or cardinality(p_vehicles)>6 then raise exception 'Préférences invalides';end if;
 if exists(select 1 from unnest(p_origins||p_destinations)x where x is null or x!~'^(0[1-9]|[1-8][0-9]|9[0-5]|2A|2B|97[1-6])$')or exists(select 1 from unnest(p_vehicles)x where x is null or x not in('Deux-roues','VL / fourgon','20 m³ avec hayon','Porteur','Semi-remorque'))then raise exception 'Département ou véhicule invalide';end if;
 insert into public.urgent_carrier_alert_preferences values(auth.uid(),p_enabled,p_origins,p_destinations,p_vehicles,now())on conflict(user_id)do update set enabled=excluded.enabled,origin_departments=excluded.origin_departments,destination_departments=excluded.destination_departments,vehicles=excluded.vehicles,updated_at=now();
end;$$;
create function public.urgent_department(p_postcode text)returns text language sql immutable set search_path='' as $$select case when left(p_postcode,2)='97'then left(p_postcode,3)when left(p_postcode,3)in('200','201')then'2A'when left(p_postcode,3)in('202','206')then'2B'else left(p_postcode,2)end;$$;
revoke all on function public.urgent_department(text)from public,anon,authenticated;

create table public.urgent_capacity_notices(id uuid primary key default gen_random_uuid(),company_id uuid not null references public.companies(id),created_by uuid not null references auth.users(id),origin text not null check(length(trim(origin))between 1 and 100),origin_postcode text not null check(origin_postcode~'^[0-9]{5}$'),destination text not null check(length(trim(destination))between 1 and 100),destination_postcode text not null check(destination_postcode~'^[0-9]{5}$'),available_from timestamptz not null,available_until timestamptz not null check(available_until>available_from),vehicle text not null check(vehicle in('Deux-roues','VL / fourgon','20 m³ avec hayon','Porteur','Semi-remorque')),pallets integer not null check(pallets between 0 and 99),weight numeric not null check(weight between 0 and 40000),notes text not null default ''check(length(notes)<=500),closed_at timestamptz,created_at timestamptz not null default now());
alter table public.urgent_capacity_notices enable row level security;
revoke all on public.urgent_capacity_notices from public,anon,authenticated;
grant select on public.urgent_capacity_notices to authenticated;
create policy urgent_capacity_read on public.urgent_capacity_notices for select to authenticated using(auth.uid()is not null and public.urgent_actor_role()in('client','carrier','admin')and(company_id=public.urgent_actor_company()or public.urgent_is_admin()or(closed_at is null and available_until>now()and public.urgent_carrier_ready(company_id))));
create function public.urgent_save_capacity(p_id uuid,p_origin text,p_origin_postcode text,p_destination text,p_destination_postcode text,p_from timestamptz,p_until timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_notes text)returns uuid language plpgsql security definer set search_path='' as $$declare previous public.urgent_capacity_notices;begin
 if public.urgent_actor_role()is distinct from'carrier'or not public.urgent_carrier_ready(public.urgent_actor_company())then raise exception 'Dossier transporteur et droits actifs requis';end if;
 if p_id is null or p_from is null or p_until is null or p_from<now()or p_until>now()+interval'180 days'then raise exception 'Choisissez une disponibilité future de moins de six mois';end if;
 select * into previous from public.urgent_capacity_notices where id=p_id for update;
 if found then
  if previous.company_id is distinct from public.urgent_actor_company()or previous.created_by is distinct from auth.uid()then raise exception 'Annonce appartenant à un autre compte';end if;
  if row(previous.origin,previous.origin_postcode,previous.destination,previous.destination_postcode,previous.available_from,previous.available_until,previous.vehicle,previous.pallets,previous.weight,previous.notes)is distinct from row(trim(p_origin),p_origin_postcode,trim(p_destination),p_destination_postcode,p_from,p_until,p_vehicle,p_pallets,p_weight,coalesce(p_notes,''))then raise exception 'Cette annonce existe déjà. Fermez-la pour publier une nouvelle disponibilité';end if;return p_id;
 end if;
 if(select count(*)from public.urgent_capacity_notices where company_id=public.urgent_actor_company()and closed_at is null and available_until>now())>=20 then raise exception 'Vingt disponibilités actives maximum';end if;
 insert into public.urgent_capacity_notices values(p_id,public.urgent_actor_company(),auth.uid(),trim(p_origin),p_origin_postcode,trim(p_destination),p_destination_postcode,p_from,p_until,p_vehicle,p_pallets,p_weight,coalesce(p_notes,''),null,now());return p_id;
end;$$;
create function public.urgent_close_capacity(p_id uuid)returns void language plpgsql security definer set search_path='' as $$begin
 update public.urgent_capacity_notices set closed_at=coalesce(closed_at,now())where id=p_id and(company_id=public.urgent_actor_company()or public.urgent_is_admin());if not found then raise exception 'Annonce inaccessible';end if;
end;$$;

create table public.urgent_course_messages(id uuid primary key,shipment_id uuid not null references public.urgent_shipments(id),sender_id uuid not null references auth.users(id),sender_company_id uuid not null references public.companies(id),body text not null check(length(trim(body))between 1 and 2000),created_at timestamptz not null default now());
create table public.urgent_message_reads(user_id uuid not null references auth.users(id),shipment_id uuid not null references public.urgent_shipments(id),read_at timestamptz not null default now(),primary key(user_id,shipment_id));
create function public.urgent_can_message(p_shipment uuid)returns boolean language sql stable security definer set search_path='' as $$select auth.uid()is not null and exists(select 1 from public.urgent_shipments where id=p_shipment and accepted_offer_id is not null and(public.urgent_is_admin()or public.urgent_actor_company()in(owner_company_id,assigned_company_id)));$$;
alter table public.urgent_course_messages enable row level security;alter table public.urgent_message_reads enable row level security;
revoke all on public.urgent_course_messages,public.urgent_message_reads from public,anon,authenticated;
grant select on public.urgent_course_messages to authenticated;
create policy urgent_messages_read on public.urgent_course_messages for select to authenticated using(public.urgent_can_message(shipment_id));
create function public.urgent_send_course_message(p_id uuid,p_shipment uuid,p_body text)returns uuid language plpgsql security definer set search_path='' as $$declare previous public.urgent_course_messages;begin
 if not public.urgent_can_message(p_shipment)then raise exception 'Messagerie réservée aux parties après attribution';end if;
 if p_id is null then raise exception 'Identifiant du message requis';end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text,0));
 select * into previous from public.urgent_course_messages where id=p_id;
 if found then if previous.sender_id is distinct from auth.uid()or previous.shipment_id is distinct from p_shipment or previous.body is distinct from trim(p_body)then raise exception 'Message déjà utilisé';end if;return p_id;end if;
 if(select count(*)from public.urgent_course_messages where sender_id=auth.uid()and created_at>now()-interval'1 minute')>=10 then raise exception 'Patientez avant d’envoyer un nouveau message';end if;
 insert into public.urgent_course_messages values(p_id,p_shipment,auth.uid(),public.urgent_actor_company(),trim(p_body),now());return p_id;
end;$$;
create function public.urgent_mark_messages_read(p_shipment uuid,p_until timestamptz)returns void language plpgsql security definer set search_path='' as $$begin
 if not public.urgent_can_message(p_shipment)then raise exception 'Course inaccessible';end if;
 insert into public.urgent_message_reads values(auth.uid(),p_shipment,least(coalesce(p_until,now()),now()))on conflict(user_id,shipment_id)do update set read_at=greatest(public.urgent_message_reads.read_at,excluded.read_at);
end;$$;
create function public.urgent_dashboard()returns jsonb language plpgsql stable security definer set search_path='' as $$declare company uuid:=public.urgent_actor_company();begin
 if auth.uid()is null or company is null then raise exception 'Connexion professionnelle requise';end if;
 return jsonb_build_object('open_requests',(select count(*)from public.urgent_shipments where owner_company_id=company and status='open'and archived_at is null),'received_offers',(select count(*)from public.urgent_offers o join public.urgent_shipments s on s.id=o.shipment_id where s.owner_company_id=company and o.status='submitted'and s.status='open'and s.archived_at is null),'active_missions',(select count(*)from public.urgent_shipments where company in(owner_company_id,assigned_company_id)and status in('assigned','heading_pickup','at_pickup','loaded','delivery_reported')and archived_at is null),'unread_messages',(select count(*)from public.urgent_course_messages m join public.urgent_shipments s on s.id=m.shipment_id left join public.urgent_message_reads r on r.shipment_id=m.shipment_id and r.user_id=auth.uid()where company in(s.owner_company_id,s.assigned_company_id)and m.sender_id<>auth.uid()and m.created_at>coalesce(r.read_at,'epoch'::timestamptz)),'carrier_ready',case when public.urgent_actor_role()='carrier'then public.urgent_carrier_ready(company)else null end);
end;$$;

-- Demande de devis sans création de compte ou contrat de consommation en ligne.
create table public.urgent_quote_requests(id uuid primary key,payload jsonb not null,payload_hash text not null,created_at timestamptz not null default now(),status text not null default 'new'check(status in('new','contacted','quoted','closed')),updated_at timestamptz not null default now(),admin_note text not null default ''check(length(admin_note)<=2000));
create table public.urgent_quote_limits(key text primary key,hits integer not null,window_start timestamptz not null);
alter table public.urgent_quote_requests enable row level security;alter table public.urgent_quote_limits enable row level security;
revoke all on public.urgent_quote_requests,public.urgent_quote_limits from public,anon,authenticated;
grant select on public.urgent_quote_requests to authenticated;
create policy urgent_quotes_admin on public.urgent_quote_requests for select to authenticated using(public.urgent_is_admin());
create function public.urgent_record_quote(p_id uuid,p_payload jsonb,p_hash text,p_ip_key text,p_email_key text)returns uuid language plpgsql security definer set search_path='' as $$declare previous public.urgent_quote_requests;k text;begin
 if p_id is null or p_hash!~'^[0-9a-f]{64}$'or p_ip_key!~'^[0-9a-f]{64}$'or p_email_key!~'^[0-9a-f]{64}$'or p_hash is null or p_ip_key is null or p_email_key is null then raise exception 'Demande invalide';end if;
 if jsonb_typeof(p_payload)<>'object'or octet_length(p_payload::text)>20000 or coalesce(p_payload->>'name','')=''or length(p_payload->>'name')>120 or coalesce(p_payload->>'email','')!~'^[^[:space:]@<>]+@[^[:space:]@<>]+[.][^[:space:]@<>]+$'or coalesce(p_payload->>'service','')not in('express','regular','moving','bulky')or coalesce(p_payload->>'origin_postcode','')!~'^[0-9]{5}$'or coalesce(p_payload->>'destination_postcode','')!~'^[0-9]{5}$'or coalesce(p_payload->>'privacy','')<>'true'then raise exception 'Informations de devis incomplètes';end if;
 perform pg_advisory_xact_lock(hashtextextended(p_id::text,1));select * into previous from public.urgent_quote_requests where id=p_id;
 if found then if previous.payload_hash<>p_hash then raise exception 'Référence déjà utilisée';end if;return p_id;end if;
 for k in select x from unnest(array['ip/'||p_ip_key,'email/'||p_email_key,'global'])x order by x loop
  insert into public.urgent_quote_limits values(k,1,date_trunc('hour',now()))on conflict(key)do update set hits=case when urgent_quote_limits.window_start<date_trunc('hour',now())then 1 else urgent_quote_limits.hits+1 end,window_start=date_trunc('hour',now());
  if(select hits from public.urgent_quote_limits where key=k)>(case when k='global'then 100 else 5 end)then raise exception 'rate_limit';end if;
 end loop;
 delete from public.urgent_quote_limits where window_start<now()-interval'2 days';
 insert into public.urgent_quote_requests(id,payload,payload_hash)values(p_id,p_payload,p_hash);return p_id;
end;$$;
create function public.urgent_review_quote(p_id uuid,p_status text,p_note text)returns void language plpgsql security definer set search_path='' as $$begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 update public.urgent_quote_requests set status=p_status,admin_note=coalesce(p_note,''),updated_at=now()where id=p_id;if not found then raise exception 'Demande introuvable';end if;
end;$$;

create table public.urgent_platform_notifications(id uuid primary key default gen_random_uuid(),dedupe text not null unique,kind text not null check(kind in('course','message','quote')),shipment_id uuid references public.urgent_shipments(id),revision integer,recipient_id uuid references auth.users(id),quote_id uuid references public.urgent_quote_requests(id),created_at timestamptz not null default now(),status text not null default'pending'check(status in('pending','sent','failed')),attempts integer not null default 0,next_attempt_at timestamptz not null default now(),lease_token uuid,locked_until timestamptz,sent_at timestamptz,provider_id text,last_error_code text);
alter table public.urgent_platform_notifications enable row level security;
revoke all on public.urgent_platform_notifications from public,anon,authenticated;
create index urgent_platform_notifications_pending on public.urgent_platform_notifications(next_attempt_at)where status='pending';
create function public.urgent_queue_platform_notification()returns trigger language plpgsql security definer set search_path='' as $$declare s public.urgent_shipments;begin
 if tg_table_name='urgent_quote_requests'then
  insert into public.urgent_platform_notifications(dedupe,kind,quote_id)values('quote/'||new.id,'quote',new.id)on conflict(dedupe)do nothing;return new;
 elsif tg_table_name='urgent_course_messages'then
  select * into s from public.urgent_shipments where id=new.shipment_id;if s.is_test then return new;end if;
  insert into public.urgent_platform_notifications(dedupe,kind,shipment_id,recipient_id)
  select 'message/'||new.id||'/'||p.id,'message',s.id,p.id from public.profiles p where p.company_id in(s.owner_company_id,s.assigned_company_id)and p.id<>new.sender_id and p.role in('client','carrier')on conflict(dedupe)do nothing;return new;
 end if;
 select * into s from public.urgent_shipments where id=new.id;
 if s.is_test or s.status<>'open'or s.archived_at is not null or s.pickup<=now()then return new;end if;
 perform pg_advisory_xact_lock(hashtextextended('urgent_course_alert_daily',0));
 insert into public.urgent_platform_notifications(dedupe,kind,shipment_id,revision,recipient_id)
 select 'course/'||s.id||'/'||s.revision||'/'||p.user_id,'course',s.id,s.revision,p.user_id
 from public.urgent_carrier_alert_preferences p join public.profiles profile on profile.id=p.user_id left join public.urgent_transport_details t on t.shipment_id=s.id
 where p.enabled and profile.role='carrier'and profile.company_id<>s.owner_company_id and public.urgent_carrier_ready(profile.company_id)
 and(cardinality(p.vehicles)=0 or s.vehicle=any(p.vehicles))
 and(cardinality(p.origin_departments)=0 or public.urgent_department(t.origin_postcode)=any(p.origin_departments))
 and(cardinality(p.destination_departments)=0 or public.urgent_department(t.destination_postcode)=any(p.destination_departments))
 and(select count(*)from public.urgent_platform_notifications n where n.recipient_id=p.user_id and n.kind='course'and n.created_at>=(date_trunc('day',now()at time zone'Europe/Paris')at time zone'Europe/Paris')and n.status in('sent','pending'))<10
 on conflict(dedupe)do nothing;return new;
end;$$;
create constraint trigger urgent_queue_course_alert after insert or update on public.urgent_shipments deferrable initially deferred for each row execute function public.urgent_queue_platform_notification();
create trigger urgent_queue_private_message after insert on public.urgent_course_messages for each row execute function public.urgent_queue_platform_notification();
create trigger urgent_queue_quote after insert on public.urgent_quote_requests for each row execute function public.urgent_queue_platform_notification();
revoke all on function public.urgent_queue_platform_notification()from public,anon,authenticated;

create function public.urgent_claim_platform_notifications()returns table(alert_id uuid,lease_token uuid,kind text,recipient_email text,recipient_confirmed boolean,recipient_allowed boolean,shipment_id uuid,origin text,destination text,pickup timestamptz,delivery_at timestamptz,vehicle text,quote_id uuid)
language plpgsql security definer set search_path='' as $$begin
 update public.urgent_platform_notifications set status='failed',last_error_code='retry_window_expired',lease_token=null,locked_until=null where status='pending'and(created_at<now()-interval'23 hours'or attempts>=8)and(locked_until is null or locked_until<now());
 return query with claimed as(
  update public.urgent_platform_notifications n set attempts=n.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval'5 minutes'
  where n.id in(select x.id from public.urgent_platform_notifications x where x.status='pending'and x.next_attempt_at<=now()and(x.locked_until is null or x.locked_until<now())order by x.created_at for update skip locked limit 3)returning n.*
 )select c.id,c.lease_token,c.kind,u.email::text,case when c.kind='quote'then true else u.email_confirmed_at is not null end,
 case when c.kind='quote'then true when c.kind='course'then s.status='open'and s.archived_at is null and not s.is_test and s.revision=c.revision and s.pickup>now()and p.enabled and profile.role='carrier'and public.urgent_carrier_ready(profile.company_id)and profile.company_id<>s.owner_company_id
 and(cardinality(p.vehicles)=0 or s.vehicle=any(p.vehicles))and(cardinality(p.origin_departments)=0 or public.urgent_department(t.origin_postcode)=any(p.origin_departments))and(cardinality(p.destination_departments)=0 or public.urgent_department(t.destination_postcode)=any(p.destination_departments))
 else not s.is_test and s.accepted_offer_id is not null and profile.company_id in(s.owner_company_id,s.assigned_company_id)end,
 c.shipment_id,s.origin,s.destination,s.pickup,s.delivery_at,s.vehicle,c.quote_id
 from claimed c left join auth.users u on u.id=c.recipient_id left join public.profiles profile on profile.id=c.recipient_id left join public.urgent_shipments s on s.id=c.shipment_id left join public.urgent_carrier_alert_preferences p on p.user_id=c.recipient_id left join public.urgent_transport_details t on t.shipment_id=c.shipment_id;
end;$$;
create function public.urgent_finish_platform_notification(p_id uuid,p_lease uuid,p_success boolean,p_provider text default null,p_error text default null)returns boolean language plpgsql security definer set search_path='' as $$declare n integer;begin
 update public.urgent_platform_notifications set status=case when p_success then'sent'when attempts>=8 or p_error in('recipient_access_changed','recipient_unconfirmed','recipient_invalid')then'failed'else'pending'end,sent_at=case when p_success then now()else null end,provider_id=case when p_success then left(p_provider,200)else null end,last_error_code=case when p_success then null else left(p_error,80)end,next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(attempts-1))::integer)),lease_token=null,locked_until=null where id=p_id and lease_token=p_lease and status='pending';get diagnostics n=row_count;return n=1;
end;$$;
revoke all on function public.urgent_claim_platform_notifications(),public.urgent_finish_platform_notification(uuid,uuid,boolean,text,text),public.urgent_record_quote(uuid,jsonb,text,text,text)from public,anon,authenticated;
grant execute on function public.urgent_claim_platform_notifications(),public.urgent_finish_platform_notification(uuid,uuid,boolean,text,text),public.urgent_record_quote(uuid,jsonb,text,text,text)to service_role;

-- Exposer seulement les fonctions publiques expressément destinées aux comptes.
revoke all on function public.urgent_publish_transport_request(text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,jsonb,boolean),public.urgent_update_transport_request(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,jsonb,boolean),public.urgent_save_alert_preferences(boolean,text[],text[],text[]),public.urgent_save_capacity(uuid,text,text,text,text,timestamptz,timestamptz,text,integer,numeric,text),public.urgent_close_capacity(uuid),public.urgent_can_message(uuid),public.urgent_send_course_message(uuid,uuid,text),public.urgent_mark_messages_read(uuid,timestamptz),public.urgent_dashboard(),public.urgent_review_quote(uuid,text,text)from public,anon;
grant execute on function public.urgent_publish_transport_request(text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,jsonb,boolean),public.urgent_update_transport_request(uuid,integer,text,text,timestamptz,text,integer,numeric,text,text,text,timestamptz,jsonb,boolean),public.urgent_save_alert_preferences(boolean,text[],text[],text[]),public.urgent_save_capacity(uuid,text,text,text,text,timestamptz,timestamptz,text,integer,numeric,text),public.urgent_close_capacity(uuid),public.urgent_can_message(uuid),public.urgent_send_course_message(uuid,uuid,text),public.urgent_mark_messages_read(uuid,timestamptz),public.urgent_dashboard(),public.urgent_review_quote(uuid,text,text)to authenticated;
create function public.urgent_platform_services_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'version','20261030-services-france','area','France','consumer_quotes',true,'alerts',true,'messages',true,'capacities',true,'transport_details',true);$$;
revoke all on function public.urgent_platform_services_policy()from public;
grant execute on function public.urgent_platform_services_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_platform_services_policy()as nouveaux_services;

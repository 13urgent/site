-- Navigation, pièces de mission privées et notifications des donneurs d'ordre.
-- Prérequis : migrations pilote, incidents et rangement des courses.
begin;
alter table public.urgent_shipment_private add column pickup_address text not null default '' check(length(pickup_address)<=500);
alter table public.urgent_shipment_private add column delivery_address text not null default '' check(length(delivery_address)<=500);

create function public.urgent_save_mission_addresses(p_shipment uuid,p_pickup text,p_delivery text)returns void
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;contact public.urgent_shipment_private;
begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if auth.uid()is null or not found or s.owner_company_id is distinct from public.urgent_actor_company()then raise exception 'Entreprise propriétaire requise';end if;
 if s.archived_at is not null or s.status not in('open','assigned','heading_pickup','at_pickup','loaded')then raise exception 'Les adresses ne peuvent plus être renseignées à cette étape';end if;
 if p_pickup is null or p_delivery is null or length(trim(p_pickup))not between 5 and 500 or length(trim(p_delivery))not between 5 and 500 then raise exception 'Renseignez les deux adresses complètes (5 à 500 caractères)';end if;
 select * into contact from public.urgent_shipment_private where shipment_id=s.id;
 if s.status not in('open','assigned')and((contact.pickup_address<>''and contact.pickup_address<>trim(p_pickup))or(contact.delivery_address<>''and contact.delivery_address<>trim(p_delivery)))then raise exception 'Les adresses existantes sont figées après le départ vers l’enlèvement';end if;
 update public.urgent_shipment_private set pickup_address=trim(p_pickup),delivery_address=trim(p_delivery)
 where shipment_id=s.id and(pickup_address is distinct from trim(p_pickup)or delivery_address is distinct from trim(p_delivery));
 if found then insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'mission_addresses_updated');end if;
end;$$;
revoke all on function public.urgent_save_mission_addresses(uuid,text,text)from public,anon;
grant execute on function public.urgent_save_mission_addresses(uuid,text,text)to authenticated;

create table public.urgent_mission_files(
 id uuid primary key,
 shipment_id uuid not null references public.urgent_shipments(id),
 uploaded_by uuid not null references auth.users(id),
 kind text not null check(kind in('goods','reservation','waybill')),
 caption text not null default '' check(length(caption)<=2000),
 storage_path text not null unique,
 original_filename text not null check(length(original_filename)between 1 and 250),
 mime_type text not null check(mime_type in('image/jpeg','image/png','application/pdf')),
 byte_size bigint not null check(byte_size between 1 and 10485760),
 created_at timestamptz not null default now()
);
create index urgent_mission_files_shipment on public.urgent_mission_files(shipment_id,created_at,id);
alter table public.urgent_mission_files enable row level security;
revoke all on public.urgent_mission_files from public,anon,authenticated;
grant select on public.urgent_mission_files to authenticated;
create policy urgent_mission_files_read on public.urgent_mission_files for select to authenticated using(public.urgent_is_party(shipment_id));

create function public.urgent_mission_can_upload(p_shipment uuid)returns boolean
language sql stable security definer set search_path='' as $$
 select coalesce(public.urgent_actor_role()='carrier'and exists(select 1 from public.urgent_shipments s
 where s.id=p_shipment and s.assigned_company_id=public.urgent_actor_company()and s.accepted_offer_id is not null
 and s.status not in('open','cancelled')and s.archived_at is null),false);
$$;
revoke all on function public.urgent_mission_can_upload(uuid)from public,anon;
grant execute on function public.urgent_mission_can_upload(uuid)to authenticated;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
 values('urgent-mission-files','urgent-mission-files',false,10485760,array['image/jpeg','image/png','application/pdf'])
on conflict(id)do update set public=false,file_size_limit=10485760,allowed_mime_types=array['image/jpeg','image/png','application/pdf'];
create function public.urgent_mission_storage_upload(p_name text)returns boolean
language sql stable security definer set search_path='' as $$
 select case when p_name~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|pdf)$'
 then public.urgent_mission_can_upload(split_part(p_name,'/',1)::uuid)else false end;
$$;
revoke all on function public.urgent_mission_storage_upload(text)from public,anon;
grant execute on function public.urgent_mission_storage_upload(text)to authenticated;
create policy urgent_mission_storage_insert on storage.objects for insert to authenticated
 with check(bucket_id='urgent-mission-files'and public.urgent_mission_storage_upload(name));
create policy urgent_mission_storage_insert_boundary on storage.objects as restrictive for insert to authenticated
 with check(bucket_id<>'urgent-mission-files'or public.urgent_mission_storage_upload(name));
create policy urgent_mission_storage_read on storage.objects for select to authenticated
 using(bucket_id='urgent-mission-files'and exists(select 1 from public.urgent_mission_files f where f.storage_path=name));
create policy urgent_mission_storage_read_boundary on storage.objects as restrictive for select to authenticated
 using(bucket_id<>'urgent-mission-files'or exists(select 1 from public.urgent_mission_files f where f.storage_path=name));
create policy urgent_mission_storage_no_update on storage.objects as restrictive for update to authenticated
 using(bucket_id<>'urgent-mission-files')with check(bucket_id<>'urgent-mission-files');
create policy urgent_mission_storage_no_delete on storage.objects as restrictive for delete to authenticated using(bucket_id<>'urgent-mission-files');
create policy urgent_mission_storage_no_anon on storage.objects as restrictive for all to anon
 using(bucket_id<>'urgent-mission-files')with check(bucket_id<>'urgent-mission-files');

create function public.urgent_add_mission_file(p_shipment uuid,p_file uuid,p_kind text,p_caption text,p_filename text,p_path text)returns uuid
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;prior public.urgent_mission_files;object_data jsonb;mime text;bytes bigint;
begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if auth.uid()is null or not found or public.urgent_actor_role()is distinct from 'carrier'or s.assigned_company_id is distinct from public.urgent_actor_company()then raise exception 'Transporteur attribué requis';end if;
 if p_file is null or p_kind is null or p_kind not in('goods','reservation','waybill')or p_caption is null or length(p_caption)>2000 or p_filename is null or length(trim(p_filename))not between 1 and 250 then raise exception 'Informations du fichier invalides';end if;
 if p_kind='reservation'and length(trim(p_caption))<10 then raise exception 'Décrivez précisément les réserves (10 caractères minimum)';end if;
 select * into prior from public.urgent_mission_files where id=p_file;
 if found then
  if prior.shipment_id=s.id and prior.uploaded_by=auth.uid()and prior.storage_path=p_path and prior.kind=p_kind and prior.caption=trim(p_caption)and prior.original_filename=trim(p_filename)then return prior.id;end if;
  raise exception 'Référence de fichier déjà utilisée';
 end if;
 if not public.urgent_mission_can_upload(s.id)then raise exception 'Cette course ne permet pas le dépôt de pièces';end if;
 if p_path is null or not public.urgent_mission_storage_upload(p_path)or split_part(p_path,'/',1)<>s.id::text or split_part(split_part(p_path,'/',2),'.',1)<>p_file::text then raise exception 'Chemin de fichier invalide';end if;
 select to_jsonb(o)into object_data from storage.objects o where o.bucket_id='urgent-mission-files'and o.name=p_path;
 if object_data is null or coalesce(object_data->>'owner_id',object_data->>'owner')is distinct from auth.uid()::text then raise exception 'Fichier non reçu pour ce compte';end if;
 mime:=object_data->'metadata'->>'mimetype';
 if coalesce(object_data->'metadata'->>'size','')!~'^[0-9]{1,8}$'then raise exception 'Taille de fichier non vérifiée';end if;
 bytes:=(object_data->'metadata'->>'size')::bigint;
 if bytes not between 1 and 10485760 or mime is null or mime not in('image/jpeg','image/png','application/pdf')or right(p_path,4)is distinct from(case mime when 'image/jpeg'then '.jpg'when 'image/png'then '.png'else '.pdf'end)then raise exception 'Format ou taille non autorisé';end if;
 insert into public.urgent_mission_files(id,shipment_id,uploaded_by,kind,caption,storage_path,original_filename,mime_type,byte_size)
 values(p_file,s.id,auth.uid(),p_kind,trim(p_caption),p_path,trim(p_filename),mime,bytes);
 if p_kind='reservation'and not exists(select 1 from public.urgent_shipment_incidents where shipment_id=s.id and reported_by=auth.uid()and status='open')then
  perform public.urgent_report_incident(s.id,trim(p_caption));
 end if;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'mission_file_added');
 return p_file;
end;$$;
revoke all on function public.urgent_add_mission_file(uuid,uuid,text,text,text,text)from public,anon;
grant execute on function public.urgent_add_mission_file(uuid,uuid,text,text,text,text)to authenticated;

-- Les notifications sont destinées au vrai créateur de la course, jamais à une adresse libre.
create table public.urgent_mission_notifications(
 id uuid primary key default gen_random_uuid(),dedupe_key text not null unique,
 shipment_id uuid not null references public.urgent_shipments(id),recipient_id uuid not null references auth.users(id),
 owner_company_id uuid not null references public.companies(id),origin text not null,destination text not null,
 event_type text not null check(event_type in('loaded','delivery_reported','goods','reservation','waybill')),filename text not null default '',
 created_at timestamptz not null default now(),status text not null default 'pending'check(status in('pending','sent','failed')),
 attempts integer not null default 0 check(attempts between 0 and 8),next_attempt_at timestamptz not null default now(),
 lease_token uuid,locked_until timestamptz,sent_at timestamptz,provider_id text,last_error_code text
);
alter table public.urgent_mission_notifications enable row level security;
revoke all on public.urgent_mission_notifications from public,anon,authenticated;
create index urgent_mission_notifications_pending on public.urgent_mission_notifications(next_attempt_at)where status='pending';
create function public.urgent_queue_mission_notice()returns trigger language plpgsql security definer set search_path='' as $$
declare sid uuid;kind text;job_key text;filename text:='';
begin
 if tg_table_name='urgent_shipment_events'then
  if new.event_type not in('loaded','delivery_reported')then return new;end if;
  sid:=new.shipment_id;kind:=new.event_type;job_key:='event/'||new.id::text;
 else sid:=new.shipment_id;kind:=new.kind;filename:=new.original_filename;job_key:='file/'||new.id::text;
 end if;
 insert into public.urgent_mission_notifications(dedupe_key,shipment_id,recipient_id,owner_company_id,origin,destination,event_type,filename)
 select job_key,s.id,s.owner_id,s.owner_company_id,s.origin,s.destination,kind,filename from public.urgent_shipments s
 where s.id=sid and not s.is_test and s.accepted_offer_id is not null on conflict(dedupe_key)do nothing;
 return new;
end;$$;
revoke all on function public.urgent_queue_mission_notice()from public,anon,authenticated;
create trigger urgent_queue_mission_status after insert on public.urgent_shipment_events for each row execute function public.urgent_queue_mission_notice();
create trigger urgent_queue_mission_file after insert on public.urgent_mission_files for each row execute function public.urgent_queue_mission_notice();

create function public.urgent_claim_mission_notifications()
returns table(alert_id uuid,lease_token uuid,shipment_id uuid,recipient_email text,recipient_confirmed boolean,recipient_allowed boolean,origin text,destination text,event_type text,filename text,recorded_at timestamptz)
language plpgsql security definer set search_path='' as $$
begin
 update public.urgent_mission_notifications a set status='failed',last_error_code=case when a.attempts>=8 then 'attempts_exhausted'else 'delivery_window_expired'end
 where a.status='pending'and(a.attempts>=8 or a.created_at<now()-interval '23 hours')and coalesce(a.locked_until,'-infinity'::timestamptz)<=now();
 return query with due as(
  select a.id from public.urgent_mission_notifications a where a.status='pending'and a.attempts<8 and a.next_attempt_at<=now()and coalesce(a.locked_until,'-infinity'::timestamptz)<=now()
  order by a.created_at,a.id limit 3 for update skip locked
 ),claimed as(
  update public.urgent_mission_notifications a set attempts=a.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval '5 minutes'from due where a.id=due.id returning a.*
 )select a.id,a.lease_token,a.shipment_id,u.email::text,u.email_confirmed_at is not null,coalesce(p.company_id=a.owner_company_id,false),a.origin,a.destination,a.event_type,a.filename,a.created_at
 from claimed a join auth.users u on u.id=a.recipient_id left join public.profiles p on p.id=a.recipient_id;
end;$$;
create function public.urgent_finish_mission_notification(p_alert_id uuid,p_lease_token uuid,p_success boolean,p_provider_id text default null,p_error_code text default null)returns boolean
language plpgsql security definer set search_path='' as $$
declare changed integer;
begin
 update public.urgent_mission_notifications a set status=case when p_success then 'sent'when a.attempts>=8 then 'failed'else 'pending'end,
 sent_at=case when p_success then now()else null end,provider_id=case when p_success then left(p_provider_id,200)else null end,
 last_error_code=case when p_success then null else left(coalesce(p_error_code,'send_error'),80)end,
 next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(a.attempts-1))::integer)),lease_token=null,locked_until=null
 where a.id=p_alert_id and a.lease_token=p_lease_token and a.status='pending';get diagnostics changed=row_count;return changed=1;
end;$$;
revoke all on function public.urgent_claim_mission_notifications(),public.urgent_finish_mission_notification(uuid,uuid,boolean,text,text)from public,anon,authenticated;
grant execute on function public.urgent_claim_mission_notifications(),public.urgent_finish_mission_notification(uuid,uuid,boolean,text,text)to service_role;
create function public.urgent_mobile_mission_policy()returns jsonb language sql stable set search_path='' as $$
 select jsonb_build_object('enabled',true,'private_files',true,'addresses',true,'version','20261029-mobile-missions');
$$;
grant execute on function public.urgent_mobile_mission_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_mobile_mission_policy()as application_mobile;

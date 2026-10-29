-- Alerte interne pour chaque nouvelle pièce : aucun envoi réseau dans le dépôt.
-- Aucun rattrapage des pièces existantes et aucune modification de leurs validations.
begin;
-- Dépôt facultatif du Kbis par un donneur d'ordre : mêmes frontières privées.
-- Les exigences des quatre catégories transporteur restent inchangées.
drop policy if exists urgent_document_insert_file_boundary on public.carrier_documents;
create policy urgent_document_insert_file_boundary on public.carrier_documents as restrictive
for insert to authenticated with check (
 public.urgent_actor_role()in('carrier','client')
 and(public.urgent_actor_role()='carrier'or document_type::text='registration')
 and company_id=public.urgent_actor_company()
 and review_status='pending'and reviewed_by is null and reviewed_at is null
 and split_part(storage_path,'/',1)=company_id::text
 and position('/'in storage_path)>0 and length(storage_path)>length(company_id::text)+1
 and storage_path!~'(^|/)\.{1,2}(/|$)'and position(chr(92)in storage_path)=0
 and exists(select 1 from storage.objects o where o.bucket_id='carrier-documents'and o.name=storage_path)
);
create policy urgent_client_document_insert on public.carrier_documents for insert to authenticated
 with check(public.urgent_actor_role()='client'and company_id=public.urgent_actor_company()and document_type::text='registration'and review_status='pending'and reviewed_by is null and reviewed_at is null);
create policy urgent_client_document_read on public.carrier_documents for select to authenticated
 using(public.urgent_actor_role()='client'and company_id=public.urgent_actor_company());
create policy urgent_client_document_storage_insert on storage.objects for insert to authenticated
 with check(bucket_id='carrier-documents'and public.urgent_actor_role()='client'and split_part(name,'/',1)=public.urgent_actor_company()::text
 and length(name)>length(public.urgent_actor_company()::text)+1 and name!~'(^|/)\.{1,2}(/|$)'and position(chr(92)in name)=0);
create policy urgent_client_document_storage_read on storage.objects for select to authenticated
 using(bucket_id='carrier-documents'and public.urgent_actor_role()='client'and split_part(name,'/',1)=public.urgent_actor_company()::text);

create table public.urgent_document_alerts (
 id uuid primary key default gen_random_uuid(),
 document_id uuid not null unique references public.carrier_documents(id) on delete cascade,
 user_id uuid not null references public.profiles(id) on delete cascade,
 company_id uuid not null references public.companies(id) on delete cascade,
 account_type text not null check(account_type in ('client','carrier')),
 company_name text not null,
 document_type text not null,
 original_filename text not null,
 created_at timestamptz not null default now(),
 status text not null default 'pending' check(status in ('pending','sent','failed')),
 attempts integer not null default 0 check(attempts between 0 and 8),
 next_attempt_at timestamptz not null default now(),
 lease_token uuid,
 locked_until timestamptz,
 sent_at timestamptz,
 provider_id text,
 last_error_code text
);
alter table public.urgent_document_alerts enable row level security;
revoke all on public.urgent_document_alerts from public,anon,authenticated;
create index urgent_document_alerts_pending on public.urgent_document_alerts(next_attempt_at) where status='pending';

create function public.urgent_queue_document_alert()returns trigger
language plpgsql security definer set search_path='' as $$
begin
 insert into public.urgent_document_alerts(document_id,user_id,company_id,account_type,company_name,document_type,original_filename)
 select new.id,p.id,new.company_id,p.role::text,c.name::text,new.document_type::text,coalesce(new.original_filename,'Document')
 from public.profiles p join public.companies c on c.id=p.company_id
 where p.id=auth.uid() and p.company_id=new.company_id and p.role::text in('client','carrier')
 on conflict(document_id)do nothing;
 return new;
end;$$;
revoke all on function public.urgent_queue_document_alert()from public,anon,authenticated;
create trigger urgent_queue_document_alert after insert on public.carrier_documents
for each row execute function public.urgent_queue_document_alert();

create function public.urgent_claim_document_alerts()
returns table(alert_id uuid,lease_token uuid,document_id uuid,user_id uuid,company_id uuid,company_name text,account_type text,email text,document_type text,original_filename text,uploaded_at timestamptz)
language plpgsql security definer set search_path='' as $$
begin
 update public.urgent_document_alerts a set status='failed',last_error_code=case when a.attempts>=8 then 'attempts_exhausted'else 'delivery_window_expired'end
 where a.status='pending'and(a.attempts>=8 or a.created_at<now()-interval '23 hours')and coalesce(a.locked_until,'-infinity'::timestamptz)<=now();
 return query
 with due as(
  select a.id from public.urgent_document_alerts a
  where a.status='pending'and a.attempts<8 and a.next_attempt_at<=now()and coalesce(a.locked_until,'-infinity'::timestamptz)<=now()
  order by a.created_at,a.id limit 3 for update skip locked
 ),claimed as(
  update public.urgent_document_alerts a set attempts=a.attempts+1,lease_token=gen_random_uuid(),locked_until=now()+interval '5 minutes'
  from due where a.id=due.id returning a.*
 )
 select a.id,a.lease_token,a.document_id,a.user_id,a.company_id,a.company_name,a.account_type,u.email::text,a.document_type,a.original_filename,a.created_at
 from claimed a join auth.users u on u.id=a.user_id;
end;$$;

create function public.urgent_finish_document_alert(p_alert_id uuid,p_lease_token uuid,p_success boolean,p_provider_id text default null,p_error_code text default null)
returns boolean language plpgsql security definer set search_path='' as $$
declare changed integer;
begin
 update public.urgent_document_alerts a set
 status=case when p_success then 'sent'when a.attempts>=8 then 'failed'else 'pending'end,
 sent_at=case when p_success then now()else null end,
 provider_id=case when p_success then left(p_provider_id,200)else null end,
 last_error_code=case when p_success then null else left(coalesce(p_error_code,'send_error'),80)end,
 next_attempt_at=now()+make_interval(secs=>least(3600,60*(2^(a.attempts-1))::integer)),
 lease_token=null,locked_until=null
 where a.id=p_alert_id and a.lease_token=p_lease_token and a.status='pending';
 get diagnostics changed=row_count;
 return changed=1;
end;$$;
revoke all on function public.urgent_claim_document_alerts(),public.urgent_finish_document_alert(uuid,uuid,boolean,text,text)from public,anon,authenticated;
grant execute on function public.urgent_claim_document_alerts(),public.urgent_finish_document_alert(uuid,uuid,boolean,text,text)to service_role;

-- Indique uniquement la disponibilité de la file, pas la délivrabilité des e-mails.
create function public.urgent_document_alert_policy()returns jsonb language sql stable set search_path='' as $$
 select jsonb_build_object('enabled',true,'client_upload',true,'version','20261029-document-alerts');
$$;
grant execute on function public.urgent_document_alert_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_document_alert_policy()as alertes_documents;

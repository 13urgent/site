-- Renouvellement des quatre justificatifs six mois après dépôt, ou expiration plus tôt.
begin;
create function public.urgent_document_renewal_due(p_created timestamptz)returns timestamptz
language sql immutable set search_path='' as $$
 select ((p_created at time zone 'Europe/Paris')::date+interval '6 months') at time zone 'Europe/Paris';
$$;
revoke all on function public.urgent_document_renewal_due(timestamptz) from public,anon,authenticated;

-- Un ancien fichier ne peut pas être rajeuni en changeant sa date ou son approbation.
create function public.urgent_document_received_at()returns trigger language plpgsql set search_path='' as $$
begin
 if tg_op='INSERT' then new.created_at:=now();
 elsif new.created_at is distinct from old.created_at then raise exception 'La date de dépôt ne peut pas être modifiée';end if;
 return new;
end;$$;
revoke all on function public.urgent_document_received_at() from public,anon,authenticated;
create trigger urgent_document_received_at before insert or update of created_at on public.carrier_documents
for each row execute function public.urgent_document_received_at();

create or replace function public.urgent_carrier_documents_ready(p_company uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_business_access a where a.company_id=p_company and a.registry_checked and a.pilot_enabled)
 and not exists(
  select 1 from (values('registration'),('transport_licence'),('insurance_rc'),('insurance_goods')) required(kind)
  where not coalesce((select d.review_status='approved'
   and (required.kind='registration' or d.expires_on is not null)
   and (d.expires_on is null or d.expires_on>=(now() at time zone 'Europe/Paris')::date)
   and d.created_at<=now() and public.urgent_document_renewal_due(d.created_at)>now()
   from public.carrier_documents d where d.company_id=p_company and d.document_type=required.kind
   order by d.created_at desc,d.id desc limit 1),false)
 );
$$;

create or replace function public.urgent_document_checklist(p_company uuid)
returns table(document_type text,document_id uuid,review_status text,expires_on date,reason text)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() and p_company is distinct from public.urgent_actor_company() then raise exception 'Accès au dossier non autorisé';end if;
 return query select required.kind,d.id,d.review_status::text,d.expires_on,
 case when d.id is null then 'missing'
 when d.review_status is distinct from 'approved' then 'not_approved'
 when required.kind<>'registration' and d.expires_on is null then 'expiry_missing'
 when d.expires_on<(now() at time zone 'Europe/Paris')::date then 'expired'
 when d.created_at is null or d.created_at>now() or public.urgent_document_renewal_due(d.created_at)<=now() then 'renewal_due'
 else 'valid' end
 from (values('registration'),('transport_licence'),('insurance_rc'),('insurance_goods')) required(kind)
 left join lateral(select cd.id,cd.review_status,cd.expires_on,cd.created_at from public.carrier_documents cd
 where cd.company_id=p_company and cd.document_type=required.kind order by cd.created_at desc,cd.id desc limit 1)d on true;
end;$$;

revoke all on function public.urgent_carrier_documents_ready(uuid) from public,anon,authenticated;
-- L'annuaire n'est plus limité aux cent premiers dossiers.
create or replace function public.urgent_pilot_directory()returns table(company_id uuid,company_name text,account_role text,declared_siret text,requested_plan text,pilot_enabled boolean,pilot_plan text,carrier_ready boolean)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 return query select c.id,c.name::text,p.role::text,u.raw_user_meta_data->>'business_siret',u.raw_user_meta_data->>'subscription_plan_request',coalesce(a.pilot_enabled and a.registry_checked,false),a.plan,public.urgent_carrier_ready(c.id)
 from public.companies c join public.profiles p on p.company_id=c.id join auth.users u on u.id=p.id
 left join public.urgent_business_access a on a.company_id=c.id
 where p.role in ('client','carrier') order by c.name,c.id,p.id;
end;$$;
revoke all on function public.urgent_document_checklist(uuid),public.urgent_pilot_directory() from public,anon;
grant execute on function public.urgent_document_checklist(uuid),public.urgent_pilot_directory() to authenticated;
create function public.urgent_document_renewal_policy()returns jsonb language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'months',6);$$;
grant execute on function public.urgent_document_renewal_policy() to anon,authenticated;
commit;

select public.urgent_document_renewal_policy()as actualisation_documentaire;

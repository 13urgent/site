-- Suppression de connexions avec conservation des identifiants d'archives.
-- L'installation ne ferme aucun compte : la commande de clôture est SQL-owner only.
begin;
create table if not exists public.urgent_account_cleanup_runs(
 id uuid primary key,parameters jsonb not null,result jsonb,created_at timestamptz not null default now()
);
create table if not exists public.urgent_closed_accounts(
 user_id uuid primary key references auth.users(id),run_id uuid not null references public.urgent_account_cleanup_runs(id),
 original_email text not null,company_id uuid,profile_snapshot jsonb,
 closed_by uuid not null references auth.users(id),closed_at timestamptz not null default now(),reason text not null
);
alter table public.urgent_account_cleanup_runs enable row level security;
alter table public.urgent_closed_accounts enable row level security;
revoke all on public.urgent_account_cleanup_runs,public.urgent_closed_accounts from public,anon,authenticated,service_role;

create or replace function public.urgent_account_is_active(p_user uuid)returns boolean
language sql stable security definer set search_path='' as $$
 select p_user is not null and exists(select 1 from auth.users u where u.id=p_user
  and u.deleted_at is null and(u.banned_until is null or u.banned_until<=now()))
 and not exists(select 1 from public.urgent_closed_accounts c where c.user_id=p_user);
$$;
revoke all on function public.urgent_account_is_active(uuid)from public,anon;
grant execute on function public.urgent_account_is_active(uuid)to authenticated;
create or replace function public.urgent_actor_role()returns text
language sql stable security definer set search_path='' as $$
 select role::text from public.profiles where id=auth.uid()and public.urgent_account_is_active(auth.uid());
$$;
create or replace function public.urgent_actor_company()returns uuid
language sql stable security definer set search_path='' as $$
 select company_id from public.profiles where id=auth.uid()and public.urgent_account_is_active(auth.uid());
$$;

create or replace view public.urgent_active_profiles with(security_invoker=true)as
 select p.* from public.profiles p where public.urgent_account_is_active(p.id);
revoke all on public.urgent_active_profiles from public,anon,authenticated;
grant select on public.urgent_active_profiles to authenticated;
create or replace function public.urgent_company_has_active_account(p_company uuid)returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_active_profiles p where p.company_id=p_company);
$$;
revoke all on function public.urgent_company_has_active_account(uuid)from public,anon;
grant execute on function public.urgent_company_has_active_account(uuid)to authenticated;

-- Les JWT déjà délivrés ne donnent plus accès aux données après clôture.
do $$declare target record;begin
 for target in select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where c.relkind='r'and c.relrowsecurity and(n.nspname='public'or(n.nspname='storage'and c.relname='objects'))loop
  execute format('drop policy if exists urgent_active_session_boundary on %I.%I',target.nspname,target.relname);
  execute format('create policy urgent_active_session_boundary on %I.%I as restrictive for all to authenticated using(public.urgent_account_is_active(auth.uid()))with check(public.urgent_account_is_active(auth.uid()))',target.nspname,target.relname);
 end loop;
end;$$;
drop policy if exists urgent_profiles_active_rows on public.profiles;
create policy urgent_profiles_active_rows on public.profiles as restrictive for select to authenticated
 using(public.urgent_account_is_active(id));
drop policy if exists urgent_companies_active_rows on public.companies;
create policy urgent_companies_active_rows on public.companies as restrictive for select to authenticated
 using(public.urgent_company_has_active_account(id));

-- Les annuaires métier ignorent les comptes clos ; leurs lignes historiques restent conservées.
do $$declare signature text;definition text;begin
 foreach signature in array array['public.urgent_pilot_directory()',
  'public.urgent_internal_premium_directory(text,integer)',
  'public.urgent_transport_document_directory(text,integer)']loop
  if to_regprocedure(signature)is not null then
   definition:=pg_get_functiondef(signature::regprocedure);
   execute replace(definition,'public.profiles','public.urgent_active_profiles');
  end if;
 end loop;
end;$$;

create or replace function public.urgent_close_login_accounts(
 p_request uuid,p_keep text[],p_expected_remove text[],p_admin_email text,p_reason text
)returns jsonb
language plpgsql security invoker set search_path='' as $$
declare keeper_count integer;target_count integer;admin_id uuid;parameters jsonb;prior public.urgent_account_cleanup_runs;
 closure_result jsonb;auth_table text;
begin
 if p_request is null or p_keep is null or p_expected_remove is null or cardinality(p_keep)<>3 or cardinality(p_expected_remove)<1
 or length(trim(coalesce(p_reason,'')))<10 or p_admin_email is null then raise exception 'Paramètres de clôture invalides';end if;
 if exists(select 1 from unnest(p_keep||p_expected_remove)e where e is null or e<>lower(trim(e))or e!~'^[^ @]+@[^ @]+[.][^ @]+$')
 or cardinality(p_keep||p_expected_remove)<>(select count(distinct e)from unnest(p_keep||p_expected_remove)e)
 or not(p_admin_email=any(p_keep))then raise exception 'Adresses invalides, dupliquées ou listes qui se recoupent';end if;
 perform pg_advisory_xact_lock(hashtextextended('urgent-account-cleanup',0));
 parameters:=jsonb_build_object('keep',to_jsonb(p_keep),'remove',to_jsonb(p_expected_remove),'admin',p_admin_email,'reason',trim(p_reason));
 select * into prior from public.urgent_account_cleanup_runs where id=p_request;
 if found then
  if prior.parameters is distinct from parameters then raise exception 'Référence de clôture déjà utilisée pour une autre demande';end if;
  return prior.result||jsonb_build_object('reused',true);
 end if;
 lock table auth.users in share row exclusive mode;
 select count(*)into keeper_count from auth.users where deleted_at is null and lower(trim(email))=any(p_keep);
 if keeper_count<>3 or exists(select 1 from unnest(p_keep)e where(select count(*)from auth.users u where u.deleted_at is null and lower(trim(u.email))=e)<>1)then raise exception 'Les trois comptes à conserver ne sont pas tous présents : aucun compte supprimé';end if;
 select u.id into admin_id from auth.users u join public.profiles p on p.id=u.id
 where lower(trim(u.email))=p_admin_email and u.deleted_at is null and p.role::text='admin';
 if admin_id is null or not public.urgent_account_is_active(admin_id)or exists(select 1 from auth.users u where lower(trim(u.email))=any(p_keep)and not public.urgent_account_is_active(u.id))then raise exception 'Administrateur à conserver absent ou indisponible';end if;
 if exists(select 1 from auth.users where deleted_at is null and not coalesce(lower(trim(email))=any(p_keep||p_expected_remove),false))then
  raise exception 'Un compte non prévu est présent : aucun changement. Actualisez la liste avant de relancer';
 end if;
 select count(*)into target_count from auth.users where deleted_at is null and lower(trim(email))=any(p_expected_remove);
 if target_count<>cardinality(p_expected_remove)then raise exception 'La liste des comptes à retirer a changé : aucun compte supprimé';end if;

 create temporary table urgent_cleanup_targets on commit drop as
 select u.id,u.email,p.company_id,to_jsonb(p)as profile_snapshot from auth.users u
 left join public.profiles p on p.id=u.id where u.deleted_at is null and lower(trim(u.email))=any(p_expected_remove);
 insert into public.urgent_account_cleanup_runs(id,parameters)values(p_request,parameters);
 insert into public.urgent_closed_accounts(user_id,run_id,original_email,company_id,profile_snapshot,closed_by,reason)
 select id,p_request,email,company_id,profile_snapshot,admin_id,trim(p_reason)from urgent_cleanup_targets;

 -- Suppression des moyens de connexion ; aucune suppression des courses/pièces/acteurs.
 foreach auth_table in array array['refresh_tokens','one_time_tokens','mfa_factors','webauthn_credentials',
  'oauth_authorizations','sessions','flow_state','identities']loop
  if exists(select 1 from information_schema.columns where table_schema='auth'and table_name=auth_table and column_name='user_id')then
   execute format('delete from auth.%I where user_id::text in(select id::text from pg_temp.urgent_cleanup_targets)',auth_table);
  end if;
 end loop;
 update auth.users u set deleted_at=now(),banned_until=now()+interval'100 years',encrypted_password=null,
  email='closed.'||u.id::text||'@deleted.invalid',phone=null,email_change='',phone_change='',
  confirmation_token='',recovery_token='',email_change_token_current='',email_change_token_new='',phone_change_token='',
  raw_user_meta_data='{}'::jsonb,raw_app_meta_data='{}'::jsonb,updated_at=now()
 where u.id in(select id from urgent_cleanup_targets);

 update public.urgent_business_access b set pilot_enabled=false,registry_checked=false,reviewed_at=now(),reviewed_by=admin_id
 where b.company_id in(select company_id from urgent_cleanup_targets)and not public.urgent_company_has_active_account(b.company_id);
 if to_regclass('public.urgent_transport_document_access')is not null then
  insert into public.urgent_transport_document_access(company_id,enabled,reviewed_by)
  select distinct company_id,false,admin_id from urgent_cleanup_targets where company_id is not null
   and not public.urgent_company_has_active_account(company_id)
  on conflict(company_id)do update set enabled=false,reviewed_by=excluded.reviewed_by,reviewed_at=now();
 end if;
 if to_regclass('public.urgent_platform_notifications')is not null then
  update public.urgent_platform_notifications set status='failed',attempts=greatest(attempts,100),lease_token=null,locked_until=null,last_error_code='account_closed'
  where recipient_id in(select id from urgent_cleanup_targets)and status in('pending','failed');
 end if;
 select jsonb_build_object('removed_accounts',coalesce((select jsonb_agg(email order by email)from urgent_cleanup_targets),'[]'::jsonb),
  'kept_accounts',to_jsonb(p_keep),'active_accounts',(select count(*)from auth.users where deleted_at is null),
  'history_preserved',true,'reused',false)into closure_result;
 if(closure_result->>'active_accounts')::integer<>3 then raise exception 'Contrôle final incorrect : transaction annulée';end if;
 update public.urgent_account_cleanup_runs set result=closure_result where id=p_request;
 return closure_result;
end;$$;
revoke all on function public.urgent_close_login_accounts(uuid,text[],text[],text,text)from public,anon,authenticated,service_role;
commit;
notify pgrst,'reload schema';

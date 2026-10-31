-- Ouverture documentaire aux entreprises professionnelles validées.
-- N'active aucun forfait, paiement, signature électronique ni intégration externe.
begin;
do $$begin
 if to_regprocedure('public.urgent_share_transport_documents(uuid,uuid,uuid,uuid)')is null
 or to_regprocedure('public.urgent_shipper_logo_policy()')is null then
  raise exception 'Installez le partage documentaire et le logo donneur d’ordre avant cette ouverture';
 end if;
end;$$;

create or replace function public.urgent_document_prepare_enabled()returns boolean
language sql stable security definer set search_path='' as $$
 select auth.uid()is not null
 and coalesce(public.urgent_actor_role()in('client','carrier','admin'),false)
 and(public.urgent_is_admin()or(
  exists(select 1 from auth.users u where u.id=auth.uid()and u.email_confirmed_at is not null)
  and exists(select 1 from public.urgent_business_access b
   where b.company_id=public.urgent_actor_company()and b.registry_checked and b.pilot_enabled)
  and not exists(select 1 from public.urgent_transport_document_access a
   where a.company_id=public.urgent_actor_company()and not a.enabled)
 ));
$$;

create or replace function public.urgent_transport_document_directory(p_query text default '',p_offset integer default 0)
returns table(company_id uuid,company_name text,enabled boolean)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin()then raise exception 'Administration requise';end if;
 if p_query is null or length(p_query)>100 or p_offset is null or p_offset<0 or p_offset>100000 then raise exception 'Recherche invalide';end if;
 return query select c.id,c.name::text,coalesce(a.enabled,true)from public.companies c
 left join public.urgent_transport_document_access a on a.company_id=c.id
 where exists(select 1 from public.profiles p where p.company_id=c.id)and position(lower(trim(p_query))in lower(c.name))>0
 order by c.name,c.id limit 100 offset p_offset;
end;$$;

-- Remplacer uniquement le message du verrou historique, en conservant les
-- contrôles et les règles métier déjà déployés dans les deux fonctions.
do $$declare signature text;definition text;begin
 foreach signature in array array[
  'public.urgent_save_document_branding(integer,jsonb)',
  'public.urgent_save_transport_document(uuid,uuid,text,integer,text,jsonb,boolean)'
 ]loop
  definition:=pg_get_functiondef(signature::regprocedure);
  execute replace(definition,'Module documentaire : accès de test à activer par l’administration',
   'Préparation documentaire indisponible : vérifiez la confirmation de votre e-mail, la validation de votre établissement ou une suspension administrative');
 end loop;
end;$$;

create or replace function public.urgent_transport_dossier_policy()returns jsonb
language sql stable set search_path='' as $$
 select jsonb_build_object('enabled',true,'rollout','authorized_companies',
  'version','20261031-open-documents','confirmation',true,'waybill_preparation',true,
  'shipper_waybill',true,'document_delivery',true,'carrier_completion',true,
  'company_authorization_required',true,'electronic_signature',false);
$$;
revoke all on function public.urgent_document_prepare_enabled(),public.urgent_transport_document_directory(text,integer)from public,anon;
grant execute on function public.urgent_document_prepare_enabled(),public.urgent_transport_document_directory(text,integer)to authenticated;
revoke all on function public.urgent_transport_dossier_policy()from public;
grant execute on function public.urgent_transport_dossier_policy()to anon,authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_transport_dossier_policy()as ouverture_documents;

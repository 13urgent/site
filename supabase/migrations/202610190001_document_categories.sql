-- Corrige les catégories attendues par le pilote sans modifier la contrainte
-- existante et sans reclasser ou approuver automatiquement les documents.
begin;
create or replace function public.urgent_carrier_ready(p_company uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_business_access a
   where a.company_id=p_company and a.registry_checked and a.pilot_enabled)
 and not exists(
  select 1 from (values('registration'),('transport_licence'),('insurance_rc'),('insurance_goods')) required(kind)
  where not coalesce((select d.review_status='approved'
     and (d.expires_on is null or d.expires_on>=(now() at time zone 'Europe/Paris')::date)
    from public.carrier_documents d
    where d.company_id=p_company and d.document_type=required.kind
    order by d.created_at desc,d.id desc limit 1),false)
 )
$$;
revoke all on function public.urgent_carrier_ready(uuid) from public,anon;
grant execute on function public.urgent_carrier_ready(uuid) to authenticated;
commit;

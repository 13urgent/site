-- Start gratuit après une période payée : nouvelle décision administrative requise.
-- Prérequis : 202610310002_internal_premium.sql.
-- Cette migration ne modifie aucun forfait retenu, règlement ou dossier client.
begin;

create or replace function public.urgent_carrier_ready(p_company uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select public.urgent_carrier_documents_ready(p_company) and (
  not public.urgent_commercial_enabled() or (
   exists(
    select 1 from public.urgent_terms_acceptances t
    join public.urgent_commercial_config c on c.terms_version=t.version and c.id
    where t.company_id=p_company
   )
   and (
    public.urgent_internal_premium_active(p_company)
    or exists(
     select 1 from public.urgent_manual_subscriptions s
     where s.company_id=p_company and s.revoked_at is null
      and s.starts_at<=now() and s.ends_at>now()
    )
    or exists(
     select 1 from public.urgent_business_access a
     where a.company_id=p_company and a.plan='basics'
      and not exists(
       select 1 from public.urgent_manual_subscriptions s
       where s.company_id=p_company and (
        s.recorded_at>=a.reviewed_at
        or s.revoked_at>=a.reviewed_at
        or (s.revoked_at is null and s.ends_at<=now() and s.ends_at>=a.reviewed_at)
       )
      )
    )
   )
  )
 )
$$;

-- La décision Start doit être postérieure à l'enregistrement et, le cas échéant,
-- au retrait ou à la fin de chaque période payée. Une décision antérieure à la
-- fin d'une période ne prépare donc pas un retour automatique vers Start.
-- Une période future peut être précédée d'un accès Start expressément réapprouvé ;
-- sa fin exigera une nouvelle décision. Les quotas des périodes restent inchangés.
revoke all on function public.urgent_carrier_ready(uuid) from public,anon;
grant execute on function public.urgent_carrier_ready(uuid) to authenticated;

create function public.urgent_start_access_policy()
returns jsonb language sql stable set search_path='' as $$
 select jsonb_build_object(
  'enabled',true,
  'version','20261031-start-reauthorization',
  'monthly_quota',1,
  'admin_decision_required',true
 )
$$;
revoke all on function public.urgent_start_access_policy() from public;
grant execute on function public.urgent_start_access_policy() to anon,authenticated;

commit;
notify pgrst,'reload schema';
select public.urgent_start_access_policy() as forfait_start;

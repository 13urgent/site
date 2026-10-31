-- LECTURE SEULE : contrôle des comptes réels, sans changer aucun droit ni document.
-- Supabase > SQL Editor > New query > Run, puis Export > CSV pour analyse.
with comptes as (
 select u.id,u.email,u.email_confirmed_at is not null as email_confirme,
 p.role::text as role,p.company_id,c.name as entreprise,a.plan as forfait_id,
 coalesce(a.registry_checked and a.pilot_enabled,false) as etablissement_autorise,
 coalesce(not d.enabled,false) as preparation_suspendue,
 case when p.role::text='carrier' then public.urgent_carrier_documents_ready(p.company_id)end as documents_transporteur_valides,
 case when p.role::text='carrier' then public.urgent_carrier_ready(p.company_id)end as acces_offres_calcule,
 coalesce((select enabled from public.urgent_commercial_config where id),false)as mode_commercial,
 exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config conf on conf.id and conf.terms_version=t.version where t.company_id=p.company_id) as conditions_entreprise_acceptees,
 exists(select 1 from public.urgent_terms_acceptances t join public.urgent_commercial_config conf on conf.id and conf.terms_version=t.version where t.company_id=p.company_id and t.user_id=u.id)as conditions_ce_compte_acceptees,
 exists(select 1 from public.urgent_manual_subscriptions s where s.company_id=p.company_id and s.revoked_at is null and s.starts_at<=now()and s.ends_at>now()) as periode_payante_active,
 public.urgent_internal_premium_active(p.company_id) as premium_interne_actif,
 (select count(*) from public.urgent_offers o join public.urgent_shipments s on s.id=o.shipment_id where o.carrier_company_id=p.company_id and not s.is_test and o.accepted_at>=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris') as attributions_ce_mois
 from auth.users u left join public.profiles p on p.id=u.id
 left join public.companies c on c.id=p.company_id
 left join public.urgent_business_access a on a.company_id=p.company_id
 left join public.urgent_transport_document_access d on d.company_id=p.company_id
 where coalesce(to_jsonb(u)->>'deleted_at','')=''
)
select email,entreprise,role,company_id,email_confirme,etablissement_autorise,
 case forfait_id when 'basics'then 'Start'when 'bronze'then 'Drive'when 'silver'then 'Boost'when 'gold'then 'Premium'else forfait_id end as forfait_retenu,
 coalesce(role='admin' or (role in('client','carrier') and email_confirme and etablissement_autorise and not preparation_suspendue),false) as preparation_documents_autorisee,
 preparation_suspendue,documents_transporteur_valides,acces_offres_calcule,
 mode_commercial,conditions_entreprise_acceptees,conditions_ce_compte_acceptees,periode_payante_active,premium_interne_actif,attributions_ce_mois,
 array_remove(array[
  case when role is null then 'Profil absent'end,
  case when company_id is null then 'Entreprise non rattachée'end,
  case when not email_confirme then 'Adresse e-mail non confirmée'end,
  case when role<>'admin' and not etablissement_autorise then 'Établissement non autorisé'end,
  case when preparation_suspendue then 'Préparation documentaire suspendue par administration'end,
  case when role in('client','carrier','admin')and mode_commercial and not conditions_entreprise_acceptees then 'Conditions professionnelles actuelles non acceptées pour cette entreprise'end,
  case when role in('client','carrier','admin')and mode_commercial and conditions_entreprise_acceptees and not conditions_ce_compte_acceptees then 'Ce compte doit accepter les conditions avant une attribution commerciale'end,
  case when role='carrier' and not documents_transporteur_valides then 'Justificatifs transporteur à contrôler'end,
  case when role='carrier' and not acces_offres_calcule then 'Accès aux offres refusé : contrôler pièces, conditions et forfait'end
 ],null) as points_a_verifier
from comptes order by email;

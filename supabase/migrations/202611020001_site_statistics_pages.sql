-- Correctif de couverture, sans activer les envois ni créer de visites.
-- Prérequis : 202610260001_site_statistics.sql. Réexécutable.
-- Ne modifie ni le consentement, ni la rétention, ni les rapports déjà figés.
begin;
create or replace function public.urgent_record_site_event(p_page text,p_source text default 'direct',p_medium text default 'direct',p_campaign text default 'aucune',p_kind text default 'page_view',p_consent boolean default false)
returns void language plpgsql security definer set search_path='' as $$
declare actor uuid:=auth.uid();company uuid;today date:=(now() at time zone 'Europe/Paris')::date;accepted integer;
begin
 if p_consent is distinct from true or not coalesce((select enabled from public.urgent_site_stats_settings where id),false) then return;end if;
 if p_page not in ('/','/mentions-legales.html','/confidentialite.html','/conditions-professionnelles.html','/conditions-professionnelles-v3.html','/conditions-professionnelles-v4.html','/fonctionnement.html','/courses.html','/mes-courses.html','/deposer.html','/donneurs-ordre.html','/transporteurs.html','/mon-espace.html','/services-chronoss.html','/demenagement.html','/demander-un-devis.html','/retours-a-vide.html','/mobile.html') or p_page is null then return;end if;
 if p_kind not in ('page_view','account_seen') or p_kind is null or (p_kind='account_seen' and actor is null) then return;end if;
 if exists(select 1 from public.profiles where id=actor and role::text='admin') then return;end if;
 select company_id into company from public.profiles where id=actor;
 -- Plafond atomique de protection du volume ; aucune IP ou empreinte de navigateur stockée.
 insert into public.urgent_site_event_limits as limits(day,events)values(today,1)
 on conflict(day)do update set events=limits.events+1 where limits.events<10000 returning events into accepted;
 if not found then return;end if;
 insert into public.urgent_site_events(kind,page,source,medium,campaign,user_id,company_id)
 values(p_kind,p_page,
 case when p_source in ('direct','google','bing','linkedin','instagram','tiktok','facebook') then p_source else 'autre' end,
 case when p_medium in ('direct','organic','referral','paid_social','organic_social','email') then p_medium else 'autre' end,
 case when p_campaign in ('lancement_local','premieres_demandes','linkedin_contacts') then p_campaign else 'aucune' end,actor,company);
end;
$$;

create or replace function public.urgent_site_stats_public_status()returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('enabled',coalesce((select enabled from public.urgent_site_stats_settings where id),false),'pages_version','20261102-main-pages');
$$;
revoke all on function public.urgent_site_stats_public_status()from public;
grant execute on function public.urgent_site_stats_public_status()to anon,authenticated;
notify pgrst,'reload schema';
commit;

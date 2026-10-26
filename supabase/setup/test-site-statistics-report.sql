-- Après migration, mise à jour de bright-service et SITE_STATS_REPORTS_ENABLED=true.
-- Met en file un seul rapport TEST de la veille ; aucun compte, visite ou course fictif créé.
-- Le cron existant traite ce rapport à son prochain passage. Aucun secret sélectionné.
insert into public.urgent_site_reports(day,snapshot)
select d,public.urgent_build_site_report(d)||jsonb_build_object('test',true)
from(select (now() at time zone 'Europe/Paris')::date-1 as d)x
on conflict on constraint urgent_site_reports_day_key do nothing;
select day,status,attempts,sent_at,last_error_code
from public.urgent_site_reports where day=(now() at time zone 'Europe/Paris')::date-1;
select jobname,active from cron.job where jobname in ('urgent-registration-alerts','urgent-site-stats-retention');

-- Test d'envoi au seul administrateur, sur le dernier mois clôturé.
-- Ne crée ni course, ni frais, ni facture. Un seul test par mois de référence.
insert into public.urgent_monthly_reports(month,snapshot)
select m,public.urgent_build_monthly_report(m)||jsonb_build_object('test',true)
from (select (date_trunc('month',now() at time zone 'Europe/Paris')-interval '1 month')::date as m) previous
on conflict(month) do nothing;
select month,status,attempts,sent_at,last_error_code
from public.urgent_monthly_reports
order by month desc;

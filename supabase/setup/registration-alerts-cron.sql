-- À exécuter APRÈS migration et déploiement de registration-alerts.
-- Dans Supabase Vault, créer deux secrets, jamais dans ce fichier :
-- urgent_registration_alerts_url = https://rwkxkpbekvssmfnugcyn.supabase.co/functions/v1/registration-alerts
-- urgent_registration_alerts_secret = même valeur aléatoire que REGISTRATION_ALERTS_SECRET (32 caractères minimum).
-- Les extensions pg_cron et pg_net doivent être activées dans le projet.
do $$
begin
 if not exists(select 1 from vault.decrypted_secrets where name='urgent_registration_alerts_url' and decrypted_secret='https://rwkxkpbekvssmfnugcyn.supabase.co/functions/v1/registration-alerts')
 or not exists(select 1 from vault.decrypted_secrets where name='urgent_registration_alerts_secret' and length(decrypted_secret)>=32) then
  raise exception 'Configurer les deux secrets Vault avant de planifier les alertes.';
 end if;
end;
$$;
select cron.schedule('urgent-registration-alerts','* * * * *',$job$
 select net.http_post(
  url:=(select decrypted_secret from vault.decrypted_secrets where name='urgent_registration_alerts_url'),
  headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select decrypted_secret from vault.decrypted_secrets where name='urgent_registration_alerts_secret')),
  body:='{}'::jsonb,
  timeout_milliseconds:=60000
 );
$job$);

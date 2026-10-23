-- Durcissement groupé après audit réel. Aucune donnée métier supprimée, aucun tarif ou mode modifié.
begin;
-- La création/mise à jour des entreprises passe par les fonctions serveur autorisées.
revoke all on public.companies from public,anon,authenticated;
grant select on public.companies to authenticated;
-- Ancienne table offers : le site utilise urgent_offers. Suspendre l'ancien accès sans effacer les lignes.
revoke all on public.offers from public,anon,authenticated;
alter table public.offers enable row level security;
drop policy if exists urgent_legacy_offers_suspended on public.offers;
create policy urgent_legacy_offers_suspended on public.offers as restrictive
for all to anon,authenticated using(false) with check(false);
-- Retirer aussi les droits par colonne, indépendants des droits de table.
do $$
declare target record;
begin
 for target in select n.nspname,c.relname,a.attname from pg_attribute a
 join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='public' and c.relname in ('companies','offers') and a.attnum>0 and not a.attisdropped
 loop
  execute format('revoke insert (%I), update (%I), references (%I) on %I.%I from public,anon,authenticated',target.attname,target.attname,target.attname,target.nspname,target.relname);
 end loop;
end;
$$;
-- Les limites annoncées dans le formulaire doivent aussi être imposées à l'API Storage.
update storage.buckets set public=false,
 file_size_limit=least(coalesce(file_size_limit,10485760),10485760),
 allowed_mime_types=array(
  select distinct mime from unnest(coalesce(allowed_mime_types,array['application/pdf','image/jpeg','image/png'])) as m(mime)
  where mime=any(array['application/pdf','image/jpeg','image/png'])
 )
where id='carrier-documents';
commit;

-- Résultat de vérification regroupé : aucun secret ni donnée métier.
select
 not (has_table_privilege('anon','public.companies','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')
  or has_table_privilege('authenticated','public.companies','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')) as entreprises_droits_reduits,
 not (has_table_privilege('anon','public.offers','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')
  or has_table_privilege('authenticated','public.offers','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER,REFERENCES')) as ancienne_table_offres_bloquee,
 not b.public as stockage_prive,
 b.file_size_limit as limite_fichier_octets,
 b.allowed_mime_types as types_autorises,
 (select enabled from public.urgent_commercial_config where id) as mode_commercial
from storage.buckets b where b.id='carrier-documents';

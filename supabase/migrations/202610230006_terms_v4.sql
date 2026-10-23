-- À appliquer seulement après publication de conditions-professionnelles-v4.html.
-- Ne modifie ni tarifs, ni mode commercial, ni acceptations existantes.
-- La version courante change : chaque professionnel doit accepter explicitement la v4.
begin;
do $$
begin
 if not exists (select 1 from public.urgent_commercial_config where id and
   terms_version in ('PRO-B2B-2026-10-20-v3','PRO-B2B-2026-10-23-v4')) then
  raise exception 'Version courante inattendue : vérifier avant de remplacer les conditions';
 end if;
end $$;
update public.urgent_commercial_config
set terms_version='PRO-B2B-2026-10-23-v4',
 document_url='conditions-professionnelles-v4.html',
 document_sha256='20312ad93878e80922057927a4e15e5a9c8e77de25839de60d09efe05670c811'
where id;
commit;
select terms_version, document_url, document_sha256, enabled
from public.urgent_commercial_config where id;

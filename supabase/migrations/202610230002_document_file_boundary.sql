-- Lie toute nouvelle fiche documentaire au fichier réellement déposé par son entreprise.
-- Aucun changement des pièces ou décisions existantes.
begin;
-- Ancienne politique inutile après le verrouillage : retirer aussi cette permission potentielle.
drop policy if exists "Update own basic profile" on public.profiles;

drop policy if exists urgent_document_insert_file_boundary on public.carrier_documents;
create policy urgent_document_insert_file_boundary on public.carrier_documents as restrictive
for insert to authenticated with check (
 public.urgent_actor_role()='carrier'
 and company_id=public.urgent_actor_company()
 and review_status='pending' and reviewed_by is null and reviewed_at is null
 and split_part(storage_path,'/',1)=company_id::text
 and position('/' in storage_path)>0
 and length(storage_path)>length(company_id::text)+1
 and storage_path !~ '(^|/)\.{1,2}(/|$)'
 and position(chr(92) in storage_path)=0
 and exists (
  select 1 from storage.objects o
  where o.bucket_id='carrier-documents' and o.name=storage_path
 )
);
commit;

-- Lecture seule ; aucun nom de fichier, contenu ou donnée personnelle retourné.
select
 count(*) as fiches_documentaires,
 count(*) filter(where d.storage_path is null or split_part(d.storage_path,'/',1) is distinct from d.company_id::text
  or position('/' in d.storage_path)=0
  or length(d.storage_path)<=length(d.company_id::text)+1
  or d.storage_path ~ '(^|/)\.{1,2}(/|$)'
  or position(chr(92) in d.storage_path)>0) as chemins_a_examiner,
 count(*) filter(where o.id is null) as fichiers_introuvables
from public.carrier_documents d
left join storage.objects o on o.bucket_id='carrier-documents' and o.name=d.storage_path;

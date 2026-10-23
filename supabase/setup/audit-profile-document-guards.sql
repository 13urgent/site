-- Lecture seule : code de contrôle et métadonnées, sans lignes métier ni secrets Vault.
-- Un seul tableau de résultats pour faciliter l'export CSV.
select 'fonction'::text as type,p.proname::text as element,
 pg_get_functiondef(p.oid)::text as detail
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.proname in (
 'is_13urgent_admin','urgent_is_admin','urgent_actor_role',
 'urgent_actor_company','urgent_is_party','urgent_can_read_shipment'
)
union all
select 'droit_table',table_name||' / '||grantee,privilege_type
from information_schema.role_table_grants
where table_schema='public' and table_name in ('profiles','urgent_external_drafts','carrier_documents')
and grantee in ('PUBLIC','anon','authenticated')
union all
select 'droit_colonne',table_name||'.'||column_name||' / '||grantee,privilege_type
from information_schema.column_privileges
where table_schema='public' and table_name in ('profiles','urgent_external_drafts','carrier_documents')
and grantee in ('PUBLIC','anon','authenticated')
and privilege_type in ('INSERT','UPDATE','REFERENCES')
union all
select 'contrainte_document',c.conname,pg_get_constraintdef(c.oid)
from pg_constraint c where c.conrelid='public.carrier_documents'::regclass
union all
select 'trigger_document',t.tgname,pg_get_triggerdef(t.oid)
from pg_trigger t where t.tgrelid='public.carrier_documents'::regclass and not t.tgisinternal
order by type,element,detail;

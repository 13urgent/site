-- Lecture seule : aucun contenu de document, budget, note, e-mail ou secret n'est retourné.
select n.nspname as schema_name,c.relname as table_name,c.relrowsecurity as rls_enabled,c.relforcerowsecurity as rls_forced
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname in ('profiles','companies','urgent_external_drafts','carrier_documents','urgent_shipments','urgent_shipment_private','urgent_offers');
select schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
from pg_policies where schemaname in ('public','storage')
and (tablename in ('profiles','companies','urgent_external_drafts','carrier_documents','urgent_shipments','urgent_shipment_private','urgent_offers') or schemaname='storage')
order by schemaname,tablename,policyname;
select table_name,grantee,privilege_type from information_schema.role_table_grants
where table_schema='public' and table_name in ('profiles','companies','urgent_external_drafts','carrier_documents','urgent_shipment_private')
and grantee in ('PUBLIC','anon','authenticated') order by table_name,grantee,privilege_type;
select table_name,column_name,grantee,privilege_type from information_schema.column_privileges
where table_schema='public' and table_name in ('profiles','urgent_external_drafts')
and grantee in ('PUBLIC','anon','authenticated') and privilege_type in ('INSERT','UPDATE','REFERENCES');
select id,public from storage.buckets;
-- Les fonctions SECURITY DEFINER accessibles aux utilisateurs doivent être relues : elles peuvent contourner la RLS.
select n.nspname as schema_name,p.proname,pg_get_function_identity_arguments(p.oid) as arguments,
has_function_privilege('anon',p.oid,'EXECUTE') as anon_execute,
has_function_privilege('authenticated',p.oid,'EXECUTE') as authenticated_execute
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.prosecdef order by p.proname;

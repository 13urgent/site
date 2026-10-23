-- Un seul résultat exportable en CSV. Lecture seule : métadonnées et code serveur,
-- aucune ligne de compte, budget, note, document ni valeur de secret.
select 'fonction'::text as section,p.proname::text as element,
 pg_get_functiondef(p.oid)::text as detail
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.prosecdef
union all
select 'fonction_droits',p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
 jsonb_build_object('anon_execute',has_function_privilege('anon',p.oid,'EXECUTE'),'authenticated_execute',has_function_privilege('authenticated',p.oid,'EXECUTE'))::text
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.prosecdef
union all
select 'table_rls',c.relname,
 jsonb_build_object('rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity)::text
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r'
union all
select 'politique',schemaname||'.'||tablename||' / '||policyname,
 jsonb_build_object('type',permissive,'roles',roles,'commande',cmd,'using',qual,'with_check',with_check)::text
from pg_policies where schemaname in ('public','storage')
union all
select 'droit_table',table_schema||'.'||table_name||' / '||grantee,privilege_type
from information_schema.role_table_grants
where table_schema='public' and grantee in ('PUBLIC','anon','authenticated')
union all
select 'droit_colonne',table_schema||'.'||table_name||'.'||column_name||' / '||grantee,privilege_type
from information_schema.column_privileges
where table_schema='public' and grantee in ('PUBLIC','anon','authenticated')
and privilege_type in ('INSERT','UPDATE','REFERENCES')
union all
select 'stockage',id,jsonb_build_object('public',public,'file_size_limit',file_size_limit,'allowed_mime_types',allowed_mime_types)::text
from storage.buckets
union all
select 'vue',schemaname||'.'||viewname,definition
from pg_views where schemaname='public'
union all
select 'trigger',n.nspname||'.'||c.relname||' / '||t.tgname,pg_get_triggerdef(t.oid)
from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
where n.nspname in ('public','auth') and not t.tgisinternal
union all
select 'configuration','mode_commercial',jsonb_build_object('enabled',enabled,'terms_version',terms_version)::text
from public.urgent_commercial_config
order by section,element,detail;

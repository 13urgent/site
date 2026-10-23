-- Suspendre les imports externes et empêcher la modification directe des privilèges des profils.
-- Aucun effacement de données. Préserve les fonctions serveur de création de comptes.
begin;
alter table public.urgent_external_drafts enable row level security;
revoke all on public.urgent_external_drafts from public,anon,authenticated;
drop policy if exists urgent_external_drafts_suspended on public.urgent_external_drafts;
create policy urgent_external_drafts_suspended on public.urgent_external_drafts as restrictive
 for all to anon,authenticated using(false) with check(false);

-- Les rôles / rattachements à une entreprise ne doivent jamais être écrits depuis le navigateur.
alter table public.profiles enable row level security;
revoke all on public.profiles from public,anon,authenticated;
grant select on public.profiles to authenticated;
-- Révoquer aussi les éventuels droits accordés par colonne : la révocation de table seule ne suffit pas.
do $$
declare target record;
begin
 for target in select n.nspname,c.relname,a.attname from pg_attribute a
 join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='public' and c.relname in ('profiles','urgent_external_drafts') and a.attnum>0 and not a.attisdropped
 loop
  execute format('revoke insert (%I), update (%I), references (%I) on %I.%I from public,anon,authenticated',target.attname,target.attname,target.attname,target.nspname,target.relname);
 end loop;
end;
$$;
-- Réduit la lecture des profils au compte courant ou à l'administration, même en présence d'une ancienne politique large.
drop policy if exists urgent_profiles_read_scoped on public.profiles;
create policy urgent_profiles_read_scoped on public.profiles for select to authenticated
 using(id=auth.uid() or public.urgent_is_admin());
drop policy if exists urgent_profiles_read_boundary on public.profiles;
create policy urgent_profiles_read_boundary on public.profiles as restrictive for select to authenticated
 using(id=auth.uid() or public.urgent_is_admin());
drop policy if exists urgent_profiles_no_anonymous on public.profiles;
create policy urgent_profiles_no_anonymous on public.profiles as restrictive for select to anon using(false);
commit;

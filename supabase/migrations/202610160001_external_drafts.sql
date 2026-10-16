-- Migration additive : ne modifie pas les tables existantes.
-- Prérequis : public.profiles(id uuid, role), administrateurs attribués côté serveur.
begin;
create table public.urgent_external_drafts (
 id uuid primary key default gen_random_uuid(),
 created_by uuid not null default auth.uid() references auth.users(id),
 source text not null check (source in ('B2PWeb','Rubiwin')),
 reference text not null default '' check (length(reference)<=100),
 origin text not null check (length(trim(origin)) between 1 and 100),
 destination text not null check (length(trim(destination)) between 1 and 100),
 pickup timestamp without time zone,
 vehicle text not null default '' check (length(vehicle)<=100),
 weight numeric not null default 0 check (weight between 0 and 40000),
 budget numeric(12,2) not null default 0 check (budget>=0),
 notes text not null default '' check (length(notes)<=800),
 created_at timestamptz not null default now()
);
alter table public.urgent_external_drafts enable row level security;
revoke all on public.urgent_external_drafts from anon, authenticated;
grant select, insert, delete on public.urgent_external_drafts to authenticated;
create policy urgent_external_drafts_admin_read on public.urgent_external_drafts
 for select to authenticated using (
 exists(select 1 from public.profiles p where p.id=auth.uid() and p.role='admin')
);
create policy urgent_external_drafts_admin_insert on public.urgent_external_drafts
 for insert to authenticated with check (
 created_by=auth.uid() and exists(select 1 from public.profiles p where p.id=auth.uid() and p.role='admin')
);
create policy urgent_external_drafts_admin_delete on public.urgent_external_drafts
 for delete to authenticated using (
 exists(select 1 from public.profiles p where p.id=auth.uid() and p.role='admin')
);
commit;

-- Une référence de facture peut regrouper abonnement et frais d'une même entreprise,
-- jamais les factures de plusieurs entreprises. Aucun frais ni facture créé ici.
-- Rapport préalable : les éventuels conflits historiques sont conservés pour examen.
with references_existantes as (
 select trim(reference) as reference,company_id from public.urgent_external_invoice_registry
 union all select trim(invoice_reference),company_id from public.urgent_manual_subscriptions
 union all select trim(external_invoice_reference),company_id from public.urgent_service_entries where external_invoice_reference is not null
)
select reference,array_agg(distinct company_id) as entreprises_a_examiner
from references_existantes group by reference having count(distinct company_id)>1;

begin;
-- L'unicité commune arbitre aussi deux écritures simultanées dans des tables différentes.
-- Pas de reprise des lignes historiques : un conflit ancien ne bloque pas l'installation.
create table if not exists public.urgent_invoice_reference_companies (
 reference text primary key check(length(trim(reference)) between 1 and 120),
 company_id uuid not null references public.companies(id)
);
alter table public.urgent_invoice_reference_companies enable row level security;
revoke all on public.urgent_invoice_reference_companies from public,anon,authenticated,service_role;

create or replace function public.urgent_enforce_invoice_company()
returns trigger language plpgsql security definer set search_path='' as $$
declare ref text;old_ref text;claimed uuid;
begin
 if tg_table_name='urgent_manual_subscriptions' then
  ref:=new.invoice_reference;
  if tg_op='UPDATE' then old_ref:=old.invoice_reference;end if;
 elsif tg_table_name='urgent_external_invoice_registry' then
  ref:=new.reference;
  if tg_op='UPDATE' then old_ref:=old.reference;end if;
 else
  ref:=new.external_invoice_reference;
  if tg_op='UPDATE' then old_ref:=old.external_invoice_reference;end if;
 end if;
 if ref is null then return new;end if;
 -- Ne pas modifier une ancienne ligne conflictuelle lors d'une mise à jour sans changement.
 if tg_op='UPDATE' then
  if ref is not distinct from old_ref and new.company_id is not distinct from old.company_id then return new;end if;
 end if;
 ref:=trim(ref);
 if length(ref) not between 1 and 120 then raise exception 'Référence de facture de 1 à 120 caractères requise';end if;
 -- Une contrainte unique et un verrou de ligne, pas un simple SELECT suivi d'INSERT.
 insert into public.urgent_invoice_reference_companies as bound(reference,company_id)
 values(ref,new.company_id)
 on conflict(reference) do update set company_id=bound.company_id
 where bound.company_id=excluded.company_id
 returning company_id into claimed;
 if not found then raise exception 'Référence de facture déjà rattachée à une autre entreprise';end if;
 -- Inclure les références antérieures à cette migration, sans réécriture ni suppression.
 if exists(select 1 from public.urgent_manual_subscriptions s where trim(s.invoice_reference)=ref and s.company_id<>new.company_id)
 or exists(select 1 from public.urgent_external_invoice_registry r where trim(r.reference)=ref and r.company_id<>new.company_id)
 or exists(select 1 from public.urgent_service_entries e where trim(e.external_invoice_reference)=ref and e.company_id<>new.company_id) then
  raise exception 'Référence historique rattachée à une autre entreprise : rapprochement manuel requis';
 end if;
 if tg_table_name='urgent_manual_subscriptions' then new.invoice_reference:=ref;
 elsif tg_table_name='urgent_external_invoice_registry' then new.reference:=ref;
 else new.external_invoice_reference:=ref;end if;
 return new;
end;
$$;
revoke all on function public.urgent_enforce_invoice_company() from public,anon,authenticated,service_role;
drop trigger if exists urgent_invoice_company_subscription on public.urgent_manual_subscriptions;
create trigger urgent_invoice_company_subscription before insert or update of invoice_reference,company_id
on public.urgent_manual_subscriptions for each row execute function public.urgent_enforce_invoice_company();
drop trigger if exists urgent_invoice_company_registry on public.urgent_external_invoice_registry;
create trigger urgent_invoice_company_registry before insert or update of reference,company_id
on public.urgent_external_invoice_registry for each row execute function public.urgent_enforce_invoice_company();
drop trigger if exists urgent_invoice_company_entry on public.urgent_service_entries;
create trigger urgent_invoice_company_entry before insert or update of external_invoice_reference,company_id
on public.urgent_service_entries for each row execute function public.urgent_enforce_invoice_company();
commit;

with references_existantes as (
 select trim(reference) as reference,company_id from public.urgent_external_invoice_registry
 union all select trim(invoice_reference),company_id from public.urgent_manual_subscriptions
 union all select trim(external_invoice_reference),company_id from public.urgent_service_entries where external_invoice_reference is not null
), conflits as (
 select reference from references_existantes group by reference having count(distinct company_id)>1
)
select (select count(*) from pg_trigger where not tgisinternal and tgname in
 ('urgent_invoice_company_subscription','urgent_invoice_company_registry','urgent_invoice_company_entry'))=3 as protection_references_active,
 count(*) as conflits_historiques_a_examiner from conflits;

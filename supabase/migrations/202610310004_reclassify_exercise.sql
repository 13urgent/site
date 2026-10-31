-- Requalifier un exercice déclaré par erreur comme course réelle, avant transport.
-- Prérequis : commerce manuel et archivage déjà installés.
-- Aucune course ni écriture existante n'est modifiée à l'installation.
begin;

create table public.urgent_exercise_reclassifications (
 shipment_id uuid primary key references public.urgent_shipments(id),
 reason text not null check(length(trim(reason)) between 10 and 1000),
 reclassified_by uuid not null references auth.users(id),
 reclassified_at timestamptz not null default now(),
 credited_cents bigint not null check(credited_cents>=0)
);
alter table public.urgent_exercise_reclassifications enable row level security;
revoke all on public.urgent_exercise_reclassifications from public,anon,authenticated,service_role;

create function public.urgent_reclassify_exercise(p_shipment uuid,p_reason text,p_confirm boolean)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 s public.urgent_shipments;
 decision public.urgent_exercise_reclassifications;
 fee public.urgent_service_entries;
 remaining bigint;
 total_credited bigint:=0;
 request_id uuid;
begin
 if auth.uid() is null or not public.urgent_is_admin() then
  raise exception 'Administration requise';
 end if;
 if p_shipment is null or p_confirm is distinct from true or p_reason is null
  or length(trim(p_reason)) not between 10 and 1000 then
  raise exception 'Confirmez l’absence de transport réel et indiquez un motif de 10 à 1000 caractères';
 end if;

 -- Compatible avec le verrou FK pris par une correction de frais déjà en cours.
 select * into s from public.urgent_shipments where id=p_shipment for no key update;
 if not found then raise exception 'Course introuvable';end if;
 select * into decision from public.urgent_exercise_reclassifications where shipment_id=s.id;
 if found then
  if s.is_test and decision.reason=trim(p_reason) and decision.reclassified_by=auth.uid() then
   return jsonb_build_object('reclassified',true,'credited_cents',decision.credited_cents);
  end if;
  raise exception 'Une décision de requalification existe déjà ; consultez son historique';
 end if;
 if s.is_test then raise exception 'Cette course est déjà un exercice fictif ; aucune requalification à effectuer';end if;
 if s.archived_at is not null then raise exception 'Une course archivée ne peut pas être requalifiée';end if;
 if s.status not in ('open','assigned','heading_pickup','at_pickup') then
  raise exception 'Requalification autorisée uniquement avant chargement, pour une course non annulée';
 end if;

 -- Même ordre que le rapprochement des factures externes. La première passe
 -- verrouille tous les frais d'origine et empêche de nouvelles corrections.
 perform e.id from public.urgent_service_entries e
 where e.shipment_id=s.id or e.parent_id in (
  select f.id from public.urgent_service_entries f where f.shipment_id=s.id and f.kind='fee'
 ) order by e.id for update;
 -- Récupérer aussi un avoir validé pendant l'attente du premier verrou.
 -- NOWAIT évite un cycle de verrous avec un rapprochement externe concurrent.
 begin
  perform e.id from public.urgent_service_entries e
  where e.shipment_id=s.id or e.parent_id in (
   select f.id from public.urgent_service_entries f where f.shipment_id=s.id and f.kind='fee'
  ) order by e.id for update nowait;
 exception when lock_not_available then
  raise exception 'Rapprochement comptable en cours ; réessayez la requalification après vérification';
 end;
 if exists(
  select 1 from public.urgent_service_entries e
  where (e.shipment_id=s.id or e.parent_id in (
   select f.id from public.urgent_service_entries f where f.shipment_id=s.id and f.kind='fee'
  )) and e.external_invoice_reference is not null
 ) then
  raise exception 'Frais ou avoir déjà rattachés à une facture externe : examen et avoir externe requis avant toute requalification';
 end if;

 for fee in select * from public.urgent_service_entries
  where shipment_id=s.id and kind='fee' order by id
 loop
  select fee.amount_ht_cents+coalesce(sum(e.amount_ht_cents),0) into remaining
  from public.urgent_service_entries e where e.parent_id=fee.id;
  if remaining<0 or remaining>fee.amount_ht_cents then
   raise exception 'Solde de frais incohérent ; examen comptable requis';
  end if;
  if remaining>0 then
   request_id:=pg_catalog.md5('urgent-exercise-reclassification/'||fee.id::text)::uuid;
   perform public.urgent_credit_service_fee(fee.id,remaining::integer,trim(p_reason),request_id);
   total_credited:=total_credited+remaining;
  end if;
 end loop;

 -- Les statuts, offres et instantanés des documents déjà créés sont conservés.
 -- Les futures versions documentaires reliront le nouveau marqueur is_test.
 update public.urgent_shipments set is_test=true,updated_at=now() where id=s.id;
 insert into public.urgent_exercise_reclassifications(shipment_id,reason,reclassified_by,credited_cents)
 values(s.id,trim(p_reason),auth.uid(),total_credited);
 insert into public.urgent_commercial_audit(actor_id,action,target_id,details)
 values(auth.uid(),'exercise_reclassified',s.id,jsonb_build_object(
  'reason',trim(p_reason),'credited_cents',total_credited,'previous_status',s.status
 )::text);
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)
 values(s.id,auth.uid(),'reclassified_as_exercise');
 return jsonb_build_object('reclassified',true,'credited_cents',total_credited);
end;
$$;
revoke all on function public.urgent_reclassify_exercise(uuid,text,boolean) from public,anon;
grant execute on function public.urgent_reclassify_exercise(uuid,text,boolean) to authenticated;

create function public.urgent_exercise_reclassification_policy()
returns jsonb language sql stable set search_path='' as $$
 select jsonb_build_object('enabled',true,'version','20261031-exercise-reclassification','admin_only',true)
$$;
revoke all on function public.urgent_exercise_reclassification_policy() from public;
grant execute on function public.urgent_exercise_reclassification_policy() to anon,authenticated;

commit;
notify pgrst,'reload schema';
select public.urgent_exercise_reclassification_policy() as requalification_exercice;

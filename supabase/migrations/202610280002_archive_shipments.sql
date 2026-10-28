-- Retirer les courses annulées et les exercices fictifs des listes courantes.
-- Conservation des pièces, offres, événements et écritures de facturation.
begin;
alter table public.urgent_shipments add column if not exists archived_at timestamptz;
alter table public.urgent_shipments add column if not exists archived_by uuid references auth.users(id);
create or replace function public.urgent_shipment_archive_policy()returns jsonb
language sql stable set search_path='' as $$select jsonb_build_object('enabled',true,'restore',true);$$;
grant execute on function public.urgent_shipment_archive_policy()to anon,authenticated;
create or replace function public.urgent_archive_shipment(p_shipment uuid,p_archive boolean default true)returns jsonb
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;
begin
 if auth.uid() is null or coalesce(public.urgent_actor_role()not in('client','carrier','admin'),true)then raise exception 'Compte professionnel requis';end if;
 if p_archive is null then raise exception 'Choisissez le retrait ou la restauration';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company()then raise exception 'Seule l’entreprise propriétaire peut ranger cette course';end if;
 if s.status<>'cancelled' and not s.is_test then raise exception 'Seules les courses annulées et les exercices fictifs peuvent être retirés';end if;
 if p_archive and s.archived_at is not null or not p_archive and s.archived_at is null then return jsonb_build_object('changed',false,'archived',p_archive);end if;
 if p_archive then
  -- Un exercice encore ouvert ne doit plus recevoir de nouvelles offres après retrait.
  if s.is_test and s.status='open'then
   update public.urgent_shipments set status='cancelled'where id=s.id;
   insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'cancelled');
  end if;
  update public.urgent_offers set status='withdrawn'where shipment_id=s.id and status='submitted';
  update public.urgent_shipments set archived_at=now(),archived_by=auth.uid(),updated_at=now()where id=s.id;
 else
  -- Réafficher l'historique ne rouvre pas une course annulée et ne réactive pas ses offres.
  update public.urgent_shipments set archived_at=null,archived_by=null,updated_at=now()where id=s.id;
 end if;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),case when p_archive then 'shipment_archived'else 'shipment_restored'end);
 return jsonb_build_object('changed',true,'archived',p_archive);
end;$$;
revoke all on function public.urgent_archive_shipment(uuid,boolean)from public,anon;
grant execute on function public.urgent_archive_shipment(uuid,boolean)to authenticated;
commit;
notify pgrst,'reload schema';
select public.urgent_shipment_archive_policy()as rangement_des_courses;

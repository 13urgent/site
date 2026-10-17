-- Pilote B2B gratuit uniquement. Aucune souscription payée ni perception de frais.
-- Prérequis : profiles(id,company_id,role), companies, carrier_documents.
begin;
create table public.urgent_business_access (
 company_id uuid primary key references public.companies(id),
 siret text not null check(siret ~ '^[0-9]{14}$'),
 registry_checked boolean not null default false,
 pilot_enabled boolean not null default false,
 plan text not null default 'basics' check(plan in ('basics','bronze','silver','gold')),
 reviewed_by uuid not null references auth.users(id),
 reviewed_at timestamptz not null default now()
);
create table public.urgent_shipments (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id),
 owner_company_id uuid not null references public.companies(id),
 origin text not null check(length(trim(origin)) between 1 and 100),
 destination text not null check(length(trim(destination)) between 1 and 100),
 pickup timestamptz not null,
 vehicle text not null check(vehicle in ('Deux-roues','VL / fourgon','20 m³ avec hayon','Porteur','Semi-remorque')),
 pallets integer not null check(pallets between 0 and 99),
 weight numeric not null check(weight between 0 and 40000),
 status text not null default 'open' check(status in ('open','assigned','heading_pickup','at_pickup','loaded','delivery_reported','completed','cancelled')),
 assigned_company_id uuid references public.companies(id),
 accepted_offer_id uuid,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table public.urgent_shipment_private (
 shipment_id uuid primary key references public.urgent_shipments(id),
 company_name text not null check(length(trim(company_name)) between 1 and 120),
 contact_email text not null check(length(contact_email) between 3 and 254),
 instructions text not null default '' check(length(instructions)<=2000)
);
create table public.urgent_offers (
 id uuid primary key default gen_random_uuid(),
 shipment_id uuid not null references public.urgent_shipments(id),
 carrier_id uuid not null references auth.users(id),
 carrier_company_id uuid not null references public.companies(id),
 amount_ht numeric(12,2) not null check(amount_ht>0 and amount_ht<=1000000),
 status text not null default 'submitted' check(status in ('submitted','withdrawn','accepted','not_selected')),
 created_at timestamptz not null default now(),
 accepted_at timestamptz,
 unique(shipment_id,carrier_company_id)
);
alter table public.urgent_shipments add foreign key(accepted_offer_id) references public.urgent_offers(id);
create table public.urgent_shipment_events (
 id uuid primary key default gen_random_uuid(),
 shipment_id uuid not null references public.urgent_shipments(id),
 actor_id uuid not null references auth.users(id),
 event_type text not null,
 created_at timestamptz not null default now()
);
create index on public.urgent_shipments(status,created_at desc);
create index on public.urgent_offers(carrier_company_id,accepted_at);
create index on public.urgent_shipment_events(shipment_id,created_at);

-- Identité obtenue des profils serveur, jamais des métadonnées déclaratives.
create function public.urgent_actor_role() returns text language sql stable security definer set search_path='' as $$
 select role::text from public.profiles where id=auth.uid()
$$;
create function public.urgent_actor_company() returns uuid language sql stable security definer set search_path='' as $$
 select company_id from public.profiles where id=auth.uid()
$$;
create function public.urgent_is_admin() returns boolean language sql stable security definer set search_path='' as $$
 select coalesce(public.urgent_actor_role()='admin',false)
$$;
create function public.urgent_carrier_ready(p_company uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_business_access a where a.company_id=p_company and a.registry_checked and a.pilot_enabled)
 and not exists(
  select 1 from (values('registration'),('transport_licence'),('insurance')) required(kind)
  where not coalesce((select d.review_status='approved' and (d.expires_on is null or d.expires_on>=(now() at time zone 'Europe/Paris')::date)
    from public.carrier_documents d where d.company_id=p_company and d.document_type=required.kind
    order by d.created_at desc,d.id desc limit 1),false)
 )
$$;
-- Fonction d'autorisation sans récursion des politiques RLS.
create function public.urgent_can_read_shipment(p_id uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_shipments s where s.id=p_id and (
 public.urgent_is_admin() or s.owner_company_id=public.urgent_actor_company()
 or (public.urgent_actor_role()='carrier' and (s.status='open' or s.assigned_company_id=public.urgent_actor_company()))))
$$;
create function public.urgent_is_party(p_id uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.urgent_shipments s where s.id=p_id and (
 public.urgent_is_admin() or s.owner_company_id=public.urgent_actor_company() or s.assigned_company_id=public.urgent_actor_company()))
$$;
alter table public.urgent_business_access enable row level security;
alter table public.urgent_shipments enable row level security;
alter table public.urgent_shipment_private enable row level security;
alter table public.urgent_offers enable row level security;
alter table public.urgent_shipment_events enable row level security;
revoke all on public.urgent_business_access,public.urgent_shipments,public.urgent_shipment_private,public.urgent_offers,public.urgent_shipment_events from anon,authenticated;
grant select on public.urgent_business_access,public.urgent_shipments,public.urgent_shipment_private,public.urgent_offers,public.urgent_shipment_events to authenticated;
create policy urgent_access_read on public.urgent_business_access for select to authenticated using(public.urgent_is_admin() or company_id=public.urgent_actor_company());
create policy urgent_shipment_read on public.urgent_shipments for select to authenticated using(public.urgent_can_read_shipment(id));
create policy urgent_private_read on public.urgent_shipment_private for select to authenticated using(public.urgent_is_party(shipment_id));
create policy urgent_offer_read on public.urgent_offers for select to authenticated using(
 public.urgent_is_admin() or carrier_company_id=public.urgent_actor_company()
 or exists(select 1 from public.urgent_shipments s where s.id=shipment_id and s.owner_company_id=public.urgent_actor_company())
);
create policy urgent_events_read on public.urgent_shipment_events for select to authenticated using(public.urgent_is_party(shipment_id));

create function public.urgent_review_pilot(p_company uuid,p_siret text,p_plan text,p_enabled boolean,p_registry_checked boolean) returns void
language plpgsql security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_enabled and not p_registry_checked then raise exception 'Vérification au registre requise';end if;
 insert into public.urgent_business_access(company_id,siret,plan,pilot_enabled,registry_checked,reviewed_by)
 values(p_company,p_siret,p_plan,p_enabled,p_registry_checked,auth.uid())
 on conflict(company_id) do update set siret=excluded.siret,plan=excluded.plan,pilot_enabled=excluded.pilot_enabled,
 registry_checked=excluded.registry_checked,reviewed_by=excluded.reviewed_by,reviewed_at=now();
end;
$$;
create function public.urgent_publish_shipment(p_origin text,p_destination text,p_pickup timestamptz,p_vehicle text,p_pallets integer,p_weight numeric,p_company_name text,p_email text,p_instructions text) returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid;company uuid:=public.urgent_actor_company();
begin
 if public.urgent_actor_role() not in ('client','admin') or auth.uid() is null then raise exception 'Compte donneur d’ordre requis';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=company and registry_checked and pilot_enabled) then raise exception 'Établissement à faire vérifier par 13 URGENT pour le pilote';end if;
 if p_pickup<now() then raise exception 'Date d’enlèvement passée';end if;
 insert into public.urgent_shipments(owner_id,owner_company_id,origin,destination,pickup,vehicle,pallets,weight)
 values(auth.uid(),company,trim(p_origin),trim(p_destination),p_pickup,p_vehicle,p_pallets,p_weight) returning id into result;
 insert into public.urgent_shipment_private values(result,trim(p_company_name),trim(p_email),coalesce(p_instructions,''));
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(result,auth.uid(),'published');
 return result;
end;
$$;
create function public.urgent_submit_offer(p_shipment uuid,p_amount numeric) returns uuid
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;company uuid:=public.urgent_actor_company();result uuid;
begin
 if auth.uid() is null or public.urgent_actor_role()<>'carrier' then raise exception 'Compte transporteur requis';end if;
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.status<>'open' or s.pickup<now() then raise exception 'Course non disponible';end if;
 if s.owner_company_id=company then raise exception 'Offre sur sa propre entreprise interdite';end if;
 if not public.urgent_carrier_ready(company) then raise exception 'Accès pilote et documents valides requis';end if;
 insert into public.urgent_offers(shipment_id,carrier_id,carrier_company_id,amount_ht)
 values(p_shipment,auth.uid(),company,p_amount)
 on conflict(shipment_id,carrier_company_id) do update set amount_ht=excluded.amount_ht,status='submitted'
 returning id into result;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'offer_submitted');
 return result;
end;
$$;
create function public.urgent_withdraw_offer(p_offer uuid) returns void
language plpgsql security definer set search_path='' as $$
declare shipment uuid;s public.urgent_shipments;
begin
 select shipment_id into shipment from public.urgent_offers where id=p_offer;
 select * into s from public.urgent_shipments where id=shipment for update;
 if not found or s.status<>'open' then raise exception 'Course non ouverte';end if;
 update public.urgent_offers set status='withdrawn' where id=p_offer and carrier_company_id=public.urgent_actor_company() and status='submitted';
 if not found then raise exception 'Offre non modifiable';end if;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(shipment,auth.uid(),'offer_withdrawn');
end;
$$;
create function public.urgent_accept_offer(p_offer uuid,p_pilot_ack boolean,p_expected_amount numeric) returns void
language plpgsql security definer set search_path='' as $$
declare offer public.urgent_offers;s public.urgent_shipments;access public.urgent_business_access;max_courses integer;used integer;
begin
 if p_pilot_ack is distinct from true then raise exception 'Confirmation du pilote gratuit requise';end if;
 select * into offer from public.urgent_offers where id=p_offer;
 if not found then raise exception 'Offre introuvable';end if;
 select * into s from public.urgent_shipments where id=offer.shipment_id for update;
 if s.owner_company_id is distinct from public.urgent_actor_company() or public.urgent_actor_role() not in ('client','admin') then raise exception 'Seul le donneur d’ordre peut sélectionner';end if;
 if not exists(select 1 from public.urgent_business_access where company_id=s.owner_company_id and registry_checked and pilot_enabled) then raise exception 'Accès pilote du donneur d’ordre suspendu';end if;
 if s.status<>'open' or s.pickup<now() then raise exception 'Course non ouverte';end if;
 -- Relire après verrouillage pour éviter une offre retirée ou modifiée entre-temps.
 select * into offer from public.urgent_offers where id=p_offer;
 if offer.status<>'submitted' then raise exception 'Offre non disponible';end if;
 if p_expected_amount is null or offer.amount_ht is distinct from p_expected_amount then raise exception 'Le prix a changé. Actualisez les offres avant de confirmer.';end if;
 select * into access from public.urgent_business_access where company_id=offer.carrier_company_id for update;
 if not public.urgent_carrier_ready(offer.carrier_company_id) then raise exception 'Dossier transporteur non valide';end if;
 max_courses:=case access.plan when 'basics' then 1 when 'bronze' then 5 when 'silver' then 30 else null end;
 select count(*) into used from public.urgent_offers where carrier_company_id=offer.carrier_company_id and accepted_at>=date_trunc('month',now() at time zone 'Europe/Paris') at time zone 'Europe/Paris';
 if max_courses is not null and used>=max_courses then raise exception 'Quota mensuel de courses attribuées atteint';end if;
 update public.urgent_offers set status=case when id=p_offer then 'accepted' else 'not_selected' end,accepted_at=case when id=p_offer then now() else accepted_at end where shipment_id=s.id and status='submitted';
 update public.urgent_shipments set status='assigned',assigned_company_id=offer.carrier_company_id,accepted_offer_id=p_offer,updated_at=now() where id=s.id;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(s.id,auth.uid(),'assigned_pilot_no_charge');
end;
$$;
create function public.urgent_progress_shipment(p_shipment uuid,p_next text) returns void
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;expected text;
begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found then raise exception 'Course introuvable';end if;
 if p_next='completed' then
  if s.owner_company_id is distinct from public.urgent_actor_company() or s.status<>'delivery_reported' then raise exception 'Confirmation du client requise après déclaration de livraison';end if;
 else
  if public.urgent_actor_role()<>'carrier' or s.assigned_company_id is distinct from public.urgent_actor_company() then raise exception 'Transporteur attribué requis';end if;
  expected:=case s.status when 'assigned' then 'heading_pickup' when 'heading_pickup' then 'at_pickup' when 'at_pickup' then 'loaded' when 'loaded' then 'delivery_reported' else null end;
  if expected is null or p_next is distinct from expected then raise exception 'Transition non autorisée';end if;
 end if;
 update public.urgent_shipments set status=p_next,updated_at=now() where id=p_shipment;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),p_next);
end;
$$;
create function public.urgent_cancel_shipment(p_shipment uuid) returns void
language plpgsql security definer set search_path='' as $$
declare s public.urgent_shipments;
begin
 select * into s from public.urgent_shipments where id=p_shipment for update;
 if not found or s.owner_company_id is distinct from public.urgent_actor_company() then raise exception 'Donneur d’ordre requis';end if;
 if s.status<>'open' then raise exception 'Annulation autonome réservée aux courses non attribuées. Contactez 13 URGENT.';end if;
 update public.urgent_shipments set status='cancelled',updated_at=now() where id=p_shipment;
 insert into public.urgent_shipment_events(shipment_id,actor_id,event_type)values(p_shipment,auth.uid(),'cancelled');
end;
$$;
create function public.urgent_assignment_details(p_shipment uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.urgent_shipments;offer public.urgent_offers;result jsonb;
begin
 if not public.urgent_is_party(p_shipment) then raise exception 'Accès aux parties uniquement';end if;
 select * into s from public.urgent_shipments where id=p_shipment;
 if s.accepted_offer_id is null then raise exception 'Course non attribuée';end if;
 select * into offer from public.urgent_offers where id=s.accepted_offer_id;
 select jsonb_build_object('shipment_id',s.id,'carrier_company',c.name,'carrier_email',u.email,'amount_ht',offer.amount_ht,'fee_preview_ht',round(offer.amount_ht*0.015,2),'charged_ht',0,'mode','pilot_free','assigned_at',offer.accepted_at)
 into result from public.companies c join auth.users u on u.id=offer.carrier_id where c.id=offer.carrier_company_id;
 return result;
end;
$$;
revoke all on function public.urgent_assignment_details(uuid) from public,anon;
grant execute on function public.urgent_assignment_details(uuid) to authenticated;
create function public.urgent_pilot_directory() returns table(company_id uuid,company_name text,account_role text,declared_siret text,requested_plan text,pilot_enabled boolean,pilot_plan text,carrier_ready boolean)
language plpgsql stable security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 return query select c.id,c.name::text,p.role::text,u.raw_user_meta_data->>'business_siret',u.raw_user_meta_data->>'subscription_plan_request',coalesce(a.pilot_enabled,false),a.plan,public.urgent_carrier_ready(c.id)
 from public.companies c join public.profiles p on p.company_id=c.id join auth.users u on u.id=p.id
 left join public.urgent_business_access a on a.company_id=c.id
 where p.role in ('client','carrier') order by c.name limit 100;
end;
$$;
revoke all on function public.urgent_pilot_directory() from public,anon;
grant execute on function public.urgent_pilot_directory() to authenticated;
-- Accès explicite aux seuls appels authentifiés ; aucun rôle anonyme.
revoke all on function public.urgent_actor_role(),public.urgent_actor_company(),public.urgent_is_admin(),public.urgent_carrier_ready(uuid),public.urgent_can_read_shipment(uuid),public.urgent_is_party(uuid),public.urgent_review_pilot(uuid,text,text,boolean,boolean),public.urgent_publish_shipment(text,text,timestamptz,text,integer,numeric,text,text,text),public.urgent_submit_offer(uuid,numeric),public.urgent_withdraw_offer(uuid),public.urgent_accept_offer(uuid,boolean,numeric),public.urgent_progress_shipment(uuid,text),public.urgent_cancel_shipment(uuid) from public,anon;
grant execute on function public.urgent_actor_role(),public.urgent_actor_company(),public.urgent_is_admin(),public.urgent_carrier_ready(uuid),public.urgent_can_read_shipment(uuid),public.urgent_is_party(uuid),public.urgent_review_pilot(uuid,text,text,boolean,boolean),public.urgent_publish_shipment(text,text,timestamptz,text,integer,numeric,text,text,text),public.urgent_submit_offer(uuid,numeric),public.urgent_withdraw_offer(uuid),public.urgent_accept_offer(uuid,boolean,numeric),public.urgent_progress_shipment(uuid,text),public.urgent_cancel_shipment(uuid) to authenticated;
commit;

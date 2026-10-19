-- Préparation Stripe TEST uniquement. Aucun effet sur les autorisations métier.
begin;
create table public.urgent_billing_config (
 id boolean primary key default true check(id),
 enabled boolean not null default false,
 tax_policy_confirmed boolean not null default false,
 terms_version text not null default 'test-preparation-v1'
);
insert into public.urgent_billing_config(id)values(true);
create table public.urgent_billing_orders (
 id uuid primary key default gen_random_uuid(),
 request_key uuid not null,
 user_id uuid not null references auth.users(id),
 company_id uuid not null references public.companies(id),
 kind text not null check(kind in ('subscription','introduction')),
 plan text check(plan in ('bronze','silver','gold')),
 offer_id uuid references public.urgent_offers(id),
 shipment_id uuid references public.urgent_shipments(id),
 base_transport_ht numeric(12,2),
 amount_ht_cents integer not null check(amount_ht_cents>=50),
 currency text not null default 'eur' check(currency='eur'),
 terms_version text not null,
 status text not null default 'created' check(status in ('created','checkout_created','paid_test','expired','needs_review','refunded_test')),
 stripe_session_id text unique,
 stripe_subscription_id text,
 created_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '2 hours',
 paid_at timestamptz,
 unique(user_id,request_key)
);
create unique index urgent_billing_pending_subscription on public.urgent_billing_orders(company_id)
 where kind='subscription' and status in ('created','checkout_created');
create unique index urgent_billing_pending_introduction on public.urgent_billing_orders(shipment_id)
 where kind='introduction' and status in ('created','checkout_created','paid_test');
create table public.urgent_billing_events (
 stripe_event_id text primary key,
 event_type text not null,
 order_id uuid references public.urgent_billing_orders(id),
 event_created bigint not null,
 outcome text not null,
 processed_at timestamptz not null default now()
);
create table public.urgent_billing_subscriptions (
 stripe_subscription_id text primary key,
 company_id uuid not null references public.companies(id),
 user_id uuid not null references auth.users(id),
 plan text not null check(plan in ('bronze','silver','gold')),
 status text not null,
 last_event_created bigint not null,
 current_period_end timestamptz,
 updated_at timestamptz not null default now()
);
alter table public.urgent_billing_config enable row level security;
alter table public.urgent_billing_orders enable row level security;
alter table public.urgent_billing_events enable row level security;
alter table public.urgent_billing_subscriptions enable row level security;
revoke all on public.urgent_billing_config,public.urgent_billing_orders,public.urgent_billing_events,public.urgent_billing_subscriptions from anon,authenticated;
grant select on public.urgent_billing_orders,public.urgent_billing_subscriptions to authenticated;
create policy urgent_billing_orders_read on public.urgent_billing_orders for select to authenticated using(user_id=auth.uid() or public.urgent_is_admin());
create policy urgent_billing_subscriptions_read on public.urgent_billing_subscriptions for select to authenticated using(user_id=auth.uid() or public.urgent_is_admin());
grant select on public.urgent_billing_config,public.urgent_billing_orders to service_role;

create function public.urgent_billing_create_order(p_request uuid,p_kind text,p_plan text,p_offer uuid,p_terms_version text)
returns setof public.urgent_billing_orders language plpgsql security definer set search_path='' as $$
declare cfg public.urgent_billing_config;old_order public.urgent_billing_orders;company uuid:=public.urgent_actor_company();amount integer;offer public.urgent_offers;shipment public.urgent_shipments;
begin
 select * into cfg from public.urgent_billing_config where id;
 if not found or cfg.enabled is distinct from true or cfg.tax_policy_confirmed is distinct from true then raise exception 'Paiements de test non configurés';end if;
 if p_terms_version is distinct from cfg.terms_version then raise exception 'Version des conditions de test à confirmer';end if;
 if auth.uid() is null or company is null or p_request is null then raise exception 'Compte professionnel requis';end if;
 -- Sérialisation par entreprise pour éviter deux abonnements simultanés.
 perform 1 from public.urgent_business_access where company_id=company and registry_checked and pilot_enabled for update;
 if not found then raise exception 'Établissement professionnel non autorisé';end if;
 select * into old_order from public.urgent_billing_orders where user_id=auth.uid() and request_key=p_request;
 if found then
  if old_order.kind is distinct from p_kind or old_order.plan is distinct from p_plan or old_order.offer_id is distinct from p_offer then raise exception 'Identifiant de demande déjà utilisé pour un autre achat';end if;
  return next old_order;return;
 end if;
 update public.urgent_billing_orders set status='expired' where company_id=company and status in ('created','checkout_created') and (expires_at<now() or (stripe_session_id is null and expires_at<now()+interval '31 minutes'));
 if p_kind='subscription' then
  if public.urgent_actor_role() is distinct from 'carrier' or p_offer is not null then raise exception 'Abonnement réservé au transporteur';end if;
  amount:=case p_plan when 'bronze' then 1250 when 'silver' then 3333 when 'gold' then 6250 else null end;
  if amount is null then raise exception 'Forfait payant non autorisé';end if;
  if exists(select 1 from public.urgent_billing_subscriptions where company_id=company and status in ('active','trialing','past_due','unpaid','incomplete','paused')) then raise exception 'Un abonnement de test existe déjà : gestion via le prestataire requise';end if;
 elsif p_kind='introduction' then
  if coalesce(public.urgent_actor_role() not in ('client','admin'),true) or p_plan is not null then raise exception 'Frais réservés au donneur d’ordre';end if;
  select * into offer from public.urgent_offers where id=p_offer;
  select * into shipment from public.urgent_shipments where id=offer.shipment_id for update;
  if not found or shipment.owner_company_id is distinct from company or shipment.status<>'open' or shipment.is_test or shipment.pickup<now() then raise exception 'Course non éligible aux frais de test';end if;
  select * into offer from public.urgent_offers where id=p_offer;
  if offer.status<>'submitted' then raise exception 'Offre non disponible';end if;
  if not public.urgent_carrier_ready(offer.carrier_company_id) then raise exception 'Transporteur non admissible';end if;
  amount:=round(offer.amount_ht*100*0.015)::integer;
  if amount<50 then raise exception 'Frais inférieurs au minimum de ce parcours de paiement. Aucun minimum de frais ajouté.';end if;
 else raise exception 'Type de commande non autorisé';end if;
 return query insert into public.urgent_billing_orders(request_key,user_id,company_id,kind,plan,offer_id,shipment_id,base_transport_ht,amount_ht_cents,terms_version)
 values(p_request,auth.uid(),company,p_kind,p_plan,p_offer,shipment.id,offer.amount_ht,amount,p_terms_version) returning *;
end;
$$;

create function public.urgent_billing_link_session(p_order uuid,p_session text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if p_session !~ '^cs_test_[A-Za-z0-9]+$' then raise exception 'Session de test requise';end if;
 update public.urgent_billing_orders set stripe_session_id=p_session,status=case when status='created' then 'checkout_created' else status end
 where id=p_order and (stripe_session_id is null or stripe_session_id=p_session);
 if not found then raise exception 'Session déjà rattachée ou commande introuvable';end if;
end;
$$;

create function public.urgent_billing_apply_event(p_event text,p_type text,p_created bigint,p_order uuid,p_session text,p_amount integer,p_currency text,p_outcome text,p_subscription text,p_subscription_status text,p_period_end timestamptz)
returns text language plpgsql security definer set search_path='' as $$
declare purchase public.urgent_billing_orders;result text:=p_outcome;already text;current_offer public.urgent_offers;current_shipment public.urgent_shipments;
begin
 if p_outcome not in ('paid_test','expired','subscription_sync') then raise exception 'État de paiement non autorisé';end if;
 if p_type not in ('checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.expired','customer.subscription.updated','customer.subscription.deleted','invoice.paid','invoice.payment_failed') then raise exception 'Événement non autorisé';end if;
 -- L'insertion verrouille aussi les tentatives concurrentes sur le même événement.
 insert into public.urgent_billing_events(stripe_event_id,event_type,order_id,event_created,outcome) values(p_event,p_type,p_order,p_created,'processing') on conflict do nothing;
 if not found then return 'duplicate';end if;
 select * into purchase from public.urgent_billing_orders where id=p_order for update;
 if not found then raise exception 'Commande introuvable';end if;
 if purchase.stripe_session_id is not null and p_session is not null and purchase.stripe_session_id<>p_session then raise exception 'Session incorrecte';end if;
 if p_outcome='paid_test' then
  if p_session is null or p_session !~ '^cs_test_[A-Za-z0-9]+$' or p_amount is distinct from purchase.amount_ht_cents or p_currency is distinct from 'eur' then raise exception 'Montant, devise ou session incorrect';end if;
  if purchase.kind='introduction' then
   select * into current_shipment from public.urgent_shipments where id=purchase.shipment_id for update;
   select * into current_offer from public.urgent_offers where id=purchase.offer_id;
   if current_shipment.status<>'open' or current_shipment.is_test or current_offer.status<>'submitted' or current_offer.amount_ht is distinct from purchase.base_transport_ht then result:='needs_review';end if;
  end if;
  if purchase.status not in ('paid_test','refunded_test') then update public.urgent_billing_orders set status=result,stripe_session_id=p_session,stripe_subscription_id=p_subscription,paid_at=now() where id=p_order;end if;
 elsif p_outcome='expired' then
  update public.urgent_billing_orders set status='expired' where id=p_order and status in ('created','checkout_created');
 end if;
 if p_subscription is not null then
  if purchase.kind<>'subscription' or p_subscription !~ '^sub_[A-Za-z0-9]+$' or p_subscription_status not in ('active','trialing','past_due','unpaid','canceled','incomplete','incomplete_expired','paused') then raise exception 'Abonnement incorrect';end if;
  if purchase.stripe_subscription_id is not null and purchase.stripe_subscription_id<>p_subscription then raise exception 'Abonnement différent de la commande';end if;
  insert into public.urgent_billing_subscriptions(stripe_subscription_id,company_id,user_id,plan,status,last_event_created,current_period_end)
  values(p_subscription,purchase.company_id,purchase.user_id,purchase.plan,p_subscription_status,p_created,p_period_end)
  on conflict(stripe_subscription_id) do update set status=excluded.status,last_event_created=excluded.last_event_created,current_period_end=excluded.current_period_end,updated_at=now()
  where excluded.last_event_created>=public.urgent_billing_subscriptions.last_event_created and (public.urgent_billing_subscriptions.status<>'canceled' or excluded.status='canceled');
 end if;
 update public.urgent_billing_events set outcome=result where stripe_event_id=p_event;
 -- Aucune modification des documents, accès pilote, quotas ou contacts.
 return result;
end;
$$;
revoke all on function public.urgent_billing_create_order(uuid,text,text,uuid,text) from public,anon;
grant execute on function public.urgent_billing_create_order(uuid,text,text,uuid,text) to authenticated;
revoke all on function public.urgent_billing_link_session(uuid,text),public.urgent_billing_apply_event(text,text,bigint,uuid,text,integer,text,text,text,text,timestamptz) from public,anon,authenticated;
grant execute on function public.urgent_billing_link_session(uuid,text),public.urgent_billing_apply_event(text,text,bigint,uuid,text,integer,text,text,text,text,timestamptz) to service_role;
commit;

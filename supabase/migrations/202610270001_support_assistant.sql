-- Assistance privée : demandes, réponses et préanalyses, sans conférer de droit métier.
-- À appliquer une seule fois, après les migrations professionnelles existantes.
begin;
create table public.urgent_support_tickets (
 id uuid primary key default gen_random_uuid(),
 created_by uuid not null references auth.users(id) on delete cascade,
 company_id uuid references public.companies(id) on delete cascade,
 subject text not null check(length(trim(subject)) between 3 and 120),
 message text not null check(length(trim(message)) between 10 and 1500),
 status text not null default 'open' check(status in ('open','in_progress','resolved')),
 admin_reply text check(length(admin_reply)<=2500),
 replied_by uuid references auth.users(id) on delete set null,
 created_at timestamptz not null default now(),updated_at timestamptz not null default now()
);
create index on public.urgent_support_tickets(created_by,created_at desc);
create index on public.urgent_support_tickets(status,created_at);
create table public.urgent_document_prechecks (
 id uuid primary key default gen_random_uuid(),
 document_id uuid not null references public.carrier_documents(id) on delete cascade,
 company_id uuid not null references public.companies(id) on delete cascade,
 created_by uuid not null references auth.users(id) on delete cascade,
 engine text not null check(engine in ('metadata','openai')),
 verdict text not null check(verdict in ('needs_attention','manual_review')),
 summary text not null check(length(summary)<=1500),
 issues jsonb not null default '[]',unknowns jsonb not null default '[]',
 created_at timestamptz not null default now()
);
create index on public.urgent_document_prechecks(document_id,created_at desc);
create table public.urgent_support_limits (
 actor_id uuid not null references auth.users(id) on delete cascade,
 day date not null,kind text not null check(kind in ('ask','review','ticket','ai')),
 calls integer not null check(calls>0),primary key(actor_id,day,kind)
);
alter table public.urgent_support_tickets enable row level security;
alter table public.urgent_document_prechecks enable row level security;
alter table public.urgent_support_limits enable row level security;
revoke all on public.urgent_support_tickets,public.urgent_document_prechecks,public.urgent_support_limits from public,anon,authenticated,service_role;
grant select on public.urgent_support_tickets,public.urgent_document_prechecks to authenticated;
grant select,insert on public.urgent_document_prechecks to service_role;
create policy urgent_support_ticket_read on public.urgent_support_tickets for select to authenticated
 using(created_by=auth.uid() or public.urgent_is_admin());
create policy urgent_precheck_read on public.urgent_document_prechecks for select to authenticated
 using(created_by=auth.uid() or public.urgent_is_admin());

-- Appelé par la fonction Edge après validation réelle du JWT. Aucun appel anonyme.
create function public.urgent_support_reserve(p_actor uuid,p_kind text) returns boolean
language plpgsql security definer set search_path='' as $$
declare d date:=(now() at time zone 'Europe/Paris')::date;per_user integer;global_max integer;used integer;
begin
 if p_actor is null or not exists(select 1 from public.profiles where id=p_actor) then return false;end if;
 case p_kind when 'ask' then per_user:=30;global_max:=300;
 when 'review' then per_user:=5;global_max:=50;
 when 'ticket' then per_user:=5;global_max:=500;
 when 'ai' then per_user:=10;global_max:=20;
 else return false;end case;
 perform pg_advisory_xact_lock(hashtextextended('urgent-support:'||d::text||':'||p_kind,0));
 if coalesce((select sum(calls) from public.urgent_support_limits where day=d and kind=p_kind),0)>=global_max then return false;end if;
 insert into public.urgent_support_limits as limits(actor_id,day,kind,calls)values(p_actor,d,p_kind,1)
 on conflict(actor_id,day,kind)do update set calls=limits.calls+1 where limits.calls<per_user returning calls into used;
 return found;
end;
$$;
revoke all on function public.urgent_support_reserve(uuid,text) from public,anon,authenticated;
grant execute on function public.urgent_support_reserve(uuid,text) to service_role;

create function public.urgent_support_create_ticket(p_subject text,p_message text) returns uuid
language plpgsql security definer set search_path='' as $$
declare actor uuid:=auth.uid();company uuid;ticket uuid;
begin
 select company_id into company from public.profiles where id=actor;
 if actor is null or not found then raise exception 'Connexion professionnelle requise';end if;
 if p_subject is null or length(trim(p_subject)) not between 3 and 120
 or p_message is null or length(trim(p_message)) not between 10 and 1500 then raise exception 'Sujet ou message invalide';end if;
 if not public.urgent_support_reserve(actor,'ticket') then raise exception 'Limite quotidienne atteinte. Contactez contact@13urgent.fr';end if;
 insert into public.urgent_support_tickets(created_by,company_id,subject,message)
 values(actor,company,trim(p_subject),trim(p_message))returning id into ticket;
 return ticket;
end;
$$;
create function public.urgent_support_reply(p_ticket uuid,p_reply text,p_status text default 'resolved')returns void
language plpgsql security definer set search_path='' as $$
begin
 if not public.urgent_is_admin() then raise exception 'Administration requise';end if;
 if p_reply is null or length(trim(p_reply)) not between 1 and 2500 or p_status is null or p_status not in ('open','in_progress','resolved') then raise exception 'Réponse invalide';end if;
 update public.urgent_support_tickets set admin_reply=trim(p_reply),replied_by=auth.uid(),status=p_status,updated_at=now() where id=p_ticket;
 if not found then raise exception 'Demande introuvable';end if;
end;
$$;
revoke all on function public.urgent_support_create_ticket(text,text),public.urgent_support_reply(uuid,text,text) from public,anon;
grant execute on function public.urgent_support_create_ticket(text,text),public.urgent_support_reply(uuid,text,text) to authenticated;

create function public.urgent_support_ready()returns boolean language sql stable security definer set search_path='' as $$select true;$$;
revoke all on function public.urgent_support_ready() from public,anon,authenticated;
grant execute on function public.urgent_support_ready() to service_role;

-- Conservation minimale des demandes/réponses 180 j, avis 90 j, quotas 8 j.
create function public.urgent_support_purge()returns void language plpgsql security definer set search_path='' as $$
begin
 delete from public.urgent_support_tickets where updated_at<now()-interval '180 days';
 delete from public.urgent_document_prechecks where created_at<now()-interval '90 days';
 delete from public.urgent_support_limits where day<(now() at time zone 'Europe/Paris')::date-8;
end;
$$;
revoke all on function public.urgent_support_purge() from public,anon,authenticated;
grant execute on function public.urgent_support_purge() to service_role;
-- Purge indépendante du trafic lorsque pg_cron est présent.
do $$begin
 if exists(select 1 from pg_extension where extname='pg_cron') then
  perform cron.schedule('urgent-support-retention','35 3 * * *','select public.urgent_support_purge();');
 end if;
end$$;
commit;

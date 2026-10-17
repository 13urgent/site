-- Nouvelles inscriptions seulement ; ne modifie pas les comptes existants.
-- Validation de déclaration, pas vérification de l'entreprise au registre.
begin;
create function public.urgent_require_business_registration()
returns trigger language plpgsql set search_path = '' as $$
begin
 if coalesce(new.raw_user_meta_data->>'business_siret','') !~ '^[0-9]{14}$'
 or length(trim(coalesce(new.raw_user_meta_data->>'business_name',''))) not between 1 and 120
 or coalesce(new.raw_user_meta_data->>'business_use_declared','') <> 'true'
 or coalesce(new.raw_user_meta_data->>'requested_account_type','') not in ('client','carrier') then
  raise exception 'Inscription réservée aux professionnels : raison sociale, SIRET et usage professionnel requis.' using errcode='23514';
 end if;
 return new;
end;
$$;
revoke all on function public.urgent_require_business_registration() from public;
create trigger urgent_require_business_registration
before insert on auth.users
for each row execute function public.urgent_require_business_registration();
commit;

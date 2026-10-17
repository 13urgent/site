CREATE OR REPLACE FUNCTION public.create_user_profile()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
  new_company_id uuid;
  account_role text;
  company_name text;
BEGIN
  -- Seuls client et transporteur sont autorisés
  account_role := CASE
    WHEN NEW.raw_user_meta_data->>'role' = 'carrier'
      OR NEW.raw_user_meta_data->>'account_type' = 'carrier'
      OR NEW.raw_user_meta_data->>'account_type' = 'transporteur'
    THEN 'carrier'
    ELSE 'client'
  END;

  company_name := COALESCE(
    NULLIF(TRIM(NEW.raw_user_meta_data->>'company_name'), ''),
    NULLIF(TRIM(NEW.email), ''),
    'Entreprise à compléter'
  );

  INSERT INTO public.companies (
    name,
    company_type,
    verification_status
  )
  VALUES (
    company_name,
    account_role,
    'pending'
  )
  RETURNING id INTO new_company_id;

  INSERT INTO public.profiles (
    id,
    company_id,
    role
  )
  VALUES (
    NEW.id,
    new_company_id,
    account_role
  );

  RETURN NEW;
END;
$function$

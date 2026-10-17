# Recette réelle d'inscription professionnelle

Utiliser la raison sociale officielle et le SIRET de l'établissement, pour l'activité professionnelle réelle. Pour une nouvelle inscription, utiliser une adresse disponible qui n'est pas déjà présente dans Authentication/Users. Ne pas supprimer les deux comptes existants ni réutiliser leur compte pour prouver une nouvelle inscription. Ne pas transmettre les mots de passe ou liens de confirmation dans le chat.

1. Mettre à jour la copie locale depuis main : index.html, auth.js, app.js, style.css. Conserver assets et config.js. Vérifier que les forfaits visibles dans l'inscription transporteur portent les noms Start, Drive, Boost, Premium.
2. Appliquer la migration professionnelle une seule fois après avoir confirmé l'absence du trigger urgent_require_business_registration. Elle ne met pas à jour les utilisateurs existants. La compatibilité avec create_user_profile exportée a été testée en PostgreSQL embarqué ; refaire la recette sur le projet réel.
3. Nouvelle inscription transporteur : raison sociale, SIRET, déclaration d'usage professionnel, forfait Start pour le test, e-mail de test, mot de passe personnel. Aucun paiement. Vérifier l'e-mail uniquement si confirmation requise. Ne pas multiplier les demandes en cas de quota d'e-mail.
4. Après connexion, vérifier le bon type de profil, le nom de l'entreprise et son statut pending. Le choix de forfait est une demande, pas un abonnement actif.
5. Déposer un justificatif de test clairement identifié, vérifier l'enregistrement et son accès par l'administrateur. Les vrais justificatifs ne doivent pas être publiés ni approuvés pour les besoins du test. La validation de l'entreprise et l'activation d'un abonnement ne sont pas encore disponibles dans l'interface.
6. Un dossier non validé ne doit pas obtenir de droit de proposition. Les offres restent actuellement désactivées pour tous ; cela ne teste pas encore le futur contrôle d'accès aux offres réelles.
7. Tester ensuite un donneur d'ordre avec une autre adresse, si disponible : aucun choix d'abonnement transporteur ne doit apparaître. Les courses demeurent locales.

Le SIRET déclaré (14 chiffres) doit ensuite être vérifié au registre avec la qualité du représentant et les autorisations transport correspondantes. Les déclarations stockées dans auth.users.raw_user_meta_data sont modifiables par l'utilisateur et ne prouvent pas une entreprise vérifiée. Ne jamais en déduire un abonnement actif ou une permission d'offre.

## Diagnostic non destructif avant migration

```sql
select tgname from pg_trigger
where tgrelid='auth.users'::regclass
and not tgisinternal
order by tgname;
```

## Contrôle après inscription (remplacer uniquement le SIRET de test)

```sql
select
 u.id as user_id,
 u.email_confirmed_at is not null as email_confirme,
 p.role,
 c.name as entreprise,
 c.verification_status,
 u.raw_user_meta_data->>'business_siret' as siret_declare,
 u.raw_user_meta_data->>'business_use_declared' as usage_professionnel_declare,
 u.raw_user_meta_data->>'subscription_plan_request' as forfait_demande
from auth.users u
left join public.profiles p on p.id=u.id
left join public.companies c on c.id=p.company_id
where u.raw_user_meta_data->>'business_siret'='REMPLACER_PAR_LE_SIRET';
```

Ne lire ni exporter encrypted_password, les jetons ou l'intégralité de auth.users.

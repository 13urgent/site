# Préparation des paiements — 19 octobre 2026

## État et modèle

Code préparé, tests locaux exécutables ; aucun compte Stripe connecté par cette session, aucune migration de facturation appliquée à distance, aucune fonction de paiement déployée. Les paiements réels et l'ouverture commerciale restent désactivés. Le site public reste le pilote gratuit.

La plateforme facture ses services. Le transporteur facture directement le transport au donneur d'ordre, qui le règle directement. Le parcours préparé ne collecte jamais le prix du transport et ne répartit pas ce montant entre des comptes tiers.

| Service | Tarif préparé HT | Limite mensuelle envisagée |
| --- | --- | --- |
| Start | Gratuit | 1 attribution |
| Drive | 12,50 € / mois | 5 attributions |
| Boost | 33,33 € / mois | 30 attributions |
| Premium | 62,50 € / mois | Illimité |
| Mise en relation donneur d'ordre professionnel | 1,5 % du transport HT | Par course, fait générateur à contractualiser |

Les forfaits sont des montants mensuels arrondis issus des prix annuels présentés par l'utilisateur. Leurs totaux annuels peuvent donc différer de quelques centimes. La TVA applicable s'ajoute après validation du régime fiscal. Exemple : transport de 450 € HT, frais de plateforme de 6,75 € HT, facturés séparément. À 20 % de TVA sur ces seuls frais, le paiement plateforme serait de 8,10 € TTC ; le régime réel reste à confirmer.

Un paiement d'abonnement ne dispense jamais de documents valides. Le traitement d'une suspension et des remboursements doit être décrit dans les CGV validées ; une clause générale « aucun remboursement, quelle que soit la situation » n'est pas considérée ici comme acquise.

## Étape utilisateur : créer le compte de paiement

Créer le compte marchand sur https://dashboard.stripe.com/register au nom de la société qui exploitera effectivement 13 URGENT. Renseigner l'activité réelle d'intermédiation et ses prestations ; le prestataire décide de l'éligibilité. Utiliser les informations exactes du registre, du représentant et du bénéficiaire effectif, le compte bancaire de la société et les informations fiscales. Ne pas inventer de numéro de TVA ni employer un nom commercial à la place de la société titulaire.

Les pièces d'identité, coordonnées bancaires, clés secrètes et justificatifs se saisissent uniquement dans les interfaces sécurisées des prestataires. Ne rien envoyer de secret dans la conversation ni dans Git. L'activation du compte marchand et sa validation ne sont pas encore réalisées.

## Branchement technique, mode test uniquement

1. Sauvegarder la base et contrôler les migrations déjà appliquées. La seule nouvelle migration de cette préparation est `supabase/migrations/202610190004_billing_test.sql` ; elle suppose les migrations pilote et correctifs 001–003 du 19 octobre. Ne pas rejouer tout le dossier. Elle crée des tables séparées et laisse `enabled=false`.
2. Dans Stripe, en environnement de test, créer les trois tarifs EUR récurrents **mensuels**, un exemplaire par abonnement, TVA exclusive : Drive 12,50 €, Boost 33,33 €, Premium 62,50 €. Pas de tarif payant Start. Configurer Stripe Tax pour les essais ; le code refuse les tarifs qui ne correspondent pas exactement. L'activation fiscale réelle demande la validation du comptable et peut entraîner des coûts prestataire.
3. Dans les secrets des Edge Functions Supabase, définir les valeurs ci-dessous. Les clés `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` sont fournies par l'environnement Supabase et restent côté serveur. Ne jamais recopier la service_role dans `config.js`.

| Nom côté serveur | Valeur attendue |
| --- | --- |
| BILLING_TEST_ENABLED | `true` uniquement pour la recette test |
| PUBLIC_SITE_URL | URL exacte du site de recette, avec son sous-dossier et sa barre finale |
| STRIPE_TEST_SECRET_KEY | Clé secrète de test `sk_test_…` |
| STRIPE_TEST_WEBHOOK_SECRET | Secret de signature du point de terminaison de test `whsec_…` |
| STRIPE_TEST_PRICE_BRONZE | Identifiant `price_…` de Drive |
| STRIPE_TEST_PRICE_SILVER | Identifiant `price_…` de Boost |
| STRIPE_TEST_PRICE_GOLD | Identifiant `price_…` de Premium |

4. Déployer les fonctions `billing-checkout` et `billing-webhook` depuis le dépôt avec la CLI Supabase authentifiée et le projet correctement lié :

```
supabase functions deploy billing-checkout
supabase functions deploy billing-webhook
```

La configuration `verify_jwt=false` est intentionnelle : Checkout vérifie lui-même le jeton utilisateur via Auth ; le webhook contrôle la signature Stripe sur les octets reçus. Le webhook ne peut pas recevoir de JWT utilisateur. Ne pas supprimer ces vérifications applicatives.

5. Enregistrer le webhook **de test** dans Stripe : `https://<référence-projet>.supabase.co/functions/v1/billing-webhook`. Configurer la version API **2024-06-20**, celle explicitement attendue par le code, et les événements suivants : `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.expired`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Vérifier que cette version est disponible ; toute autre version est refusée et nécessite adaptation et nouvelle recette. Reporter son secret dans Supabase.
6. Une fois les tarifs, la politique fiscale de test et les fonctions vérifiés, autoriser uniquement la recette en base :

```sql
update public.urgent_billing_config
set enabled = true, tax_policy_confirmed = true
where id = true;
```

7. Activer `window.URGENT_BILLING_TEST_UI = true` uniquement dans une copie de recette du site. Le constructeur de publication pilote force cette valeur à `false`. Ce commutateur n'accorde aucun droit et ne remplace pas les contrôles serveur. Les établissements de recette doivent être normalement admissibles : l'exception CHRONOSS pour exercices fictifs ne suffit pas pour tester des frais sur une course ordinaire.

Le code refuse les clés de production et les objets Stripe réels. Changer simplement une clé ne permet donc pas de passer en production.

## Recette à effectuer chez les prestataires

Utiliser les moyens de paiement de test publiés par Stripe : https://docs.stripe.com/testing. Ne pas saisir une vraie carte pour cette recette.

- Abonnement : consentement explicite à l'essai, montant HT correct et TVA de test, retour au bon site, statut confirmé seulement après webhook signé. Annulation, expiration, authentification supplémentaire et échec du paiement.
- Frais : sur une course de recette ordinaire appartenant au donneur d'ordre de test, offre à 450 € HT → 675 centimes HT de frais. Le bouton ne paie jamais les 450 € et n'attribue pas la course. Si le prix change pendant le paiement, la commande passe en vérification manuelle.
- Rejouer un événement, vérifier l'absence de doublon ; vérifier les renouvellements et un paiement échoué, la résiliation dans Stripe test et les événements reçus dans le désordre.
- Vérifier avec deux comptes distincts la confidentialité des commandes. Vérifier qu'aucun abonnement payé en test n'approuve de document, ne change un quota ou ne révèle un contact.
- Pour arrêter la recette : désactiver `BILLING_TEST_ENABLED`, `urgent_billing_config.enabled` et le commutateur d'interface. Une coupure entraîne des tentatives de webhook en échec ; surveiller leur reprise avant de relancer.

## Ce qu'il reste pour encaisser réellement

Ce lot prépare les ordres et les confirmations de paiement de test. Il ne fournit pas encore : ouverture publique des inscriptions, abonnement commercial donnant les quotas correspondants, portail de changement/résiliation, remboursements et avoirs, factures conformes, rapprochement comptable, parcours définitif reliant sélection → frais → attribution, gestion des litiges et impayés, ni preuve de livraison signée.

La version commerciale doit aussi traiter les changements de prix, documents expirés pendant le paiement, course annulée ou attribuée pendant Checkout et frais trop faibles pour un paiement unitaire. Le parcours test refuse un montant inférieur à 0,50 € HT sans ajouter de frais minimum ; la solution commerciale reste à décider.

Avant ouverture : valider avec un conseil compétent le rôle réel d'intermédiaire au regard du transport, les contrats client/transporteur, le fait générateur des 1,5 %, les annulations/remboursements/suspensions, la TVA et les mentions de facturation. Compléter mentions légales, confidentialité, conservation et droits RGPD. L'intitulé « mise en relation » ne suffit pas à déterminer la qualification juridique.

Terminer ensuite l'intégration commerciale, faire la recette distante Stripe/Supabase, vérifier les accès et documents, l'envoi d'e-mails, les sauvegardes et la surveillance d'erreurs, puis ouvrir les inscriptions. Le domaine `13urgent.fr` et son HTTPS peuvent être raccordés séparément : aucun paiement ne nécessite de résoudre d'abord le ticket FTP OVH.

## Vérifications locales et limites

Tests SQL via PGlite : activation explicite, tarifs, 1,5 %, droits de lecture et écriture, protection des RPC serveur, idempotence et événements désordonnés. Tests HTTP avec prestataires simulés : connexion, origine, prix, signature brute, mode test, montants et URL. Chromium : consentement et absence de montant contrôlé par le navigateur. Le pilote conserve ses parcours existants.

Ces tests ne prouvent pas un encaissement Stripe ni une exécution Deno distante. La CLI/Deno et l'API Stripe réelle ne sont pas validés par cette session. Aucun secret ni donnée de carte n'est inclus dans les tests.

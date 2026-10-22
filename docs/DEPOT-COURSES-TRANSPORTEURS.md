# Déposer une course avec un compte transporteur — 22 octobre 2026

Demande : administrateurs, donneurs d'ordre et transporteurs peuvent déposer une course. Le transporteur déposant devient donneur d'ordre pour cette course ; son abonnement transporteur ne couvre pas les frais de mise en relation. Le dépôt reste gratuit. En mode commercial actif, les frais restent de 1,5 % HT du prix HT convenu, TVA applicable en sus, à confirmation de la proposition et sur la facture mensuelle CHRONOSS.

## Préparation et installation

Le formulaire affiche maintenant la raison d'un accès bloqué et un bouton de connexion. Il est disponible pour les trois rôles après lecture du profil, indépendamment d'une erreur de chargement de la liste des courses. Le serveur conserve le contrôle de la vérification de l'établissement avant publication. Les transporteurs voient un rappel de leur rôle de donneur d'ordre lorsqu'ils déposent.

Appliquer dans SQL Editor `supabase/migrations/202610220001_carrier_shipper.sql`, après la migration commerciale manuelle `202610200001_manual_commerce.sql`. Le script transactionnel remplace trois fonctions : publication, attribution sans frais et attribution commerciale. Il peut être réexécuté. Aucune modification de rôle, de tarif, de frais déjà enregistrés, de paiements, d'abonnements ou d'accès aux pièces. Les privilèges existants des fonctions sont conservés.

Cette migration n'active pas le mode commercial. Vérifier ce réglage dans l'administration avant de promettre une facturation réelle : les attributions du mode gratuit restent sans frais ; seuls les parcours commerciaux avec consentement explicite enregistrent les 1,5 %.

Un transporteur ne peut pas répondre à une demande de sa propre entreprise. Le propriétaire de la demande sélectionne les offres ; les autres transporteurs ne voient pas leurs prix. Le dépôt par un transporteur ne remplace pas les contrôles de documents, de période et de quota quand il répond à la demande d'une autre entreprise. Les exercices fictifs restent réservés à l'administration.

## Vérifications locales

- `tests/carrier-shipper-sql.cjs` : trois rôles, établissement vérifié, interdiction d'auto-offre, attribution par le propriétaire transporteur, confidentialité et refus anonyme. Deux transporteurs avec périodes d'abonnement enregistrées en base de test ; frais de 675 centimes HT à la charge du transporteur déposant pour 450 € HT, prix et consentement contrôlés.
- `tests/marketplace-pilot-browser.cjs` : connexion absente, erreurs réseau, formulaire utilisable malgré une liste inaccessible, dépôt client et transporteur, pas de formulaire d'offre sur sa propre course, attribution et suivi, affichage mobile.
- `tests/manual-commerce-browser.cjs` : parcours commercial existant, frais, conditions, CSV et contrôles d'accès toujours fonctionnels.

La migration n'a pas été exécutée dans la base distante par l'assistant ; cette étape doit être confirmée dans le tableau de bord. Les tests bancaires sont simulés localement et ne constituent aucun rapprochement bancaire réel.

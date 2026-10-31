# Premium interne offert

Choix demandé par Haeckel le 31 octobre 2026 : conserver Premium pour les comptes internes avec une décision administrative distincte des règlements clients.

## Modèle

`urgent_internal_premium_periods` conserve les périodes, le décideur, le motif et les retraits. Seuls les administrateurs peuvent accorder/retirer un droit via les fonctions contrôlées. La lecture est réservée à l'entreprise concernée et aux administrateurs. Aucune modification directe de la table n'est accordée aux utilisateurs.

Les périodes utilisent les jours de Paris ; le dernier jour choisi est inclus, stocké sous la forme d'une fin exclusive à minuit du lendemain. Elles commencent aujourd'hui ou dans le futur et durent au plus 366 jours. Les périodes internes ne se chevauchent pas pour la même entreprise. Une référence stable rend le rejeu après réponse réseau perdue idempotent. Un motif et une confirmation explicite sont nécessaires. Les décisions sont ajoutées à `urgent_commercial_audit`.

Une période offerte ne crée aucune ligne de règlement, souscription bancaire ou facture. Elle ne change pas les plans historiquement sélectionnés, les documents ou les acceptations de conditions. La préparation de l'accès n'utilise pas les métadonnées déclaratives Auth.

## Calcul des droits

Les contrôles d'établissement, documents et conditions restent communs. En mode commercial, une période Premium interne active devient une source de droit supplémentaire, à côté d'une période payée ou du Start admissible. Une période interne active applique le quota Premium au moment de l'attribution commerciale ; elle prime sur un ancien choix Start ou une période payée inférieure pendant sa durée. À sa fin ou son retrait, les autres sources de droit applicables sont relues, sans désactiver une période payée valable.

Les frais de mise en relation et leur consentement restent inchangés. L'ancien parcours pilote reste soumis aux protections antérieures et au quota Premium si cet accès est actif. Les périodes expirées ou futures ne donnent pas d'accès par elles-mêmes. Les fonctions d'attribution conservent les contrôles de prix, d'entreprise propriétaire, de statut, de dates et de pièces.

## Interface

`internal-premium.js`, chargé depuis le modèle partagé, s'active seulement si `urgent_internal_premium_policy` existe. Administration : recherche d'entreprise par nom/e-mail, identité technique et SIRET visibles, état documentaire/conditions, dates, motif, décision, historique et retrait. Mon espace transporteur : période offerte clairement distinguée d'un règlement, sans message de paiement nécessaire pour cet accès. Le service worker ne cache que le fichier JavaScript, pas les réponses privées.

## Activation

Migration séparée `202610310002_internal_premium.sql`, puis activation explicite des périodes depuis le compte administrateur. Aucun accès n'est attribué lors de la migration. Les comptes du projet réel ne sont pas modifiés depuis l'environnement de développement, qui ne dispose pas d'accès administrateur Supabase.

Le diagnostic privé des comptes est fourni par l'utilisateur ; il n'est pas inclus dans la publication statique. Le rattachement de plusieurs fiches d'entreprise reste un sujet séparé et ne doit pas être fusionné par nom seul.

## Vérifications

`tests/internal-premium-sql.cjs` vérifie les rôles, droits directs, dates, reprises, chevauchements, absence de faux paiement, quota Premium, maintien des frais, contrôle des pièces/conditions/établissement, retrait, expiration et cloisonnement.

`tests/manual-commerce-browser.cjs --internal` vérifie le parcours administratif réel sur SQL local, la reprise après réponse perdue, l'affichage transporteur, le retrait et le mobile. Les autres parcours de commerce manuel sont vérifiés dans le même scénario. Les utilisateurs et sessions de test sont simulés, sans écriture de production.

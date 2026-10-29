# Vérification du 29 octobre 2026

## Résultat observé

Les 35 scénarios de la suite générale ont réussi lors de cette vérification. Deux contrôles complémentaires ont réussi séparément : visibilité SQL des exercices fictifs, puis navigateur sur la version publiée exportée de GitHub. Le nouveau scénario de visibilité rejoint la suite générale pour les prochains contrôles.

Les essais utilisent PostgreSQL local (PGlite), des comptes de fixture et des API simulées pour les parcours navigateur. Ils ne prouvent pas à eux seuls qu'un compte client réel peut terminer chaque opération en production.

## Site et services effectivement vérifiés en ligne

- Les 25 fichiers HTML, JavaScript et CSS contrôlés sont identiques à la branche `gh-pages` récupérée aujourd'hui.
- Les 25 liens et ressources contrôlés depuis les pages publiques et d'administration répondent HTTP 200. Cela ne mesure ni le référencement ni toute la lecture des médias.
- L'inscription e-mail est ouverte ; la confirmation de l'adresse reste requise.
- Les fonctions de modification et de rangement des courses répondent avec les indicateurs d'activation attendus.
- La politique documentaire répond `enabled=true`, `months=6`.
- L'assistance répond avec la version `20261028-validation-mail`. La mise à jour préparée pour les notifications de validation est donc déployée. Le statut annonce les services IA et tickets disponibles ; aucun appel IA payant n'a été déclenché pour vérifier la qualité d'une réponse pendant cet audit.
- Le mode commercial est actif, avec les conditions `PRO-B2B-2026-10-23-v4`. L'empreinte du document servi est identique à celle déclarée par le serveur.
- Sans connexion, les profils, pièces des transporteurs, coordonnées privées des courses, tickets et annuaire administratif répondent 401. L'appel non authentifié à `bright-service` est également refusé.

Aucune course réelle, inscription, offre, validation documentaire, facture ou période d'abonnement n'a été créée, supprimée ou modifiée en production. Aucun e-mail, publication sociale, paiement ou changement publicitaire n'a été déclenché.

## Parcours couverts localement

Inscription professionnelle, connexion et réinitialisation du mot de passe ; séparation administration/utilisateur ; absence d'auto-promotion au rôle administrateur ; documents et stockage privé ; préanalyse distincte de l'approbation ; catégories, expiration et renouvellement semestriel ; classement des dossiers.

Publication client et transporteur ; offres confidentielles ; erreurs locales d'envoi ; modification avec révision et retrait explicite des offres antérieures ; attribution ; suivi ; incidents ; confirmation client ; classement et restauration des courses annulées et fictives ; pagination et affichage mobile.

Abonnements demandés distincts des droits actifs ; activation administrative et périodes après virement ; quotas ; frais, factures et relevés ; assistance et réponses ; notifications de validation avec vrais destinataires relus côté serveur ; consentement et exclusion des administrateurs/exercices de la conversion publicitaire.

## Exercices fictifs : réponse précise au problème signalé

Un exercice ouvert peut être lu par les transporteurs connectés ; ses coordonnées privées ne sont pas accessibles aux entreprises non participantes. Il porte la mention d'exercice fictif. Un exercice terminé n'est plus visible d'un autre transporteur non attribué. Le propriétaire, le transporteur attribué et l'administration conservent les accès autorisés à l'historique.

Le rangement est activé. Il est réservé à l'entreprise propriétaire, même lorsqu'un administrateur peut consulter des fiches d'autres entreprises. Il conserve les données et ne constitue pas une suppression définitive. Un exercice terminé rangé reste terminé ; il reste accessible aux parties dans l'historique replié.

Ces règles sont vérifiées par un nouveau scénario SQL. La cause exacte du bouton absent sur la capture du propriétaire reste à confirmer avec son compte connecté : la capture seule ne permet pas de connaître l'entreprise de la session ni la version JavaScript chargée. Ne pas annoncer ce cas individuel résolu sur la seule base d'un test local.

## Améliorations recommandées, par priorité

1. **Notification et délivrabilité.** Ajouter une file persistante des e-mails, un état consultable « en attente / accepté / échec » et une reprise bornée après erreur. Actuellement, la réception en boîte de réception n'est pas garantie par l'acceptation du fournisseur ; les notifications de validation n'ont pas de file de reprise persistante.
2. **Renouvellement documentaire.** Ajouter des rappels automatiques avant échéance, par exemple à J-30, J-7 et à échéance, avec prévention des doublons. La règle semestrielle et son affichage existent ; une relance périodique par e-mail n'est pas installée.
3. **Nettoyage et lisibilité du suivi.** Montrer clairement le compte et l'entreprise connectés dans le suivi, expliquer les actions réservées au propriétaire et distinguer davantage les exercices des courses commerciales. Étudier un espace de test séparé : aujourd'hui un exercice ouvert peut être vu par les transporteurs.
4. **Fiabilité des envois de course.** Renforcer la publication initiale avec un délai réseau explicite, une protection contre les soumissions concurrentes et une référence permettant de retrouver l'opération après une réponse réseau perdue. Les offres et modifications disposent déjà de protections spécifiques ; elles ne constituent pas une garantie d'idempotence de toutes les publications.
5. **Mesure de la campagne.** Vérifier une conversion réelle attribuée et la pertinence des nouveaux termes de recherche avant toute hausse de budget. Le tableau transmis affiche 19 clics, 15,54 euros et aucune conversion enregistrée sur le 26–28 octobre ; il ne permet pas de distinguer absence de conversion et défaut de mesure.

Ces évolutions sont des recommandations et ne sont pas annoncées comme développées ou déployées par cet audit.

## Vérifications réelles encore nécessaires

- Réception d'un e-mail de validation et d'une réponse d'assistance, ainsi que parcours complet de réinitialisation de mot de passe sur une boîte contrôlée.
- Reproduction avec le compte actuellement connecté du bouton de rangement absent signalé par le propriétaire.
- Parcours commercial complet avec deux comptes réels et rapprochement bancaire ; sans créer de fausse opération commerciale pour cet audit.
- Journaux privés, tâches planifiées, sauvegardes et restauration Supabase : absence d'accès administrateur dans cette session, donc aucune affirmation de contrôle de ces éléments.
- Conversion réellement attribuée, paramètres actuels et date de fin Google Ads : aucun accès au compte publicitaire.
- Agent autonome de publication sociale et futurs marchés publics : non installés. Les publications déjà réalisées étaient manuelles.

## Preuves conservées

- `/workspace/13urgent-tools/audit-site-20261029.json` : 35 scénarios généraux et deux contrôles complémentaires réussis.
- `/workspace/13urgent-tools/audit-public-live-20261029.json` : fichiers publiés et réponses réelles des services.
- `/workspace/13urgent-tools/audit-liens-20261029.json` : liens et ressources contrôlés.
- `tests/shipment-visibility-sql.cjs` : nouveau contrôle de la visibilité des exercices.

Le contrôle navigateur de déploiement repose sur les fichiers publiés et des API simulées. Les contrôles HTTPS en ligne utilisent le client Python avec sa chaîne de confiance configurée. Ils ne sont pas présentés comme un parcours client connecté effectué dans le navigateur réel.

# Validation des transporteurs et notification

## État affiché dans l’administration

La fiche affiche l’autorisation réelle de l’établissement et l’état des droits transporteur issus de l’annuaire serveur, ainsi que les catégories documentaires manquantes. Le champ historique `companies.verification_status` n’est plus présenté comme la décision d’accès : la décision enregistrée par l’administrateur est portée par `urgent_business_access` et l’accès transporteur est calculé par `urgent_carrier_ready`.

Une pièce approuvée ne valide pas automatiquement l’établissement. Une décision d’autorisation ne rend pas automatiquement les quatre catégories documentaires conformes. Les catégories RC et marchandises sont distinctes, même si une seule attestation couvre les deux ; son contenu doit être contrôlé. Les fichiers ne sont jamais dupliqués, approuvés ou reclassés automatiquement sur la foi de leur nom.

## Notification

Après une décision administrative d’autorisation, le site demande au serveur l’envoi d’un e-mail aux comptes transporteur confirmés rattachés à cette entreprise. Le serveur relit les accès effectifs : s’ils sont complets, le message annonce les accès validés ; sinon il indique une autorisation d’établissement avec inscription restant à compléter. Aucun lien de fichier ni document n’est envoyé.

Après approbation d’une pièce, un message d’activation est demandé seulement si l’ensemble des accès est effectivement valide. Un bouton « Notifier la décision au transporteur » permet de notifier une décision déjà enregistrée sans la modifier. L’e-mail est déduit du compte Auth confirmé, jamais d’un destinataire libre fourni par le navigateur. L’action est réservée aux administrateurs. Aucune IA ni dépense publicitaire déclenchée par cette notification ; les éventuels plafonds du fournisseur de mails existant restent applicables.

L’interface distingue l’acceptation du message par le fournisseur, l’envoi non confirmé et la fonction à mettre à jour. L’idempotence du fournisseur limite les doublons pour une même décision et un même état, pendant sa période de rétention. Une acceptation ne garantit pas la livraison en boîte de réception. Il n’y a pas de relance automatique persistante après échec dans cette version. Au-delà de neuf comptes transporteur rattachés, l’envoi est refusé explicitement et nécessite une prise en charge administrative.

Les changements ultérieurs réalisés uniquement par le client (acceptation des conditions, par exemple) ne déclenchent pas automatiquement une notification administrative : le bouton permet de relire l’état et d’envoyer le message adapté. Aucun déclencheur global de changement d’état ni cron n’a été ajouté.

## Activation nécessaire

Publier les fichiers statiques habituels, puis remplacer le fichier complet de la fonction Supabase `support-assistant` et cliquer sur **Deploy updates**. Version attendue : `20261028-validation-mail`. Aucune nouvelle migration SQL ni nouveau secret : réutilisation de `RESEND_API_KEY` et `REGISTRATION_ALERTS_FROM` existants. Tant que la fonction n’est pas déployée, l’interface indique qu’une mise à jour est nécessaire et ne prétend pas avoir envoyé le message.

## Forfait demandé et forfait actif

Le transporteur peut demander un autre forfait dans son compte. Ce choix est une métadonnée de demande ; il ne modifie pas `urgent_business_access`, les périodes `urgent_manual_subscriptions`, les quotas ni les règlements. L’activation d’un forfait payant utilise une fonction administrative vérifiant le crédit bancaire reçu. Le libellé client indique désormais explicitement « Soumettre ma demande de forfait à l’administration ».

Test PostgreSQL supplémentaire : passage de la demande à Premium et ajout d’un statut actif dans les métadonnées Auth ; la période Drive reste inchangée, l’écriture directe et l’auto-validation sont refusées et la sixième attribution reste refusée après les cinq consommées. Ces essais sont locaux ; les métadonnées de la base privée réelle ne sont pas accessibles à cette session.

## Contrôles

33 vérifications générales réussies, dont la notification HTTP (administrateur seul, destinataire confirmé, pas de fausse activation, catégorie manquante, fournisseur en erreur, absence de mutation métier), les permissions/quota SQL et les tests navigateur de décision et d’état documentaire. Le bouton de notification d’une décision existante a un test navigateur supplémentaire. Aucun e-mail réel envoyé par les tests. L’activation réelle de la société figurant dans la capture n’est pas déduite de ces tests : seule la lecture avec une session administrateur peut la confirmer.

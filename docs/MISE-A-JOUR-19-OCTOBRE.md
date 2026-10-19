# Mise à jour du 19 octobre — revue des dossiers et signalements

Cette version est préparée pour réduire les manipulations SQL manuelles. Aucun paiement n'est activé et aucune assurance n'est validée automatiquement.

## Intervention groupée à la reprise

1. La correction `202610190001_document_categories.sql` a été exécutée par l'utilisateur. Ne pas rejouer les migrations déjà appliquées.
2. Après sauvegarde adaptée et examen, appliquer **une seule fois** `supabase/migrations/202610190002_document_review_tools.sql`. Elle ajoute les outils de revue et les signalements dans une transaction ; elle ne reclassifie, n'approuve ni ne supprime aucun document existant.
3. Récupérer la dernière version GitHub. Dans le dossier local du site, mettre à jour `documents.js`, `marketplace.js` et `style.css`. Conserver impérativement le `config.js` local avec le pilote activé. Actualiser Ctrl+F5. Le code du suivi nécessite le nouveau schéma de signalements : appliquer la migration avant de remplacer les fichiers.
4. Dans Administration, utiliser « Corriger la catégorie / la date » sur une pièce existante. Une modification la remet en attente de revue ; les anciennes métadonnées et l'auteur de la correction sont conservés dans un journal réservé à l'administration. Contrôler puis approuver de nouveau dans sa bonne catégorie.
5. Dans l'annuaire pilote, « Voir les pièces qui bloquent » indique précisément la catégorie manquante, non approuvée, expirée ou dont la date est absente. Pour le pilote, date de fin de validité requise sur licence et assurances ; ne pas inventer de date si le document n'en fournit pas, demander la clarification correspondante.

## Situation CHRONOSS à préserver

Inscription transporteur et e-mail confirmés, entreprise rattachée et autorisation de pilote accordée par l'utilisateur. Le dossier reste bloqué tant que toutes les garanties requises du pilote ne sont pas établies.

La lecture de l'attestation Orus fournie indique une RC professionnelle pour transport en véhicules de moins de 3,5 tonnes, valable du 23/09/2026 au 22/09/2027. Cela ne prouve pas une couverture des marchandises confiées (perte, vol, avarie), ni une couverture tout tonnage. Ne pas approuver la catégorie assurance marchandises sur cette seule base. La confirmation de couverture correspondante reste à obtenir auprès de l'assureur. La licence doit aussi être vérifiée avec sa portée et sa date. Le logiciel ne vérifie pas automatiquement l'authenticité ni la suffisance juridique des pièces.

## Signalements de prestation

Une fois la course attribuée, chaque partie peut ouvrir un signalement privé de retard ou problème. Un seul signalement ouvert par auteur et course évite les doublons. Le transporteur non retenu et les tiers n'ont pas accès aux signalements. Seule l'administration peut clôturer avec une explication écrite ; l'historique reste conservé. La confirmation finale de réalisation par le client est refusée tant qu'un signalement est ouvert.

Ces outils ne déclenchent ni remboursement, ni paiement, ni annulation automatique ; ils ne remplacent pas la preuve de livraison ou les procédures contractuelles de litige.

## Tests

Les tests PostgreSQL embarqués reproduisent désormais la contrainte réelle des catégories documentaires. Ils couvrent les corrections réservées à l'administrateur, la remise en attente et la traçabilité, l'interdiction d'accès aux dossiers tiers, les dates manquantes/expirées, les offres confidentielles, l'attribution, les signalements privés et leur clôture, les quotas et le suivi ordonné.

Le parcours Chromium est relié au vrai SQL via un adaptateur de test local. Un autre test de formulaire vérifie la correction de catégorie/date, et la non-régression des écrans de comptes est également testée. Ces tests ne prouvent pas le fonctionnement de la nouvelle migration dans Supabase tant que la recette réelle n'a pas été effectuée.

## Restant avant ouverture

Recette réelle client puis transporteur admissible, preuve de livraison privée, notifications SMTP, accès OVH, contrôle des capacités de chaque transporteur pour chaque course, validation juridique, paiements et abonnements réellement administrés, facturation/TVA. Aucun agent autonome de contrôle n'a été mis en place.

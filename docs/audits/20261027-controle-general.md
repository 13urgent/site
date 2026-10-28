# Contrôle général de 13 URGENT — 27 octobre 2026

## Résultat et périmètre

32 contrôles automatisés réussis sur le code, le navigateur simulé et PostgreSQL local (PGlite). Contrôles ciblés de l’assistance et du mot de passe réussis après les corrections supplémentaires. Construction et test de la version à publier réussis.

Les tests locaux ne contactent pas les comptes réels et n’envoient pas de mail. Les vérifications en production sont séparées ci-dessous. Aucun compte, course, document, abonnement, paiement ou ticket réel n’a été créé ou modifié pendant cet audit. Aucun appel d’IA payant, nouvelle dépense publicitaire ou publication sociale n’a été déclenché.

## Vérifications réellement réalisées en ligne

- 25 fichiers HTML/JS/CSS : réponses HTTPS 200 et contenu identique à la branche publiée avant corrections ; contrôle répété après publication pour les fichiers modifiés.
- chronoss.fr et www.chronoss.fr : réponses 200, redirection HTTPS vers www ; le lien vers 13 URGENT et les trois pages de stockage liées depuis l’accueil répondent 200. Le contenu et les formulaires complets de ce site externe ne sont pas validés par cette seule lecture.
- Empreinte SHA-256 du document contractuel public identique à celle déclarée par le serveur commercial.
- 24 liens et ressources de l’accueil, administration et pages d’information : réponses HTTP 200. Ces réponses ne constituent pas une lecture complète de chaque vidéo.
- Assistance : statut 200 ; service IA, préanalyse et tickets annoncés disponibles. Version serveur observée : `20261027-replies`.
- Renouvellement documentaire : RPC publique répondant `months=6`, `enabled=true`.
- Commerce : mode commercial actif et conditions version `PRO-B2B-2026-10-23-v4`. Le statut anonyme ne vaut pas acceptation de ces conditions par un client.
- Inscription par e-mail ouverte ; confirmation d’adresse requise.
- Sans authentification, l’annuaire administratif, les documents, les profils, les coordonnées privées des courses et les tickets répondent 401.
- bright-service refuse une invocation sans authentification (401). Aucun secret d’alerte utilisé et aucun envoi de test déclenché.

L’accès HTTPS est vérifié avec le client Python et sa chaîne de confiance configurée. Le navigateur Chromium de cette session ne reconnaît pas l’autorité du proxy de l’environnement ; sa navigation réelle a donc échoué, sans désactiver TLS. Les essais navigateur sur les fichiers et API simulés sont réussis. Ce défaut du navigateur de contrôle n’est pas une preuve de défaut du certificat du site.

## Défauts trouvés et corrections

1. **Historique d’assistance tronqué à 30 demandes.** Chargement paginé de l’ensemble des demandes accessibles, avec ordre stable et protection contre les anciennes réponses de chargement. Test avec 205 dossiers, dont une ancienne demande ouverte.
2. **Lien expiré sans explication visible.** L’arrivée avec le code d’expiration affiche maintenant un message et le chemin pour demander un nouveau lien. Aucun formulaire de modification n’est ouvert par ce lien expiré.
3. **Anciennes consignes de connexion dans le serveur d’assistance.** Mise à jour vers le parcours « Mot de passe oublié ? », cohérent avec le site. Cette correction serveur doit encore être déployée dans Supabase.
4. **Clôture d’assistance avant confirmation de notification.** Le serveur corrigé enregistre d’abord la réponse en cours, demande l’envoi au vrai auteur confirmé, puis clôture seulement si l’envoi est accepté et l’enregistrement de clôture réussit. Un échec de clôture reste signalé « en cours ». Tests de refus fournisseur et de refus de clôture réussis. Cette correction serveur doit encore être déployée dans Supabase.

Le fournisseur qui accepte un e-mail ne garantit pas sa réception en boîte de réception. Les notifications identiques emploient une clé d’idempotence ; cela ne constitue pas une garantie absolue de non-duplication au-delà de la rétention du fournisseur.

## Parcours couverts par les tests locaux

Inscription professionnelle et erreurs réseau ; connexion et sessions concurrentes ; réinitialisation de mot de passe et changement de compte ; séparation public/admin ; accès aux données d’une autre entreprise refusé ; liens de fichiers privés et catégories documentaires ; préanalyse conservatrice et approbation humaine ; renouvellement à six mois calendaires et expiration plus proche ; classement des dossiers et anciennes pièces conservées.

Publication de course client/transporteur ; offres confidentielles ; attribution ; suivi ; déclaration de livraison et confirmation client ; incidents ; pagination ; courses fictives exclues des parcours réels.

Frais de plateforme à l’attribution, périodes d’abonnement et quotas ; activation par virement ; références de facturation ; relevés mensuels ; alertes et reprise après erreur ; consentement distinct pour statistiques et Google Ads ; conversion excluant admin/tests et aucun envoi avant accord ; mobile et absence d’erreurs JavaScript dans les scénarios exécutés.

## Éléments confirmés par le propriétaire, sans nouvelle exécution réelle

Le propriétaire a publié sa première course. L’inscription de test et la préanalyse documentaire avaient été confirmées précédemment. La première communication a été publiée manuellement sur LinkedIn, Instagram et TikTok, avec relais sur le profil personnel LinkedIn. Ce sont des preuves limitées à ces opérations, pas une recette de tous les comptes et cas possibles.

## Points encore non confirmés

- Réception effective d’un e-mail de réponse d’assistance et parcours complet d’un lien réel de réinitialisation jusqu’au nouveau mot de passe. L’audit ne dispose pas des boîtes mail et ne modifie pas les mots de passe des clients.
- Métadonnées complètes et journaux de la base privée en production, exécution effective des tâches planifiées, état des secrets et délivrabilité générale. La réussite des tests locaux n’atteste pas ces réglages réels.
- Réalisation d’une mission complète avec deux comptes réels et rapprochement d’un vrai virement. Ces scénarios sont testés localement ; aucune opération commerciale réelle n’a été inventée.
- Remontée d’une vraie conversion attribuée dans Google Ads, actualité des exclusions/mots clés, dépenses exactes et date de fin de campagne. La dernière date de fin montrée était le 1er novembre 2026 : elle reste à vérifier dans le compte publicitaire. Aucun accès Ads disponible dans cette session.
- Agent autonome de réseaux sociaux : non développé/connecté. Les publications actuelles sont manuelles. Aucun abonnement social ni budget supplémentaire actif du fait de cet audit.
- Veille et dépôt de marchés publics : projet futur, non installé. Aucun abonnement de ce type activé.

## Unique activation technique encore nécessaire pour les corrections de cet audit

Dans Supabase, remplacer uniquement le code complet de `support-assistant/index.ts` par la version du dépôt et cliquer sur **Deploy updates**. Version attendue ensuite : `20261027-audit`. Aucun SQL, secret supplémentaire ou changement de bright-service nécessaire.

La version statique du site et la version Supabase sont des déploiements distincts. Tant que cette fonction n’est pas mise à jour, les nouvelles consignes et la protection de clôture sont préparées mais ne sont pas exécutées en production.

## Pièces de contrôle

Rapports JSON locaux : `/workspace/13urgent-tools/audit-general-final-20261027.json`, `/workspace/13urgent-tools/audit-public-live-20261027.json`, `/workspace/13urgent-tools/audit-liens-20261027.json`. La suite générale contient 32 contrôles, tous réussis ; les tests ciblés après modification de la clôture ont également réussi. La nouvelle version construite a réussi `deployment-browser.cjs`.

## Suivi du 28 octobre 2026

Après la modification et le déploiement annoncés par le propriétaire, le point de statut réel de support-assistant répond HTTP 200 avec la version attendue `20261027-audit`, service actif et tickets disponibles. La mise à jour Supabase demandée à la fin de l’audit est donc confirmée déployée. La réception réelle des e-mails et une vraie conversion attribuée dans Google Ads restent non confirmées par ce contrôle de statut. Rapport de vérification : `/workspace/13urgent-tools/verification-assistance-20261028.json`.

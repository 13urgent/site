# Alertes lors du dépôt de documents — 29 octobre 2026

## Comportement

Une nouvelle pièce enregistrée par un compte transporteur ou donneur d'ordre rattaché à l'entreprise crée une alerte interne. Chaque pièce reçoit sa propre alerte : deux pièces déposées produisent deux messages. Aucune alerte rétroactive n'est créée pour les pièces existantes, et une approbation ou correction administrative ne déclenche pas une nouvelle alerte de dépôt.

Destinataire fixe : `saschronoss@outlook.com`. Le message indique l'entreprise, le type de compte, le compte déposant, la catégorie, le nom du fichier et les références utiles. Il renvoie vers l'administration. Aucune pièce ni URL de téléchargement privé n'est jointe. Le destinataire ne peut pas être choisi depuis le navigateur.

Le dépôt du Kbis / justificatif d'immatriculation devient disponible dans « Mes documents » pour un donneur d'ordre après activation de la migration. Il reste facultatif au regard des droits de publication existants : il ne valide ni ne suspend automatiquement l'établissement. Les quatre catégories requises des transporteurs et leurs abonnements restent contrôlés séparément. Aucun nouveau rôle ni droit d'approbation n'est accordé.

Les donneurs d'ordre peuvent déposer un Kbis dans leur propre entreprise, lire leurs pièces et envoyer un fichier dans leur propre dossier privé. La fiche doit correspondre à un fichier existant et rester `pending`, sans auteur ni date d'approbation. Les chemins invalides, pièces d'une autre entreprise, auto-approbations et catégories réservées aux transporteurs sont refusés. Les limites existantes PDF/JPG/PNG et 10 Mo restent applicables.

L'administration inclut les donneurs d'ordre dans les dossiers. Leurs fiches ne réclament pas les quatre justificatifs d'un transporteur, ni un forfait transporteur. Le dossier documentaire du donneur d'ordre est classé à partir de son justificatif d'immatriculation ; la décision d'autorisation de l'établissement reste distincte.

## Livraison et reprise

La file est enregistrée dans la même transaction que la fiche documentaire. Le travailleur déjà utilisé pour les inscriptions (`bright-service`, dont le code source est dans `supabase/functions/registration-alerts/index.ts`) traite aussi ces alertes lorsque `REGISTRATION_ALERTS_ENABLED=true`.

Chaque passage prend au plus trois pièces, avec un bail de cinq minutes et des envois parallèles bornés. Une clé d'idempotence stable par alerte limite les doublons chez Resend. Une erreur fournisseur ou réseau est enregistrée, avec temporisation exponentielle et huit tentatives maximum. Une alerte non prise en charge dans la fenêtre de 23 heures est classée en échec pour rester dans la fenêtre d'idempotence du fournisseur. Ce mécanisme ne garantit pas la réception en boîte de réception ; `sent` signifie que le fournisseur a accepté le message et que la base a enregistré son accusé.

Une interruption après acceptation fournisseur et avant accusé permet une reprise avec la même clé. Une alerte qui échoue définitivement nécessite un examen administratif ; elle n'est pas relancée indéfiniment. Les notifications de validation et les réponses d'assistance conservent leur mécanisme existant : cette nouvelle file concerne les nouveaux dépôts documentaires.

## Activation dans Supabase

1. Dans SQL Editor, exécuter une fois le fichier complet `supabase/migrations/202610290001_document_upload_alerts.sql`. Résultat attendu : `enabled=true`, `client_upload=true`, version `20261029-document-alerts`.
2. Dans Edge Functions, ouvrir **bright-service**, puis remplacer son code complet par `supabase/functions/registration-alerts/index.ts` et cliquer **Deploy updates**. Ne pas remplacer `support-assistant`. Le fichier conserve les alertes d'inscription et les rapports mensuels / statistiques existants.

Les secrets existants sont réutilisés : `REGISTRATION_ALERTS_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY`, `REGISTRATION_ALERTS_FROM`. Conserver `REGISTRATION_ALERTS_ENABLED=true`. Aucune nouvelle clé n'est nécessaire et aucun secret ne doit être copié dans le site ou le chat.

Le cron existant `urgent-registration-alerts` appelle normalement bright-service chaque minute. Sa présence et son activation doivent être contrôlées dans Supabase (aucun accès administrateur à cette configuration depuis l'environnement de développement). Si le cron n'existe pas, suivre `supabase/setup/registration-alerts-cron.sql`, qui utilise les secrets Vault déjà prévus. Ne pas créer une seconde tâche pour les documents.

Déployer la nouvelle fonction avant le SQL reste compatible : la fonction signale `documents.enabled=false`, `reason=migration_required` si la migration manque, tout en conservant les alertes d'inscription. Appliquer le SQL avant la nouvelle fonction met les alertes en attente jusqu'au déploiement ; il faut effectuer les deux étapes sans laisser dépasser la fenêtre de reprise.

## Vérification après activation

Se connecter avec un compte professionnel contrôlé et déposer une nouvelle pièce. Vérifier sa présence en attente d'examen dans l'administration, puis la réception de l'alerte à l'adresse fixe. Dans les journaux d'invocation de bright-service, `documents.sent` compte les messages acceptés, `documents.retry` les erreurs remises en attente. Une réponse HTTP 200 sans pièce en attente ne constitue pas un test de réception.

Le SQL suivant est réservé au propriétaire dans SQL Editor ; il ne révèle aucune clé :

```sql
select status, count(*) from public.urgent_document_alerts group by status;
select created_at, status, attempts, last_error_code
from public.urgent_document_alerts order by created_at desc limit 20;
select jobname, active from cron.job where jobname='urgent-registration-alerts';
```

Les essais locaux n'envoient aucun mail réel. Tests dédiés : `document-upload-alerts-sql.cjs`, `document-upload-alerts-http.cjs`, `client-documents-browser.cjs`. Les tests d'inscription et rapports existants sont conservés.

## Présentation

Fond gris bleuté avec nuances discrètes ; entête bleu nuit et accents rouges ; boutons encadrés, contraste renforcé, zones d'action d'au moins 44 pixels, état désactivé distinct et focus clavier visible. Les formulaires, cartes de courses, fenêtres de compte et administration partagent cette présentation. Aucun média payant ni image de tiers ajouté.

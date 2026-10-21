# Alertes de nouvelles inscriptions — 21 octobre 2026

## État et destination

**Code testé localement. Selon les confirmations utilisateur : fonction déployée sous `bright-service`, JWT legacy désactivé, migration appliquée et secrets Vault créés. La planification, l’activation et la réception réelle restent à vérifier.**
Destinataire demandé par CHRONOSS : **saschronoss@outlook.com**. Cette adresse est fixée côté serveur. Aucun paramètre envoyé depuis le navigateur ne peut la modifier.

Chaque nouvelle création de profil client/transporteur ajoute un travail dans une file privée. Un worker planifié chaque minute envoie un e-mail via Resend : entreprise, type de compte, e-mail, SIRET déclaré, état de confirmation de l'adresse et références. Le bouton ouvre le site ; après connexion administrateur, cliquer sur Administration. Il n'ouvre pas directement la fiche entreprise.

L'alerte n'approuve ni l'entreprise ni ses pièces, n'active aucun abonnement et ne modifie aucun droit. Aucun justificatif n'est joint. Les comptes existants ne sont pas repris et une modification de profil ne déclenche pas une nouvelle alerte.

## Installation nécessaire, une fois

L'environnement de travail n'a ni session de gestion Supabase ni identifiants d'un service d'envoi. La configuration suivante doit donc être réalisée depuis les tableaux de bord autorisés. Ne pas transmettre de mot de passe ou clé privée dans le chat.

1. Dans Resend, configurer un domaine d'envoi et les entrées DNS demandées pour `13urgent.fr`. Ne pas remplacer les MX OVH qui reçoivent le courrier. Vérifier le tarif/quota en vigueur avant activation. L'adresse de réception Outlook est indépendante du domaine d'envoi.
2. Dans le projet Supabase `rwkxkpbekvssmfnugcyn`, exécuter `supabase/migrations/202610210001_registration_alerts.sql`. Cette migration dépend des tables existantes `profiles`, `companies`, `auth.users` et des rôles Supabase standard ; elle ne dépend pas de Stripe.
3. Déployer `supabase/functions/registration-alerts/index.ts` sous le nom `bright-service` (nom conservé après création dans le tableau de bord). Ce fichier est autonome et peut être collé dans l'éditeur Edge Functions. Désactiver la vérification JWT de la passerelle pour cette fonction uniquement ; le code vérifie son propre secret Bearer. La source du code reste dans `registration-alerts/index.ts`. Pour un déploiement CLI ultérieur sous `bright-service`, préparer un dossier de fonction portant ce nom avec le même code ; ne pas déployer une seconde fonction `registration-alerts` par inadvertance. `supabase/config.toml` déclare la vérification JWT désactivée pour les deux noms.
4. Dans Edge Functions → Secrets :
   - `REGISTRATION_ALERTS_SECRET` : une valeur aléatoire de 32 caractères minimum ;
   - `REGISTRATION_ALERTS_ENABLED` : `false` pendant l'installation, puis `true` pour activer ;
   - `RESEND_API_KEY` : clé d'envoi Resend ;
   - `REGISTRATION_ALERTS_FROM` : `13 URGENT <alertes@13urgent.fr>`, seulement après vérification du domaine d'envoi.
   - `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` sont normalement fournis par Supabase au runtime ; ne jamais les copier dans config.js.
5. Activer les extensions `pg_cron` et `pg_net`, puis créer dans Supabase Vault les deux secrets indiqués dans `supabase/setup/registration-alerts-cron.sql`. Le secret de déclenchement est le même que celui de la fonction. Exécuter ensuite ce script de planification, qui traite jusqu'à cinq dossiers par minute.
6. Activer le worker et faire une nouvelle inscription de recette avec une adresse contrôlée et des informations de test clairement identifiées. Vérifier le reçu dans Outlook, l'état dans la file et les journaux fournisseur. Supprimer le compte test une fois la recette terminée. Ne pas présenter la recette locale comme un test réel d'envoi.

## Contrôle et arrêt

La file est inaccessible aux comptes anon/authenticated. Les RPC de traitement sont réservées au service serveur. Les baux de cinq minutes évitent deux traitements simultanés, et un délai progressif est appliqué aux échecs, avec huit tentatives maximum. La clé d'idempotence est stable par alerte. La fenêtre d'envoi automatique est limitée à 23 heures pour rester sous la fenêtre d'idempotence de 24 heures de Resend : les dossiers plus anciens passent en échec et doivent être examinés, pas remis en file à l'aveugle.

`sent` signifie que Resend a accepté le message, pas qu'Outlook l'a livré en boîte principale. Contrôler les rejets, spams et quotas dans le fournisseur. L'intégration n'envoie pas de rappel en cas de dossier sans traitement, et ne notifie pas encore les nouveaux dépôts de documents.

Dans SQL Editor, surveillance :

```sql
select status, count(*) from public.urgent_registration_alerts group by status;
select id,user_id,created_at,attempts,last_error_code
from public.urgent_registration_alerts where status='failed' order by created_at desc;
```

Pour suspendre : mettre `REGISTRATION_ALERTS_ENABLED=false`, puis éventuellement `select cron.unschedule('urgent-registration-alerts');`. La file reste conservée. Reprendre les alertes en attente avant 23 h ; au-delà, vérifier manuellement les inscriptions.

## Vérifications locales réalisées

- SQL sous PostgreSQL embarqué PGlite : pas de reprise historique, clients/transporteurs seulement, refus utilisateur, bail, reprise après panne, temporisation, limites.
- Handler HTTP avec réseau simulé : authentification, arrêt, destinataire fixe, échappement HTML et sujet, clé d'idempotence, erreurs réseau/fournisseur, accusé DB.

```sh
NODE_PATH=/workspace/13urgent-tools/node_modules node tests/registration-alerts-sql.cjs
node tests/registration-alerts-http.cjs
```

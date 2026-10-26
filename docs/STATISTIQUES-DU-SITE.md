# Rapport quotidien de fréquentation — 13 URGENT

Choix de l’exploitant le 26 octobre 2026 : e-mail chaque matin à **08:00, heure de Paris**, à **saschronoss@outlook.com**. Le destinataire est fixe côté serveur ; aucun destinataire n’est accepté depuis le navigateur ou le corps d’une requête. Il s’agit d’un traitement planifié déterministe, sans coût d’IA par rapport.

## Ce que mesure le rapport

- Pages vues après accord, par provenance (LinkedIn, Instagram, TikTok, Google, direct/autre) et page instrumentée.
- Nombre de comptes connectés observés après accord ; entreprise, e-mail du compte, rôle et dernière observation. Le rapport détaille au maximum 50 comptes et indique lorsque cette limite est atteinte.
- Nouvelles inscriptions et demandes réelles enregistrées dans la journée. Ces deux totaux sont issus des données métier, indépendamment du choix de mesure d’audience. Les exercices fictifs de course sont exclus.

Les affichages ne sont pas un nombre de personnes uniques. Aucun identifiant anonyme persistant, adresse IP, empreinte de navigateur ou URL complète n’est conservé par le module. Un visiteur anonyme ne peut donc pas être identifié par son nom ou son entreprise. Les pages non instrumentées, refus, bloqueurs, robots et rechargements limitent l’interprétation. Les données ne permettent pas de reconstituer des visites antérieures à l’activation.

La mesure est instrumentée sur l’accueil et certaines pages légales. Les conditions versionnées déjà acceptées restent immuables et ne sont pas modifiées. Les pages d’administration sont exclues ; les visites d’un compte identifié admin sur l’accueil sont ignorées côté serveur. Une visite anonyme de l’exploitant peut être comptée s’il accepte.

## Installation — trois opérations dans Supabase

Les secrets Supabase/Resend et le cron des alertes d’inscription existent déjà. Les conserver ; **aucune nouvelle clé privée n’est requise** et aucune clé `service_role` ne doit être ajoutée au site.

1. Dans **SQL Editor**, exécuter uniquement [la nouvelle migration](../supabase/migrations/202610260001_site_statistics.sql). Elle crée les événements et files privés, les fonctions de collecte/rapport et, si l’extension cron est déjà disponible, une purge quotidienne `urgent-site-stats-retention`. Le résultat doit indiquer `enabled=true` et `retention_scheduler_available=true`. Cette dernière colonne indique la disponibilité de l’ordonnanceur ; vérifier ensuite le job `active` avec le test ci-dessous. Ne pas rejouer toutes les migrations. Pré requis : tables `profiles`, `companies`, `auth.users.created_at`, marketplace avec `is_test`, et rôles standards Supabase.
2. Dans **Edge Functions → bright-service**, remplacer le contenu déployé par le fichier complet [registration-alerts/index.ts](../supabase/functions/registration-alerts/index.ts), puis déployer. Le fichier conserve les alertes d’inscription et rapports mensuels ; ne pas remplacer par un extrait ne contenant que les statistiques. Garder `verify_jwt=false` sur cette fonction : son secret serveur existant reste vérifié par le code.
3. Dans **Edge Functions → Secrets**, ajouter **`SITE_STATS_REPORTS_ENABLED=true`**. Garder les autres paramètres et secrets. Le cron existant `urgent-registration-alerts`, appelé chaque minute, traite désormais aussi la file quotidienne. Aucun nouvel expéditeur ni destinataire à configurer.

Le code frontend vérifie d’abord l’existence et l’activation du service de mesure. Tant que cette installation n’est pas faite, il n’affiche pas le choix et ne collecte rien. Une activation du rapport ne prouve pas encore la collecte navigateur ni la réception d’un e-mail.

## Vérification d’activation

1. Ouvrir l’accueil dans un navigateur neuf : le choix **Statistiques facultatives** doit apparaître. Cliquer sur **Refuser les statistiques** : le site doit rester utilisable. Le bouton **Gérer les statistiques** permet de changer le choix.
2. Accepter depuis un navigateur de test non administrateur. Une page vue doit être ajoutée. Le choix local est conservé 180 jours. Les signaux de confidentialité GPC/DNT désactivent la mesure. Aucune identité n’est fournie par le client : Supabase utilise exclusivement la session authentifiée pour l’associer à un compte.
3. Exécuter [le test d’envoi](../supabase/setup/test-site-statistics-report.sql). Il met en file un rapport marqué TEST pour la veille sans inventer de visites, comptes ou courses ; il peut être vide. Le cron existant doit être actif et la réception doit être constatée dans Outlook. `sent` signifie accepté par Resend, pas livraison garantie en boîte de réception. Réexécuter le test ne recrée pas un rapport déjà existant pour la même journée.
4. Si besoin, consulter `select day,status,attempts,sent_at,last_error_code from public.urgent_site_reports order by day desc limit 10;` dans SQL Editor. Ce contrôle ne révèle pas de secret.

Le premier rapport automatique normal porte sur le jour d’installation et devient éligible le lendemain à 08:00 Paris. Les changements d’heure sont calculés par PostgreSQL avec le fuseau `Europe/Paris` ; le cron traite à son passage suivant. L’heure de réception dépend aussi du fournisseur.

## Données, sécurité et limites

Tables sans accès navigateur, RLS active et droits révoqués ; seul le RPC d’enregistrement minimisé et le booléen public d’activation sont accessibles. Les événements sans accord déclaré sont ignorés et les chemins/catégories inconnus sont rejetés ou réduits à une catégorie neutre. Les données métier et l’identité sont calculées côté serveur. Aucun rôle ou identifiant d’entreprise fourni par le navigateur n’est accepté.

L’API de mesure est publique, comme les collecteurs d’audience habituels. Des appels artificiels restent possibles : les statistiques sont indicatives, pas une preuve de visite humaine. Un plafond atomique de 10 000 événements/jour limite le volume ; les totaux métier ne dépendent pas de ce plafond. Aucun choix d’accès au service n’est fondé sur ces chiffres.

Événements purgés après 30 jours, rapports de la plateforme après 90 jours. La tâche SQL de purge est indépendante du flag d’envoi ; le worker exécute aussi la purge à chaque traitement. Les copies Outlook nécessitent une gestion de conservation séparée par CHRONOSS. La notice de confidentialité décrit ces traitements ; l’ancien contenu de la v4 acceptée reste inchangé.

Une file est unique par journée, avec snapshot stable, bail de cinq minutes, clé d’idempotence Resend, huit tentatives maximum et arrêt après 23 heures. Aucun renvoi automatique d’un rapport accepté. Le rattrapage se limite aux sept journées clôturées récentes, sans rapport antérieur au `first_day` installé.

Pause des envois : `SITE_STATS_REPORTS_ENABLED=false`. Pause de la collecte et de la génération : `update public.urgent_site_stats_settings set enabled=false where id;`. La purge planifiée reste à conserver. Le rapport n’est pas public et n’ajoute aucun compteur de clients ou de chiffre d’affaires à l’accueil.

## Validation technique

`tests/site-statistics-sql.cjs` : accord, identité serveur, données minimisées, isolation, limites Paris/DST, inscriptions et demandes, exclusion des tests/admins, bail/reprises, purge et plafond.

`tests/site-statistics-http.cjs` : destinataire fixe, authentification, activation indépendante, sécurité HTML, rapport TEST, idempotence et échecs fournisseur.

`tests/site-statistics-browser.cjs` : absence de collecte avant accord et après refus, retrait et expiration, catégories, GPC, administration exclue et fonctionnement du service.

Ces tests sont locaux ; l’installation distante et la réception réelle doivent être vérifiées après les trois opérations ci-dessus.

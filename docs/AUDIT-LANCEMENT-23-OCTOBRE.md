# Audit de préparation au lancement — 23 octobre 2026

## Priorité : sécurité, puis pilote local encadré

Aucune conclusion de sécurité complète ne peut être tirée des seuls fichiers source ou de la visibilité d'un formulaire. L'inspection ci-dessous couvre le code et les migrations présents, des tests locaux PostgreSQL/navigateur, et le contenu de publication suivi dans Git. Le tableau de bord Supabase distant, les politiques historiques et les éventuelles fonctions ajoutées hors dépôt restent à auditer. Aucun secret privé n'a été demandé ou inséré côté client.

## 1. Formulaire d'import / budgets et notes privés

**Constat :** le formulaire B2PWeb/Rubiwin et ses champs budget/notes figuraient dans le HTML de `index.html`, à l'intérieur du dialogue d'administration. L'absence d'affichage visuel ne les retirait pas du HTML. Les vraies valeurs n'étaient pas préremplies dans ce fichier. `imports.js` obtenait les données depuis Supabase après un contrôle client du rôle ; la migration `202610160001_external_drafts.sql` prévoyait une RLS administrateur pour lecture/insertion/suppression. Un test local la vérifiait, mais son efficacité distante dépend notamment de la protection de `profiles.role` et `profiles.company_id`.

**Retrait préparé :** section d'import supprimée du HTML public ; référence au script supprimée ; ancien fichier `imports.js` remplacé par un module neutre pour les anciennes pages en cache. Les brouillons et archives locaux existants ne sont ni lus, ni effacés, ni publiés. Le formulaire n'est pas déplacé vers une page simplement cachée : l'import est suspendu.

**Action indispensable côté serveur :** exécuter `supabase/migrations/202610230001_admin_lockdown.sql` dans le bon projet. Le script suspend tous les accès des navigateurs à `urgent_external_drafts`, même pour les administrateurs, préserve les lignes existantes, révoque les écritures directes sur les profils (y compris droits par colonne), et limite leur lecture au compte courant ou à l'administration. Les fonctions serveur de création de compte restent possibles. Les écritures de profil depuis un navigateur sont volontairement suspendues ; le code actuel ne propose pas de modification de profil par cette voie.

**Contrôle distant complémentaire :** exécuter `supabase/setup/audit-access.sql` et examiner tous les résultats : RLS, politiques, privilèges, buckets privés et fonctions SECURITY DEFINER accessibles aux utilisateurs. Ne pas réouvrir les imports ou saisir de vrais budgets/notes avant cette revue. Il faut également contrôler les fonctions serveur éventuellement installées hors dépôt : des RPC privilégiées peuvent contourner les protections de table.

## 2. Stockage / hébergement

L'affirmation « toutes les données ne sont que dans le navigateur » ne correspond plus au déploiement configuré : `URGENT_MARKETPLACE_PILOT=true` active `marketplace.js` et désactive le chemin de démonstration locale de `app.js`. Les courses/offres/coordonnées/historiques sont gérés dans Supabase ; les documents utilisent Supabase Storage ; les alertes passent par une Edge Function et un traitement planifié. L'utilisateur a confirmé le fonctionnement distant de l'inscription, des alertes Outlook et du dépôt transporteur.

Des vestiges de démonstration et anciens exports locaux existent, avec des textes contradictoires dans le HTML. Ils doivent être traités lors d'une revue de présentation et de déploiement, sans migration aveugle des anciennes données vers de vraies courses. GitHub Pages fournit le frontend statique, Supabase la base, l'authentification et le serveur applicatif. Passer à un hébergement payant n'est pas une condition technique automatique ; quotas, sauvegardes, disponibilité, conditions des offres et coûts doivent être vérifiés pour l'exploitation réelle. La restauration et la stratégie de sauvegarde ne sont pas validées par cet audit.

## 3. CHRONOSS, exploitant et transporteur

Le texte « 13 URGENT intervient » est remplacé par l'identification explicite de CHRONOSS comme exploitant et entreprise de transport. Cela informe sur le double rôle, sans prétendre résoudre à lui seul le conflit d'intérêts.

Les administrateurs ont actuellement accès aux propositions tarifaires pour l'administration. Le code n'établit pas une séparation organisationnelle entre cette connaissance et l'activité de transport de CHRONOSS. Une promesse d'étanchéité ou d'égalité automatique n'est donc pas justifiée. Recommandation pour le démarrage : faire valider une politique et envisager de ne pas faire répondre CHRONOSS aux courses de la plateforme avant sa mise en place ; ne pas annoncer cette restriction comme déjà appliquée. La sélection par le donneur d'ordre et l'interdiction de répondre à sa propre demande sont des contrôles existants, pas une solution complète à ce conflit.

## 4. Missions B2PWeb / Rubiwin

Aucun connecteur automatique ni publication automatique n'est présent dans ce module ; il s'agissait de brouillons manuels. Cela ne constitue pas une autorisation de copie ou de republication. Les droits/conditions actuels des deux plateformes n'ont pas été vérifiés. L'import reste suspendu tant que les droits de réutilisation, les données des tiers et l'autorisation du donneur d'ordre ne sont pas établis. Aucune nouvelle republication n'a été effectuée.

## 5. Cadre légal et confidentialité

Des conditions professionnelles versionnées existent (`conditions-professionnelles-v3.html`) et identifient notamment CHRONOSS. En revanche, le pied de page ne comporte pas de pages distinctes de mentions légales et de politique de confidentialité ; l'existence des conditions ne suffit pas à traiter ces sujets.

À finaliser : mentions légales et hébergeurs ; politique de confidentialité (responsable, finalités, bases légales, sous-traitants, transferts, durées et droits) ; stockage des pièces et conservation ; information sur les prestataires d'envoi d'e-mails ; règles applicables aux éventuels outils de suivi publicitaire avant installation. Les durées de conservation et transferts effectifs ne doivent pas être inventés pour remplir une page.

Faire examiner le rôle réellement exercé par CHRONOSS par un conseil compétent en transport : négociation/organisation, choix du transporteur, contrats et facturation, assurance et responsabilités. Le libellé « mise en relation » ne suffit pas à déterminer le régime applicable. L'audit technique ne valide ni statut réglementé ni conformité juridique.

## 6. Lancement local

L'accroche publique et la zone de lancement sont recentrées sur Marseille et sa région. Préparer une cohorte d'environ dix transporteurs dont les dossiers sont examinés, identifier leur zone et leurs capacités réelles, puis accompagner quelques donneurs d'ordre locaux. Ne pas annoncer de disponibilité ou délai garanti sans dispositif réel. Le fonctionnement commercial et les parcours de support doivent être vérifiés avant les campagnes payantes.

## 7. Prix / équilibre économique

Le taux de 1,5 % HT du transport HT reste inchangé ; un transport de 500 € HT produit 7,50 € HT de frais de plateforme, avant les coûts. Cent transports de ce montant produiraient 750 € HT de frais, sans garantie de volume. Cela ne constitue pas une prévision de marge.

Des prix d'abonnement sont définis dans le code commercial et les conditions ; la page publique ne les affiche pas clairement et contient encore une mention de souscriptions non ouvertes. Définir une grille publique cohérente avec le mode réel, les périodes, quotas et règles de renouvellement, puis recueillir l'avis des transporteurs. Aucune modification des tarifs ou activation commerciale n'est incluse ici.

## Vérifications réalisées

- `tests/admin-lockdown-sql.cjs` : droits par table/colonne volontairement trop larges avant migration ; après migration, refus accès budgets/notes, refus auto-promotion et changement d'entreprise, lecture des profils limitée, création serveur conservée et données intactes. Exécution locale uniquement.
- `tests/external-drafts-browser.cjs` : section et script absents du HTML, ancien script sans réseau, administration documentaire conservée.
- Tests de non-régression du parcours courses et de l'administration documentaire.

## Séquence proposée avant lancement payant

1. Publier le retrait des imports et appliquer le verrouillage SQL.
2. Auditer les politiques et fonctions effectivement présentes dans Supabase ; vérifier les documents privés avec des comptes distincts.
3. Mettre en cohérence tous les textes et tarifs avec le mode réellement ouvert.
4. Finaliser le cadre juridique et la politique de confidentialité avec les informations vérifiées.
5. Réaliser une recette complète avec les premiers professionnels locaux, puis seulement engager le budget publicitaire.

## Résultats transmis depuis Supabase après le verrouillage

L'utilisateur a confirmé le succès de la migration. Un résultat SQL montre ensuite la RLS active sur les sept tables contrôlées et le bucket `carrier-documents` non public. Le CSV des politiques fourni dans le chat confirme :

- `urgent_external_drafts_suspended`, RESTRICTIVE, ALL, rôles anon/authenticated, USING false / WITH CHECK false : l'accès par ces rôles est effectivement suspendu indépendamment des anciennes politiques permissives.
- Profils : lecture limitée au compte courant ou à l'administration par la frontière restrictive ajoutée ; l'ancienne politique UPDATE `Update own basic profile` reste installée. Elle ne doit pas être confondue avec un privilège effectif : la migration révoque les droits d'écriture. Contrôler les privilèges réellement installés ; cette politique serait dangereuse pour les rôles et rattachements si les droits d'écriture étaient réintroduits sans contrôle des colonnes.
- Companies : lecture propriétaire/administrateur ; aucune politique d'écriture fournie dans le CSV.
- Documents : propriétaire/administrateur en lecture ; ajout par un carrier de sa propre société, statut pending et champs de revue non renseignés ; mise à jour via politique administrateur. La politique INSERT ne valide pas elle-même la concordance de `storage_path` avec le dossier de l'entreprise. Il reste à inspecter contraintes et triggers avant de conclure à un défaut exploitable ou de proposer le correctif.
- Storage : SELECT au dossier de l'entreprise transporteur ou administrateur ; INSERT au dossier de l'entreprise transporteur ; aucune politique UPDATE/DELETE fournie dans le CSV.
- Offres : lectures limitées au transporteur auteur, au propriétaire de la course et à l'administration ; coordonnées privées et courses dépendent de fonctions de contrôle à relire dans leur version réellement installée.

Les captures des privilèges des fonctions montrent les RPC métier appelables par authenticated ; cela n'accorde pas automatiquement les droits administrateur, qui doivent être vérifiés dans chaque fonction. Les workers d'alerte et fonctions internes visibles ne sont pas exécutables par anon/authenticated. `urgent_commercial_status` est appelable anonymement ; vérifier sa sortie limitée à la configuration publique et à l'acceptation du compte courant avant de l'identifier comme fuite. Aucun incident ni extraction de données privées n'est démontré par ces métadonnées.

Étape suivante : `supabase/setup/audit-profile-document-guards.sql` rassemble les fonctions de contrôle de rôle/entreprise/partie, privilèges effectifs et contraintes/triggers documentaires dans un seul tableau, sans données métier. L'audit des fonctions de mutation et les tests négatifs avec identités distinctes restent nécessaires pour une conclusion globale.

## Deuxième export Supabase : profils et lien fiche/fichier

L'export utilisateur `Untitled query (6)` confirme que `profiles / authenticated` dispose uniquement de SELECT dans les privilèges de table/colonnes exportés, et qu'aucun droit navigateur n'est accordé à `urgent_external_drafts`. Les six fonctions de rôle/entreprise/partie contrôlées utilisent l'identité `auth.uid()`, un `search_path` vide et des relations explicitement qualifiées. Les règles de partie/propriétaire restreignent effectivement leurs résultats aux entreprises concernées et à l'administration. Cela ne constitue pas encore un audit de toutes les fonctions de mutation.

Le contrôle documentaire ne dispose d'aucune contrainte ou trigger exporté liant `carrier_documents.storage_path` au dossier de `company_id` et à un objet réel de `carrier-documents`. Le navigateur a précisément le droit d'insérer ce champ. La politique existante impose l'entreprise et pending, mais ne contrôle pas ce lien. Ce défaut est établi dans les règles exportées ; aucune exploitation ni lecture d'un fichier tiers n'a été observée.

Correctif préparé, non appliqué à distance par l'assistant : `202610230002_document_file_boundary.sql`. Politique INSERT restrictive imposant le rôle carrier, sa propre entreprise, un état pending sans revue, un chemin dans son dossier sans traversée et l'existence de l'objet dans le bon bucket. Elle se cumule avec les règles existantes et ne peut pas être contournée par une autre politique INSERT permissive. Les documents existants ne sont ni changés ni supprimés ; `audit-document-file-links.sql` en vérifie les liens avec un résultat agrégé sans noms de fichier ni données personnelles. L'ancienne politique `Update own basic profile`, devenue inutile, est également supprimée pour éviter une réouverture ultérieure accidentelle.

Test PostgreSQL local `tests/document-file-boundary-sql.cjs` : fichier propre existant accepté, autre entreprise/fichier absent/chemin invalide/client/auto-approbation refusés, y compris avec une politique permissive trop large. La recette réelle d'upload devra ensuite vérifier que les permissions Storage installées autorisent bien le contrôle d'existence dans le dossier de l'entreprise.

## Regroupement de la recette après les correctifs

L'utilisateur a confirmé le succès de `202610230002_document_file_boundary.sql`. Son contrôle agrégé indique huit fiches documentaires, zéro chemin à examiner et zéro fichier introuvable. Cela confirme les liens avec les objets stockés, sans établir l'authenticité ou la couverture des pièces.

Le repli historique de `app.js` est désormais désactivé par défaut et interdit sur le domaine public, même si un drapeau de démonstration est ajouté. Si le backend de courses n'est pas activé/chargé, le formulaire de production est désactivé et affiche une indisponibilité ; aucun enregistrement local de secours. Le mode de démonstration ne reste possible qu'avec opt-in explicite sur localhost. Les formulations statiques « démonstration locale », « prototype » et « souscriptions non ouvertes » ont été remplacées par des textes décrivant le service et les conditions d'activation ; aucun mode commercial ou tarif n'est modifié.

Recette groupée locale `tools/check_launch.py` : **15 contrôles réussis sur 15**, couvrant verrouillage, lien document/fichier, alertes, inscription, trois rôles, attributions/frais/CSV, documents, effacement à déconnexion, retrait import, choix de forfait et absence de repli local en production. Un test de construction/déploiement vérifie également le domaine, le retour des e-mails, le logo et l'état des inscriptions. Les tests utilisent des bases et réseaux de simulation ; ils ne démontrent pas la totalité du comportement distant.

Pour terminer la revue des RPC réellement installées sans multiplier les requêtes, `supabase/setup/audit-consolidated-production.sql` regroupe dans un seul résultat : fonctions SECURITY DEFINER et droits d'appel, RLS, politiques, droits de tables/colonnes, paramètres de stockage, vues, triggers et état commercial. Il est en lecture seule et n'exporte pas de lignes de comptes, budgets, notes, documents ou secrets Vault. Ne pas annoncer une sécurité complète ou une ouverture commerciale validée avant examen de cet export et des vérifications restantes listées plus haut.

## Export consolidé réel : conclusions techniques et commerciales

Export utilisateur `Untitled query (7)` : 39 fonctions SECURITY DEFINER, 39 jeux de privilèges de fonctions, 32 politiques, 23 tables avec RLS, 42 privilèges de table, 110 privilèges de colonne, trois triggers, un bucket et une configuration commerciale. Aucune vue publique n'est présente dans cet export.

Les corps des **37 fonctions issues des migrations sont identiques** aux dernières définitions du dépôt après normalisation des espaces/commentaires. Les deux autres fonctions sont le déclencheur historique `create_user_profile` et `is_13urgent_admin`, examinés séparément. Le déclencheur attribue uniquement client ou carrier, jamais admin sur la base d'une métadonnée. La création des profils et le contrôle du rôle sont réalisés côté serveur. Les fonctions d'administration, abonnements, frais/avoirs, corrections de pièces, rapports et exercices fictifs disposent du contrôle administrateur ; les fonctions internes des alertes ne sont pas exécutables par anon/authenticated.

**Mode commercial réellement exporté : `enabled=false`, conditions v3.** Les frais de 1,5 % ne sont donc pas activés pour les attributions réelles à cet instant. Aucun correctif de cet audit n'active la facturation. Ne pas confondre affichage des tarifs, présence des fonctions et activation effective.

Deux durcissements supplémentaires regroupés dans `202610230003_access_and_upload_limits.sql` :

- `companies` et l'ancienne table `offers` conservent des privilèges hérités très larges pour anon/authenticated, dont TRUNCATE et TRIGGER. Les règles RLS de lecture n'accordent pas pour autant toutes les opérations métier, et une exposition exploitable par l'API REST n'est pas démontrée. Ces privilèges restent inutiles et doivent être retirés : SELECT authentifié conservé sur companies avec sa RLS, ancienne table offers suspendue sans effacement. Le site et ses fonctions utilisent `urgent_offers`.
- Bucket privé confirmé, mais `file_size_limit=null` et `allowed_mime_types=null` : les restrictions du formulaire ne sont pas imposées par la configuration de ce bucket. Configurer au maximum 10 485 760 octets et PDF/JPEG/PNG, sans élargir une éventuelle restriction préexistante plus stricte. Cela ne remplace pas une analyse du contenu ou de l'authenticité de la pièce.

**Test supplémentaire sur l'export :** `tests/exported-production-guards.cjs` recharge les 39 fonctions, rejoue les politiques et privilèges des tables principales nécessaires et applique le durcissement préparé dans une base PGlite jetable. Il vérifie 22 refus explicites d'actions administrateur pour client/transporteur, les refus anonymes, la non-approbation directe d'une pièce par son propriétaire, la non-modification du rôle, les refus de TRUNCATE après révocation, l'absence de données privées dans la réponse de configuration publique, les limites du bucket, et une inscription avec métadonnée `role=admin` qui reste client. Les colonnes historiques non sollicitées par les fonctions peuvent être représentées de façon minimale pour rejouer les ACL ; ce n'est pas une copie du schéma ou des données de production. Aucun appel de mutation n'a été effectué sur Supabase réel.

Commande de reproduction après conversion locale de l'export CSV en tableau JSON :

```sh
NODE_PATH=/workspace/13urgent-tools/node_modules node tests/exported-production-guards.cjs /workspace/supabase-audit-20261023.json
```

Les contrôles inspectés ne montrent pas d'action d'administration accordée aux comptes ordinaires par ces RPC. L'audit ne couvre pas les sessions du tableau de bord Supabase, les clés de service externes, une revue d'intrusion complète ou les conditions juridiques et opérationnelles. La validation juridique, la politique de confidentialité, la présentation des tarifs et du double rôle CHRONOSS, ainsi que la recette réelle du mode commercial restent des sujets distincts à terminer.

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

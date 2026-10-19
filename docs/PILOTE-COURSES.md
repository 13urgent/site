# Courses partagées — pilote professionnel gratuit

## État et limites

Code préparé et testé localement. La migration n'a pas été appliquée au projet distant par cette session ; aucune validation de nouvelle machine ni mise en ligne OVH n'est revendiquée. `URGENT_MARKETPLACE_PILOT` reste `false` : l'ancien parcours de démonstration est préservé. Les données locales ne sont jamais publiées automatiquement.

Le pilote permet publication B2B, propositions confidentielles, attribution unique, contacts des parties après attribution, suivi par étapes et confirmation client. Aucun prélèvement, abonnement payé, facture, e-mail automatique, confirmation d'affrètement juridiquement validée ou preuve de livraison signée n'est produit. Le montant de frais de 1,5 % est indicatif et aucun frais plateforme n'est dû dans ce pilote gratuit. Les parties confirment directement leur contrat de transport.

Les règles commerciales et juridiques d'une ouverture payante restent à valider. L'abonnement choisi à l'inscription est une demande déclarative ; il ne confère aucun accès. Les opérations en base utilisent les profils et autorisations administrateur, jamais les métadonnées utilisateur comme preuve de validation.

## Intervention groupée pour activer la recette

1. Conserver les fichiers locaux et obtenir la dernière version du dépôt. Pour éviter de mélanger des versions, utiliser un nouveau dossier extrait complet. Lancer `start-local.cmd` sous Windows (Python requis), ou `python -m http.server 8000 --bind 127.0.0.1 --directory /workspace/site` dans le cloud.
2. Examiner puis appliquer **une fois** `supabase/migrations/202610170002_marketplace_pilot.sql`, puis la correction `supabase/migrations/202610190001_document_categories.sql` dans SQL Editor du projet existant. Prévoir un export de sauvegarde adapté de la base existante avant tout changement de schéma. Le script est transactionnel, ajoute ses propres tables/fonctions et ne change pas les profils, entreprises ou documents existants. Il requiert leurs colonnes déjà utilisées par le site.
3. Après succès, mettre `window.URGENT_MARKETPLACE_PILOT = true;` dans `config.js`, puis recharger le navigateur (Ctrl+F5). Ce drapeau affiche le parcours ; il ne donne aucun droit en base. Si le schéma est absent, un message d'échec est affiché, sans repli ni publication locale cachée.
4. Connecté comme administrateur, ouvrir Administration. L'annuaire du pilote répertorie les établissements client/transporteur, leurs déclarations SIRET et leur éventuelle autorisation. Sélectionner « Préparer la décision » ; vérifier réellement au registre le SIRET, l'état de l'établissement et le représentant, puis saisir/confirmer le SIRET contrôlé, cocher l'attestation et autoriser le pilote gratuit. Ne pas autoriser un établissement non contrôlé.
5. Pour un transporteur, contrôler puis approuver les documents applicables. Le pilote accepte seulement les quatre catégories : immatriculation (`registration`), licence (`transport_licence`), assurance responsabilité civile (`insurance_rc`) et assurance marchandises (`insurance_goods`). Il s’agit du contrôle conservateur de ce pilote, pas d’une conclusion sur les obligations légales de toutes les activités. Une même attestation peut être classée dans les deux garanties uniquement après contrôle de son contenu. La pièce la plus récente de chaque catégorie doit être approuvée et non expirée à la date française. Un document approuvé puis remplacé par une pièce en attente bloque les nouvelles offres. Cette liste est volontairement restrictive ; les cas professionnels particuliers ne doivent pas être approuvés artificiellement pour contourner le contrôle.
6. Choisir explicitement le niveau de quota pilote. Start = 1, Drive = 5, Boost = 30 attributions par mois civil à Paris ; Premium = illimité. Ce décompte est un choix provisoire de recette, pas une condition d'abonnement payant. Il compte les attributions, pas les propositions, et ne s'efface pas après livraison. Aucun forfait payé n'est activé et les statuts existants d'entreprise ne sont pas modifiés.
7. Utiliser un compte donneur d'ordre distinct, vérifié et autorisé au pilote. Publier une course de test future Marseille–Lyon, 1 palette, 300 kg. Ne pas saisir de coordonnées dans les champs de ville ; seules les instructions et coordonnées du formulaire sont isolées dans une table privée.
8. Deux comptes transporteurs autorisés proposent des prix ; chacun doit voir uniquement ses propres propositions. Le client compare et sélectionne un tarif après confirmation explicite du pilote gratuit. Si le tarif a changé depuis son affichage, le serveur refuse et demande une actualisation. Un second choix sur la même course doit échouer.
9. Les coordonnées et la fiche d'attribution sont accessibles uniquement au client, au transporteur retenu et à l'administration. Le transporteur perdant ne doit pas y accéder. Le transporteur retenu effectue, dans l'ordre : départ vers enlèvement, arrivée, chargement, livraison déclarée. Le client confirme ensuite la réalisation. Ces déclarations ne remplacent pas une preuve de livraison signée.
10. Vérifier le journal horodaté. Les utilisateurs ne peuvent pas écrire directement dans les tables ni effacer l'historique. Les annulations autonomes sont limitées aux courses non attribuées ; pour une course attribuée, la gestion des incidents/annulations reste à développer et ne doit pas être traitée comme une suppression du contrat.

Pour suspendre les nouvelles opérations d'un établissement, utiliser la décision pilote « Suspendre ». Les nouvelles offres et attributions transporteur sont refusées ; les transports déjà attribués restent suivables pour éviter de perdre la continuité opérationnelle. Les échanges hors plateforme, les données volontairement placées dans les champs publics et les fausses déclarations ne sont pas détectés automatiquement.

## Sécurité et couverture locale

- RLS activé sur chaque nouvelle table. Aucun accès `anon`, aucun droit d'écriture directe pour `authenticated`.
- RPC SECURITY DEFINER avec chemins de recherche vides, contrôle du rôle serveur, société et statut. Droits EXECUTE limités à authenticated.
- Verrouillage de la course pour attribution, retrait et modification d'offre ; verrouillage de l'autorisation transporteur lors du contrôle de quota afin de sérialiser les attributions sur plusieurs courses. Vérification du montant affiché avant acceptation.
- Offres concurrentes et contacts privés masqués par la base. Journal d'événements réservé aux parties et à l'administration, avec auteur et horodatage.
- Nettoyage des données affichées au changement de session. Aucune télémétrie externe ni agent autonome installé.
- Limites d'affichage de cette version : 100 courses, 500 offres et 300 événements récents par chargement. Pagination complète et notifications à développer avant usage intensif.
- Tests PostgreSQL embarqués PGlite et parcours Chromium avec adaptateur vers ce vrai SQL. Ces tests ne valident ni le proxy Supabase, ni les permissions des tables existantes du projet distant, ni une concurrence réelle entre connexions PostgreSQL indépendantes.

Commandes (outils locaux hors dépôt) :

```
npm --prefix /workspace/13urgent-tools --cache /tmp/13urgent-npm-cache install @electric-sql/pglite@0.3.14 --no-audit --no-fund
NODE_PATH=/workspace/13urgent-tools/node_modules node tests/marketplace-pilot-sql.cjs
NODE_PATH=/workspace/13urgent-tools/node_modules:/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules node tests/marketplace-pilot-browser.cjs
```

Ne pas appliquer un `rollback` manuel qui supprimerait les tables contenant des données réelles. Pour désactiver l'interface, remettre le drapeau à false ; les données et politiques restent conservées. Les anciennes demandes locales sont exportables sans être migrées ni mélangées au pilote.

## Après la recette

Restent notamment : accès OVH, inscription complète de donneurs d'ordre, vérification officielle d'entreprise, traitement des incidents, preuve de livraison privée, notifications fiables avec SMTP, pagination, rapprochement des abonnements/paiements, conditions contractuelles, TVA et remboursements. Le site n'est pas prêt à encaisser de l'argent.

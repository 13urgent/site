# Activation des brouillons partagés

La migration `migrations/202610160001_external_drafts.sql` ajoute une nouvelle table ; elle ne modifie ni profils, ni sociétés, ni documents. Ne l'exécuter qu'une fois, dans le projet correspondant à `config.js`. Elle est transactionnelle : une erreur annule l'ensemble.

## Prérequis de sécurité

Avant activation, contrôler les politiques et privilèges de `public.profiles` : un utilisateur ne doit pouvoir modifier ni son rôle ni son entreprise. Les rôles administrateurs doivent être attribués exclusivement côté serveur. La migration s'appuie sur ce rôle existant. Sans ce contrôle, ne pas activer le partage de budgets. Les politiques existantes de profils et leur interaction avec les nouvelles règles ne sont pas vérifiées dans le projet réel.

## Exécution et recette réelle

1. Dans Supabase, sélectionner le projet `rwkxkpbekvssmfnugcyn`, ouvrir SQL Editor et exécuter la migration après vérification des prérequis.
2. Avec un compte administrateur, enregistrer un brouillon, se reconnecter depuis un second navigateur et vérifier sa présence.
3. Avec un transporteur puis un client, vérifier par API que lecture, insertion et suppression de brouillons sont refusées ; le masquage du bouton n'est pas une protection suffisante.
4. Vérifier la suppression administrateur et la copie des anciens brouillons. Les originaux locaux restent conservés. Deux copies successives doivent conserver le même nombre de lignes.

Aucune publication de course externe n'est incluse. Les abonnements, paiements et offres réelles restent désactivés. Aucune migration n'a été appliquée au projet distant par cette session.

## Tests locaux réalisés

Le SQL est exécuté sous PGlite (PostgreSQL embarqué) avec un schéma auth et profiles de test. Vérifications : écriture/lecture/suppression admin, refus transporteur/anonyme, contrainte poids négatif. Ceci ne remplace pas la recette sur le projet Supabase et ses politiques existantes.

```
npm --prefix /workspace/13urgent-tools --cache /tmp/13urgent-npm-cache install @electric-sql/pglite@0.3.14 --no-audit --no-fund
NODE_PATH=/workspace/13urgent-tools/node_modules node tests/external-drafts-sql.cjs
```

Le test navigateur utilise Playwright disponible dans l'environnement, Chromium système et une simulation de l'API :

```
python -m http.server 8000 --bind 127.0.0.1 --directory /workspace/site
node tests/external-drafts-browser.cjs
```

Le proxy de cette session refuse encore les requêtes Supabase avec CONNECT 403. Aucune clé privée n'est nécessaire dans le JavaScript public.

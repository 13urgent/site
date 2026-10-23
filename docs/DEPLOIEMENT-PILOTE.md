# Déploiement GitHub Pages — 13 URGENT

État revu le **23 octobre 2026**. Le site public est `https://13urgent.fr/`, hébergé par GitHub Pages depuis la branche `gh-pages`. Le fichier `CNAME` contient `13urgent.fr`. Le code source est sur `main` : un changement de source ne republie pas automatiquement le site.

## État confirmé

- L'utilisateur a confirmé le raccordement du domaine, HTTPS, les inscriptions professionnelles et le fonctionnement du dépôt d'une course côté transporteur.
- Le mode commercial est **actif**, confirmé par le statut serveur affiché dans l'administration et la capture utilisateur. Son état est stocké dans Supabase ; le commutateur JavaScript de marketplace ne l'active pas et ne le désactive pas.
- Les restrictions d'accès, le stockage privé et ses limites PDF/JPEG/PNG de 10 Mo ont été confirmés dans le résultat SQL fourni par l'utilisateur.
- Les alertes d'inscription et le récapitulatif mensuel ont été testés avec réception effective des e-mails. Le récapitulatif est un document préparatoire ; les factures restent émises dans l'outil CHRONOSS.
- La publication permet l'indexation : balise `index,follow`, canonical `https://13urgent.fr/`, robots et sitemap publics. Cela ne garantit aucun classement ni délai d'indexation.

L'audit de déploiement a constaté le succès de l'exécution Pages [39931917689](https://github.com/13urgent/site/actions/runs/39931917689), pour la publication `4bf6e161`. Les contrôles navigateur sur cet artefact téléchargé passent pour le domaine racine et le sous-dossier GitHub Pages. L'accès HTTPS direct au domaine reste bloqué par le proxy de l'environnement d'audit : ces tests ne constituent pas une nouvelle connexion réelle au site ou au projet Supabase.

## Construire sans refermer les inscriptions

Utiliser un **nouveau dossier vide séparé du dépôt** et conserver les deux arguments d'ouverture :

```sh
python tools/build_pilot.py --output /workspace/releases/NOUVEAU-DOSSIER-VIDE --open-registration
node tests/deployment-browser.cjs /workspace/releases/NOUVEAU-DOSSIER-VIDE open
```

La variante sans `--open-registration` masque les inscriptions ; elle n'est pas celle du site public actuel. Le constructeur active `URGENT_MARKETPLACE_PILOT`, garde `URGENT_BILLING_TEST_UI=false` et définit `URGENT_ALLOW_REGISTRATION=true` avec l'option ci-dessus. Les autorisations réelles restent contrôlées par Supabase.

**Préserver `videos/` et `CNAME` de la publication existante.** Les vidéos ne sont pas recopiées par le constructeur. Ne pas remplacer aveuglément toute la branche par le seul dossier construit : une mise à jour doit conserver les médias existants et ne modifier que les fichiers prévus. Vérifier le diff avant de pousser. Le paquet public exclut pièces justificatives, tests, documentation interne, migrations et métadonnées Git. Ne jamais y introduire de clé privée ou `service_role`.

## Publier et contrôler

1. Vérifier les tests applicables et le test de déploiement de la variante ouverte.
2. Comparer les fichiers à publier avec `gh-pages`, en préservant les vidéos, `CNAME`, `.nojekyll` et les commutateurs de production.
3. Pousser les fichiers publics sur `gh-pages` ; pousser seulement `main` ne suffit pas.
4. Attendre **Success** dans GitHub Actions pour le commit publié avant d'annoncer la mise en ligne.
5. Contrôler le site et les parcours concernés dans un navigateur. Une réussite du build ne prouve pas les droits Supabase ni une opération métier réelle.

Dans Settings → Pages, le mode attendu est **Deploy from a branch → gh-pages → / (root)**. Le domaine canonique reste `13urgent.fr` ; ne pas changer DNS, domaine ou paramètres Supabase lors d'une simple mise à jour de fichiers.

## Connexions et changements serveur

Les liens de connexion doivent revenir vers `https://13urgent.fr/`, autorisé dans Authentication → URL Configuration. Garder les URL existantes nécessaires aux environnements de recette ; le code sait également conserver `/site/` pour une publication en sous-dossier. Ne jamais copier les jetons de l'URL courante dans les paramètres de retour.

Les migrations SQL, Edge Functions et secrets Supabase sont déployés séparément du site statique. Ne pas rejouer tout le dossier de migrations : vérifier celles déjà appliquées et les résultats fournis par l'utilisateur. Le fonctionnement des notifications via Resend ne prouve pas à lui seul la configuration du SMTP d'authentification Supabase.

## Portée de la validation

Le mode commercial actif, les tests locaux et les e-mails reçus ne signifient pas que tous les parcours ont été rejoués en production. Vérifier notamment les offres confidentielles, les droits entre entreprises, une attribution réelle, les périodes payées, les quotas et les expirations documentaires. Les coordonnées légales, les engagements contractuels, la TVA applicable et le statut réglementaire doivent rester cohérents avec l'activité réelle ; ne pas présenter les tests techniques comme une validation juridique.

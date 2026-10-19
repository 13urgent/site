# Déploiement provisoire GitHub Pages

Une version statique pilote est construite depuis le code source et publiée sur la branche `gh-pages`. Cette alternative ne requiert pas de changement DNS ni d'accès FTP OVH. Le domaine 13urgent.fr reste inchangé tant qu'aucune migration de domaine n'est décidée.

## Activation du service GitHub Pages

Le réglage du dépôt doit être : Settings → Pages → Build and deployment → Source = Deploy from a branch → Branch = gh-pages → Folder = / (root) → Save. La branche contient déjà les fichiers de publication. L'URL attendue après déploiement réussi est `https://13urgent.github.io/site/` ; ce nom n'est pas une preuve que la publication est active.

L'accès API GitHub et le domaine github.io sont refusés par le proxy de cette session. La session peut pousser des commits via l'accès Git existant et lire les pages publiques github.com, mais ne peut pas confirmer ce réglage via l'API ni effectuer une requête vers le site final. L'utilisateur doit confirmer l'activation dans Pages et la réussite de l'ouverture réelle du site.

## Connexion Supabase depuis le pilote public

Les comptes existants avec mot de passe peuvent se connecter. Pour les liens par e-mail, ajouter exactement `https://13urgent.github.io/site/` à Authentication → URL Configuration → Redirect URLs, sans supprimer les adresses existantes. Les retours conservent le sous-dossier /site/ et ne recopient aucun jeton de l'adresse courante. Les envois restent soumis au quota de messagerie Supabase ; SMTP de production non configuré.

Les inscriptions sont masquées et refusées dans l'interface de publication pour éviter d'ouvrir commercialement le pilote. Cela ne désactive pas l'API d'inscription de Supabase : les protections B2B serveur et les autorisations pilote demeurent nécessaires. Ne pas considérer le masquage d'interface comme une restriction d'accès serveur.

## Contenu et sécurité

- Pilote gratuit activé dans le fichier de configuration de déploiement uniquement ; configuration locale source inchangée.
- Aucun paiement, souscription payée ou frais de service encaissé.
- Le paquet exclut les pièces jointes, fichiers PDF, tests, documentation interne, migrations SQL et métadonnées Git.
- Seule la clé publique Supabase déjà utilisée par le client est incluse. Une clé privée ou service_role ne doit jamais être introduite.
- Robots et balise noindex demandent l'absence d'indexation ; ce ne sont pas des contrôles d'accès.
- Les données sont protégées par Supabase/RLS et les fonctions serveur. L'utilisateur indique avoir appliqué la dernière migration ; la session cloud ne peut toujours pas tester son exécution réelle.
- Le contrôle documentaire n'est pas contourné : CHRONOSS doit encore justifier la garantie marchandises ; l'attestation RC reçue ne suffit pas à l'établir.

## Reconstruire une publication

```
python tools/build_pilot.py --output /workspace/releases/NOUVEAU-DOSSIER-VIDE
node tests/deployment-browser.cjs /workspace/releases/NOUVEAU-DOSSIER-VIDE
```

La publication gh-pages est une copie construite, distincte de main. Un simple changement sur main ne republie pas ce paquet : il faut le reconstruire, tester et pousser la nouvelle arborescence de publication. Ne jamais mélanger les pièces ou le dossier de tests avec les fichiers d'hébergement.

## Validation avant ouverture commerciale

Confirmer le HTTPS réel, les connexions existantes, les droits sur le projet distant, une course client/transporteur complète, les liens d'e-mail et la non-exposition des prix/contacts aux tiers. Valider ensuite les contrats, coordonnées légales, TVA, paiements et abonnements avant leur activation. Cette publication sert à la recette du pilote, pas à annoncer un service payant opérationnel.

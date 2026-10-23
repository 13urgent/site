# Séparation de l’administration et conditions v4

## Contrôle de la publication précédente

Le 23 octobre, les requêtes HTTP au domaine canonique avec et sans paramètre anticache ont retourné le même contenu : titre « Mes courses et leur suivi », liens du formulaire et du pied de page vers la v3, GitHub, Inc. et son adresse dans les mentions. La navigation Chromium dans un contexte neuf a confirmé ces trois points. Le commit gh-pages contrôlé était `17363fd046eb298a0d5f2ac287a4ee1cee41bd2d`. Ces observations ne permettent pas de déterminer pourquoi un autre navigateur affiche une ancienne version.

## Correction de l’interface

L’accueil ne contient plus `adminDialog` ni le formulaire d’accès pilote. Son lien Administration n’est affiché qu’après lecture du rôle serveur et ouvre `admin.html`. Les formulaires commerciaux administratifs sont ajoutés au DOM uniquement sur cette page et pour un administrateur. À la déconnexion, les contenus privés sont effacés et les formulaires retirés. Les droits Supabase restent indispensables : une page statique distincte n’est pas une frontière de sécurité serveur.

`admin.html` est générée par `python tools/build_admin.py` à partir de l’accueil partagé et de `tools/admin-dialog.html`. La construction publique régénère elle-même cette page ; ne pas modifier sa copie générée indépendamment.

## Conditions professionnelles

La v3 acceptée reste inchangée et archivée à son URL versionnée. La v4 `PRO-B2B-2026-10-23-v4` supprime les trois formulations éditoriales (« à confirmer […] avant publication », « ce projet », « non étudié avec le conseil »), sans modifier les tarifs, le délai contractuel de sept jours ni les clauses de TVA. La validation juridique et comptable a été confirmée par l’exploitant dans le chat ; aucune validation indépendante n’est revendiquée.

Le fichier source de la nouvelle version est `docs/juridique/CGU-CGV-v4.md`. `python tools/build_terms.py` reproduit son HTML et refuse de remplacer une v4 existante de contenu différent.

Les liens visibles suivent `urgent_commercial_status.document_url`. L’URL générique `conditions-professionnelles.html` ouvre la version en vigueur selon le serveur. Les pages de mentions et de confidentialité utilisent les seules métadonnées publiques du même RPC. Si la lecture échoue, un lien statique vers la dernière version connue reste utilisable.

## Ordre de publication et activation

1. Construire dans un dossier neuf avec `--open-registration` et valider les tests. Publier les fichiers publics sur gh-pages en préservant les vidéos et CNAME existants. Attendre la réussite GitHub Pages et vérifier que la v4 publique correspond à son empreinte.
2. **Seulement ensuite**, exécuter `supabase/migrations/202610230006_terms_v4.sql` dans le SQL Editor du projet de production. La migration change uniquement la version, l’URL et l’empreinte contractuelles ; elle ne touche ni au mode commercial, ni aux tarifs, ni aux acceptations antérieures. Une version serveur inattendue provoque un refus.
3. Vérifier le statut public : version v4, URL v4 et empreinte SHA-256 exacte. Vérifier les liens sur le site dans un contexte neuf.
4. Les membres doivent accepter expressément la v4 dans leur espace professionnel. Une acceptation v3 ne vaut pas acceptation v4 : les nouvelles propositions/attributions nécessitant la version courante sont bloquées jusqu’à cette acceptation. Les acceptations v3 restent conservées.

L’environnement ne fournit pas d’accès SQL administratif à Supabase. La migration peut être préparée et testée sous PostgreSQL embarqué, mais son application distante doit être effectuée par l’exploitant ; ne pas prétendre qu’elle a été appliquée sans contrôle du statut distant.

## Hébergeur

Adresse GitHub vérifiée dans sa [notice officielle](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). GitHub indique dans ses [conditions](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#n-communications-with-github) ne pas proposer d’assistance téléphonique ; aucun numéro non vérifié n’a été ajouté. Faire valider par le juriste si ces coordonnées et ce canal de contact satisfont les mentions attendues pour cet hébergement.

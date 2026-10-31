# Livraison documentaire du 31 octobre 2026

Source : `transport-dossier.js`, `transport-dossier.css`, migration `202610310001_transport_dossier.sql`. Points d'entrée : suivi des courses attribuées et identité/logo dans Mon espace. Les fichiers HTML sont générés depuis `tools/site-template.html`.

## Données et permissions

La préparation est réservée aux entreprises dont l’accès de test a été activé par l’administration ; aucune entreprise cliente n’est activée par défaut. Les administrateurs conservent leur accès, sans pouvoir émettre au nom d’une autre entreprise. La désactivation du test ne masque pas les versions déjà partagées. La gestion des accès est disponible dans Administration et ne change aucun forfait ni paiement.

- Identité propre à l'entreprise ; nom légal et SIRET repris des tables serveur, logo raster PNG borné à 80 Ko et 1024 px. Le navigateur convertit un PNG/JPEG local, sans adresse de logo externe.
- Documents rattachés à une mission attribuée, versions de 1 à 200 par type. Émetteur tiré de la course et du profil authentifié, pas d'une entreprise envoyée par le navigateur.
- Confirmation : donneur d'ordre seul ; brouillon privé à son entreprise et aux administrateurs, version émise aux parties.
- Préparation de lettre de voiture : transporteur attribué seul ; visible aux parties, clairement non signée. Aucun accès nouveau aux tiers, expéditeurs, destinataires ou personnes anonymes.
- Pas d'UPDATE/DELETE/INSERT direct accordé aux utilisateurs. Fonctions contrôlées, verrouillage de la course et version attendue contre les écrasements ; référence stable contre les doubles clics et réponses perdues.
- Prix d'affrètement et entreprises obtenus du serveur. Les quantités déclarées sont un état documentaire distinct ; l'origine de la demande reste inchangée.
- Instantané de l'identité et du logo dans chaque version : les changements ultérieurs ne réécrivent pas l'historique. Les logos ne sont pas répétés dans la réponse de liste ; le document complet est chargé sur demande.
- Aucune mutation des cours, offres, frais, plans, validations et notifications existants.

## PDF et mobile

L'impression PDF utilise la version enregistrée, jamais la saisie non sauvegardée. Le contenu est construit comme texte et image raster, sans interprétation du HTML utilisateur. Les données documentaires et images privées ne sont pas placées dans le cache du service worker. À la déconnexion, la fenêtre documentaire et la copie d'impression sont retirées.

L'impression dépend du navigateur de l'appareil. Le test navigateur couvre la création du contenu imprimable et un PDF de démonstration ; ce n'est pas une preuve d'impression réelle sur chaque appareil iOS/Android.

## Activation et état réel

La publication statique et l'activation SQL sont deux opérations différentes. Les nouveaux boutons restent masqués si la politique `urgent_transport_dossier_policy` n'est pas disponible. Le pack d'activation contient un seul SQL et aucune nouvelle fonction Edge. Aucun accès administrateur Supabase n'est disponible dans cet environnement.

Le circuit CHRONOSS déclaré est iRoad → X Mobile / TransFollow. Aucun connecteur à ces outils n'est actif. Voir `CONNECTEUR-IROAD-XMOBILE-TRANSFOLLOW.md` pour le cadrage. L'exemple client de lettre de voiture reste dans les fichiers joints privés et ne doit pas entrer dans la publication du site.

## Validation

- `tests/transport-dossier-sql.cjs` : rôles, absence d'accès anonyme, cloisonnement entre entreprises, visibilité brouillon/émis, identité, PNG, prix serveur, versions, quantités, reprises et clôtures.
- `tests/site-pages-browser.cjs BUILD --dossier` : serveur SQL local et sessions simulées, logo, confirmation, perte de réponse après écriture et reprise, PDF, préremplissage depuis l'affrètement, préparation chauffeur et modification du poids, mobile, déconnexion.
- `--services` sans migration documentaire : ancien parcours maintenu.
- `tests/mobile-cache.cjs` et `tests/mobile-install-browser.cjs BUILD` : cache statique, exclusion des contenus privés, installation locale et affichage.

Ces tests ne prouvent pas l'activation de la migration en production ni une signature électronique, une connexion EDI ou une impression sur téléphone physique.

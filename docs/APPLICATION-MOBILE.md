# Application mobile 13 URGENT — 29 octobre 2026

## Version réalisée

Application web installable (PWA) sur Android et iPhone : `https://13urgent.fr/mobile.html`. Elle reprend la connexion, les rôles, les comptes, les courses, les offres confidentielles, les droits de forfait et les documents du site. Aucun second compte n'est créé. Cette version s'installe depuis le navigateur, sans distribution App Store / Google Play.

Navigation fixe : Mes courses, Disponibles, Déposer, Forfaits. Les boutons Mon compte et Mes justificatifs utilisent les espaces existants. Un champ appareil photo permet de prendre un justificatif depuis le téléphone ; PDF/JPG/PNG et limite de 10 Mo conservés. Le donneur d'ordre dispose du dépôt de son justificatif d'immatriculation lorsque la migration documentaire précédente est active.

## Parcours du transporteur

1. La course doit être attribuée à son entreprise. Les règles de contrôle des documents et des forfaits restent celles du site.
2. Les adresses exactes d'enlèvement et de livraison sont saisies par l'entreprise propriétaire dans le suivi, avant le départ. Pour une ancienne course déjà commencée, les adresses encore manquantes peuvent être complétées ; les adresses existantes ne peuvent pas être changées après le départ. Elles restent privées. Sans adresse exacte, l'application demande de la faire préciser et ne présente pas un guidage vers une ville comme une destination précise.
3. Les boutons Google Maps et Waze ouvrent l'application ou le service correspondant avec l'adresse encodée. Ils ne constituent pas un calcul d'itinéraire poids lourds. Le conducteur doit vérifier les contraintes de gabarit et de poids dans son outil de navigation. Aucun suivi GPS en direct ni collecte de positions en arrière-plan n'est ajouté à 13 URGENT.
4. Le conducteur conserve les étapes du site : départ vers l'enlèvement, arrivée au chargement, marchandise chargée, livraison déclarée. La confirmation finale reste au donneur d'ordre.
5. Il peut prendre une photo ou sélectionner une photo / un PDF, choisir Photo de marchandise, Photo et réserves, ou Lettre de voiture, puis partager dans le dossier privé de la course.
6. Des réserves exigent une description de dix caractères minimum. Leur enregistrement ouvre un signalement s'il n'en existe pas déjà un pour ce déclarant. Le traitement reste administratif, et un signalement ouvert bloque la confirmation finale selon la règle existante.

Le transporteur attribué peut ajouter une copie tardive de lettre de voiture après confirmation de la réalisation. Une course annulée, non attribuée ou rangée ne permet pas un nouveau dépôt. Le rangement ne supprime pas les pièces historiques.

## Donneur d'ordre et notifications

Les pièces et leurs descriptions sont consultables par l'entreprise propriétaire, le transporteur attribué et l'administration. Le bouton d'accès produit un lien privé valable 60 secondes ; le lien n'est pas stocké dans un cache hors ligne. Une copie photographiée ou scannée n'est pas un système de signature électronique ni une certification de son authenticité.

Le chargement déclaré, la livraison déclarée et chaque pièce ajoutée créent une notification persistante pour le vrai compte créateur de la course. Le serveur relit son adresse confirmée et vérifie son rattachement à l'entreprise propriétaire. L'adresse de contact libre saisie dans un formulaire n'est pas utilisée comme destinataire. Aucun e-mail n'est envoyé pour les exercices fictifs.

Le message invite à consulter le dossier après connexion, sans pièce jointe ni lien de téléchargement public. La déclaration de livraison reste présentée comme une déclaration du transporteur, à confirmer par le donneur d'ordre. Les étapes et pièces restent également visibles sur le site classique. Dans l'onglet Mes courses de l'application, un contrôle périodique toutes les 45 secondes actualise le suivi lorsque la page est visible, connectée et sans saisie/envoi en cours. Pas de notification push système dans cette version.

Les notifications utilisent le worker `bright-service` existant et son cron. Les missions passent avant les récapitulatifs et alertes d'inscription. Trois notifications au plus sont prises à chaque passage, avec baux de cinq minutes, idempotence fournisseur, reprise temporisée, huit tentatives et fenêtre de 23 heures. Le champ `sent` signifie acceptation par le fournisseur et accusé enregistré, pas réception garantie dans la boîte du client. Les refus d'envoi et destinataires non confirmés restent comptabilisés pour reprise bornée.

## Sécurité et réseau

Le bucket `urgent-mission-files` est privé. Le serveur contrôle l'entreprise attribuée, le fichier effectivement reçu, son propriétaire, sa taille et son type, le chemin et la référence de la pièce. L'écriture directe des métadonnées est refusée. Les politiques restrictives protègent le nouveau bucket même en présence d'anciennes politiques Storage larges. Les comptes non participants et anonymes ne peuvent consulter les pièces.

La reprise d'une transmission avec réponse réseau perdue réutilise la référence de pièce ; elle ne crée pas un doublon de métadonnées ni un nouvel événement. L'interface conserve la sélection en mémoire pour réessayer tant que le formulaire reste ouvert. Il ne s'agit pas d'une file de fichiers conservés après fermeture de l'application. Un fichier reçu dans Storage mais non enregistré reste inaccessible via le dossier ; aucun nettoyage automatique de ces fichiers orphelins n'est prévu dans cette version.

Le service worker ne met en cache que la liste explicite de fichiers statiques de l'interface. Auth, Supabase, pièces privées, GPS, requêtes POST et codes de connexion sont exclus. La session reste gérée par le SDK Supabase dans le navigateur comme sur le site. La coque peut se charger hors connexion ; consulter les données à jour, envoyer les fichiers et déclarer les étapes exige une connexion internet. Aucune action n'est présentée comme envoyée hors connexion.

## Activation serveur

Le 29 octobre, la politique documentaire réelle répond `enabled=true`, `client_upload=true` ; la migration de dépôt des documents préparée précédemment est donc confirmée active. La politique des missions mobiles répond encore 404 avant activation.

1. Supabase → SQL Editor : exécuter une fois le fichier complet `supabase/migrations/202610290002_mobile_missions.sql`. Il dépend du pilote, des incidents et du rangement déjà actifs. Résultat attendu : version `20261029-mobile-missions`, `enabled=true`, `private_files=true`, `addresses=true`.
2. Edge Functions → **bright-service** → Code : remplacer le code complet avec `supabase/functions/registration-alerts/index.ts`, puis **Deploy updates**. Ne pas remplacer `support-assistant`. Les alertes d'inscription, alertes documentaires et rapports existants sont conservés. Aucun nouveau secret ni nouveau cron : conserver `REGISTRATION_ALERTS_ENABLED=true` et vérifier que le cron `urgent-registration-alerts` est actif.

La fonction reste compatible avec une base sans les nouvelles files et signale `migration_required` sans bloquer les anciennes inscriptions. Tant que la migration mobile manque, l'application explique que les outils de mission doivent être activés ; les parcours existants restent disponibles. Après le SQL, le nouveau code de bright-service est indispensable pour envoyer les notifications mises en file.

## Installation et vérification sur téléphone

- Android : ouvrir l'URL dans Chrome, utiliser Installer l'application si proposé, sinon le menu du navigateur.
- iPhone : ouvrir dans Safari, Partager, Sur l'écran d'accueil.
- Se connecter avec les comptes existants ; aucun accès à une boutique d'applications n'est nécessaire.

Après activation serveur, utiliser une course et deux comptes contrôlés pour vérifier les adresses, l'ouverture effective de Waze/Maps, la caméra du téléphone, le dépôt d'une pièce, son ouverture par le donneur d'ordre et la réception de l'e-mail. Les essais Chromium ne remplacent pas ces essais matériels ni une vérification des boîtes mail. Ne pas déclencher de fausse attribution commerciale pour ce contrôle.

## Preuves de développement

44 scénarios généraux et nouveaux scénarios réussis : permissions SQL, confidentialité, réserves, adresses figées après départ, notifications au créateur confirmé et exercices exclus ; parcours navigateur relié à PostgreSQL local avec photo et CMR ; réponse perdue et reprise idempotente ; donneur d'ordre lecteur et confirmation séparée ; service worker réellement actif sur serveur local, cache privé exclu et rechargement de l'interface hors connexion.

La version construite a aussi passé les contrôles de déploiement et d'installation navigateur. Les tests n'ont créé aucune course, photo, facture, compte ou notification réelle en production, et n'ont envoyé aucun e-mail. Rapport : `/workspace/13urgent-tools/mobile-final-checks-20261029.json`.

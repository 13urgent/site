# 13 URGENT — Étape documents et administration

## Inclus
- Authentification Supabase, profils client / transporteur / administrateur.
- Téléversement de justificatifs dans le bucket privé `carrier-documents` (PDF/JPG/PNG, 10 Mo max).
- Tableau de bord admin : visualiser les dossiers, ouvrir les fichiers via lien temporaire, accepter/refuser un document.
- Les courses et les offres restent en **démonstration locale**. Aucun transport réel, abonnement payant ou validation complète d’entreprise n’est encore opérationnel.

## Configuration
La configuration publique du projet est dans `config.js`. Ne jamais y mettre une clé secrète.
Le rôle admin doit être défini côté base ; le bouton Administration n’apparaît que pour un profil `admin`.

## Sécurité / avant mise en ligne
1. Vérifier les GRANT sur les tables, et s’assurer que seuls les admins peuvent mettre à jour les colonnes de revue.
2. Confirmer la liste complète des valeurs permises par `carrier_documents.document_type` ; l’option assurance peut nécessiter un ajustement.
3. Mettre en place une validation complète de l’entreprise (documents obligatoires, expiration), et la restriction RLS des offres.
4. Corriger les informations légales et les mentions du site avant publication.
5. Tester sur un hébergement HTTPS : les pages `file://` ne sont pas une configuration de production.

## Essai
Connectez-vous avec `exploitationchronoss@outlook.com` pour afficher « Mes documents ». Connectez-vous avec `saschronoss@outlook.com` pour afficher « Administration ». Si les comptes ne sont pas confirmés, vérifiez la boîte mail.

## Ajout : préparation de missions B2PWeb / Rubiwin
Dans « Administration », le formulaire « Importer une mission externe » permet de copier une mission et son budget interne, puis de l'enregistrer comme **brouillon local non publié**. Les transporteurs ne voient pas ces brouillons. Les données ne sont **pas synchronisées entre ordinateurs**. Aucun accès API ni republication automatique n'est inclus. Ne publier les offres de tiers qu'après obtention des droits nécessaires.

## Développement — suivi local
- Recherche par départ/destination et filtre par véhicule.
- Suivi des demandes du navigateur, annulation locale persistante et export JSON.
- Les offres sont désactivées même si le SDK Supabase ne charge pas.
- Les coordonnées et demandes locales ne sont pas isolées par compte : ne pas utiliser comme espace client de production.

Validation : parcours Chromium avec création, rechargement, recherche, filtre véhicule, téléchargement JSON et annulation après rechargement ; aucune erreur JavaScript. Pour ce test, le SDK CDN a été téléchargé avec vérification TLS puis servi au navigateur par interception de requête, car Chromium rejette le certificat du proxy. Cela ne valide pas le chargement CDN en production ni la connexion Supabase.

Blocages : le proxy de la session refuse encore la connexion au projet Supabase (CONNECT 403). Authentification réelle, politiques RLS, stockage privé et validation des rôles non testés. Accès SFTP OVH en attente du support, ticket S16949971. Aucun déploiement réalisé.

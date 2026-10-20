# Vidéos de présentation — livraison du 20 octobre 2026

Deux MP4 préparés pour diffusion après ouverture officielle : donneurs d'ordre (26 s) et transporteurs/TikTok (22 s), 1080×1920, 30 i/s, H.264/AAC. Musique synthétique originale et titres animés, pas de voix off parlée. Visuel de véhicule généré par IA, illustratif ; pas une capture du site ou une vidéo réelle de la flotte.

Les liens locaux /workspace ne permettaient pas le téléchargement par l'utilisateur. Une page de lecture et téléchargement a été ajoutée à la branche gh-pages, commit 57b9feb1e68084ce59fa89c5cf5312a5c3144dbd, sous /videos/ :

- https://13urgent.github.io/site/videos/
- https://13urgent.github.io/site/videos/donneurs-ordre.mp4
- https://13urgent.github.io/site/videos/transporteurs-tiktok.mp4
- https://13urgent.github.io/site/videos/13urgent-videos.zip

La page est accessible par lien direct, non liée depuis l'accueil, balisée noindex,nofollow ; elle est **publique**, ces balises ne sont pas un contrôle d'accès. Elle précise l'état de préparation et la diffusion prévue après ouverture officielle. Aucun réseau social n'a été utilisé pour publier les vidéos.

Recette locale : lecteurs HTML chargent les deux fichiers avec dimensions et durées attendues ; téléchargement d'un MP4 réussi dans Chromium aux largeurs 390 et 1440 px, sans débordement horizontal. Ces tests ne prouvent pas la délivrance du site distant dans le navigateur utilisateur.

Sources originales et rendus conservés dans /workspace/13urgent-videos/. Le fichier page-telechargement-videos.html est une copie du HTML publié pour faciliter sa maintenance. Les binaires sont uniquement sur gh-pages et dans le dossier de travail, pas dans main.

Attention : tools/build_pilot.py reconstruit le site de base sans inclure videos/. Tout futur déploiement doit préserver ce dossier de publication ; ne pas le supprimer lors d'un remplacement global de l'arborescence. Le constructeur refusait déjà les fichiers inconnus lors du script de publication utilisé en session ; conserver cette vérification ou intégrer explicitement les médias.

## Versions commerciales préparées le 20 octobre en vue du 21 octobre

Nouvelle page : https://13urgent.fr/videos/commerciales/ ; ZIP : https://13urgent.fr/videos/commerciales/13urgent-videos-commerciales.zip . Donneurs d’ordre 27 s (1,5 % HT sur transport HT, TVA en sus et facture mensuelle CHRONOSS), transporteurs 24 s (propositions confidentielles, forfait et activation après validation du dossier et vérification du virement).

Ces versions utilisent le même visuel illustratif IA et le logo, avec un nouveau montage de titres et musique originale. Toujours sans voix off parlée ; scripts fournis dans le ZIP. Aucune diffusion sociale automatique. Elles sont destinées à la diffusion après activation et vérification du mode commercial, actuellement laissé désactivé pour la pause de l’exploitant. Les anciens liens /site/videos/ ne sont plus la référence après raccordement : utiliser https://13urgent.fr/videos/ .

Décodage complet des deux MP4 vérifié (H.264/AAC, 1080×1920) ; scène du pourcentage contrôlée visuellement. Lecteurs et téléchargement du ZIP vérifiés dans Chromium aux largeurs mobile et ordinateur. Sources et exports conservés dans /workspace/13urgent-videos-commerciales-20261020/ .

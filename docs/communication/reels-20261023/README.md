# Kit Instagram Reels et TikTok — 23 octobre 2026

Livraison : https://13urgent.fr/videos/reels-20261023/

Nouvelle narration féminine demandée ensuite par l’exploitant : https://13urgent.fr/videos/voix-feminine-20261023/ ; voir `../voix-feminine-20261023/README.md`. Le kit initial reste disponible pour comparaison.

- Donneurs d’ordre : 25 secondes, frais de 1,5 % HT sur le prix HT du transport à l’attribution commerciale confirmée, TVA en sus.
- Transporteurs : 22 secondes, dossier et droits valides, offres confidentielles et forfaits.
- MP4 H.264/AAC, 1080×1920, 30 i/s, voix synthétique française et sous-titres intégrés. Couvertures JPEG, sous-titres SRT/VTT, textes, bios, liens UTM et crédits dans le ZIP.

Compte Entreprise dédié à 13 URGENT conseillé sur chaque réseau ; nom proposé `13 URGENT | Transport express`, identifiant souhaité `@13urgent` sous réserve de disponibilité. Aucun compte créé, aucune réservation de nom, aucun post social ni achat publicitaire effectué. Les UTM différencient les liens ; ils ne mesurent pas seuls les inscriptions. Aucun pixel de suivi ajouté au site.

La voix existante du projet est remontée depuis `https://13urgent.fr/videos/explication/13urgent-explication-reseaux.mp4`. Attribution détaillée dans `CREDITS.txt` fourni à la livraison et à reprendre dans les publications. La capture du formulaire est réalisée hors réseau avec des champs fictifs : aucune demande ni compte réel créé. La musique additionnelle est originale et synthétisée localement. Les scènes d’offres sont illustratives ; aucune disponibilité, course ou rémunération n’est garantie.

## Reproduction

Prérequis : Python, Pillow, numpy, FFmpeg avec libx264/libass, polices DejaVu. Sorties de travail dans `/workspace/13urgent-social-20261023` ; le script accepte `--root`.

Dans `production/` sous ce répertoire, placer `formulaire-exemple.png` fourni ici, `source-explication.mp4` et ses sous-titres `source-explication.srt` issus des URL publiques de la vidéo explicative. Vérifier l’empreinte de la source avec celle inscrite dans les crédits de livraison. Le logo est lu depuis `/workspace/site/assets/logo-13urgent-web.png`.

Exécuter `python docs/communication/reels-20261023/render.py`. Le script crée les scènes, les montages, la musique et les sous-titres dans le dossier de travail ; les MP4 ne sont pas placés sur main.

Contrôles : décodage intégral FFmpeg, dimensions/codecs/durées FFprobe, absence de débordement des textes à la génération, contrôle visuel du storyboard et d’images avec sous-titres, lecture et téléchargement depuis la page de livraison en largeur mobile et ordinateur. La livraison publique reste sous `videos/` sur gh-pages ; préserver ces médias lors des futures constructions.

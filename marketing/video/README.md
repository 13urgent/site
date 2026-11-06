# Capsules vidéo 13 URGENT

Générateur local de capsules verticales de 20 secondes, avec textes français, illustration du parcours, logo officiel et musique instrumentale originale synthétisée. Aucun client réel, aucune voix off et aucun service payant ne sont utilisés.

## Exécuter

Prérequis Ubuntu : Python 3.11+, `ffmpeg`, `fonts-dejavu-core` et Pillow.

```sh
python -m pip install 'Pillow>=10,<13'
python video/render_daily.py --date 2026-11-06 --topic donneurs_ordre --output output/2026-11-06
```

Le chemin de la commande est relatif au dossier parent `video`. `--topic auto` fait tourner quatre sujets : donneurs d’ordre, transporteurs, documents et particuliers. La date doit être celle du calendrier éditorial en heure de Paris. À sujets et date identiques, les visuels et les notes synthétisées sont déterministes ; les octets du fichier vidéo peuvent varier avec la version de FFmpeg.

Le résultat contient le MP4, sa couverture, un storyboard, le texte de publication, un manifeste de provenance et le rapport FFprobe. L’encodage vérifié est H.264, 1080 × 1920, 24 images/s, AAC stéréo 48 kHz, 20 secondes. Le script échoue si ces caractéristiques ne sont pas respectées.

## Ce qui doit rester clair

- Il s’agit de visuels illustrant le parcours, et non d’une capture actuelle du site. Chaque scène le précise.
- La musique est générée ici à partir d’oscillateurs, sans échantillon ni chanson existante. Elle n’est pas présentée comme une tendance vérifiée. Les musiques natives tendance de TikTok ne sont pas téléchargées ni réutilisées sur LinkedIn.
- Le logo est celui fourni pour CHRONOSS / 13 URGENT. Le projet doit conserver l’autorisation de son titulaire. Les polices DejaVu sont fournies par le système et leur licence est disponible dans le paquet Ubuntu `fonts-dejavu-core`.
- Aucun envoi ou appel à Buffer n’est effectué par ce script. Le superviseur éditorial doit vérifier le sujet contre les fonctions réellement disponibles avant programmation.
- Ce programme automatise la production de capsules à partir de modèles. Il ne constitue pas un agent IA permanent, une recherche des tendances, ni une génération quotidienne de nouvelles captures réelles du site.
- Les quotas du compte Buffer et l’hébergement public du MP4 doivent être gérés par le composant de diffusion, pas par ce générateur.

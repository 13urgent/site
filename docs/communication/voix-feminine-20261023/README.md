# Nouvelle narration féminine — 23 octobre 2026

Demande de l’exploitant : remplacer la voix jugée trop robotique par une voix féminine chaleureuse. Le montage donneurs d’ordre garde ses cinq scènes, ses 25 secondes, ses informations commerciales et le format vertical 1080×1920, H.264/AAC, 30 i/s.

Livraison : https://13urgent.fr/videos/voix-feminine-20261023/

Voix de synthèse française Microsoft `fr-FR-VivienneMultilingualNeural` produite avec `edge-tts==7.3.1`. Débit demandé -3 %, hauteur -1 Hz. Les cinq segments sont placés dans les scènes existantes sans accélération supplémentaire de l’audio. La musique instrumentale originale est réutilisée, les sous-titres sont recalés sur les limites de mots retournées par le service. Les anciens enregistrements Piper/SIWIS ne sont pas utilisés dans cette version. Aucun clonage d’une personne réelle.

Travail conservé dans `/workspace/13urgent-social-voix-naturelle-20261023`, dépendances Python dans `/workspace/13urgent-voice-tools`. `generate_voice.py` génère les segments MP3 et leurs repères, via le proxy existant. Le certificat public de la plateforme est ajouté au contexte de confiance ; la vérification TLS reste active. Aucun secret ni donnée de client envoyé : uniquement le texte de la narration.

`revoice.py` assemble les nouveaux segments sur le montage silencieux et la musique du kit précédent, dans `/workspace/13urgent-social-20261023/production`. Prérequis : Python/numpy, FFmpeg avec libass/libx264 et polices DejaVu. Les paramètres de production sont conservés dans le script ; aucune publication automatique sur TikTok ou Instagram.

Livrables : MP4, MP3 de narration seule, SRT/VTT, couverture, texte de publication actualisé, crédits et rapport technique. Les MP4/MP3 sont conservés uniquement dans le dossier de travail et sur gh-pages sous `videos/voix-feminine-20261023/`, pas sur main. Les versions précédentes restent disponibles pour comparaison.

Contrôles : décodage intégral, dimensions/codecs/durée/fréquence, niveau audio et crête, lecture du lecteur et téléchargement, absence de débordement mobile. Le caractère naturel de la voix reste à apprécier à l’écoute par l’exploitant avant publication sociale.

## Correction du niveau musical

L’exploitant signale que la musique est inaudible. Le premier mix multipliait par 0,45 une source instrumentale déjà très faible (mesurée à -41,19 LUFS). `remix_music.py`, à exécuter après `revoice.py`, normalise la musique à -23 LUFS avant une compression pilotée par la voix : la musique baisse pendant les paroles puis remonte dans les pauses. La voix et le flux vidéo sont conservés ; le MP4 corrigé utilise un nouveau nom pour éviter un téléchargement depuis un ancien cache : `donneurs-ordre-voix-feminine-musique.mp4`.

Contrôle mesuré pendant la pause finale, de 24 à 24,5 secondes : musique passée de -58,0 à -32,9 dB moyens (fondu de fin inclus). Le mix complet est mesuré à -16,98 LUFS et -1,50 dBTP ; décodage intégral réussi et flux vidéo identique à la version précédente. La page de livraison pointe désormais vers la version corrigée.

Seconde correction après retour utilisateur : remplacement du fond minimaliste par la bande pop instrumentale originale de la vidéo commerciale donneurs d’ordre (sans voix off, provenance documentée dans `docs/medias/VIDEOS.md`). `remix_pop.py` produit `donneurs-ordre-femme-pop-v3.mp4`, avec musique à -20 LUFS avant atténuation légère pendant la voix, et un MP3 de musique seule pour contrôle.

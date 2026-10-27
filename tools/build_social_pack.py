"""Prépare des supports originaux avec le logo fourni, sans service payant ni publication."""
from pathlib import Path
import json, shutil
root=Path(__file__).resolve().parents[1]
out=Path('/workspace/13urgent-social-pack');out.mkdir(exist_ok=True)
shutil.copy2(root/'assets/logo-13urgent-web.png',out/'logo.png')
shutil.copy2(root/'docs/communication/premiere-semaine-reseaux.md',out/'textes-valides.md')
subjects=[
 {'id':'01-presentation','slides':[
 ['PLATEFORME PROFESSIONNELLE','Un transport<br>à organiser ?','Découvrez 13 URGENT.'],
 ['DONNEURS D’ORDRE','Déposez.<br>Comparez.<br>Choisissez.','Votre besoin de transport.<br>Les propositions reçues.<br>Le transporteur qui vous convient.'],
 ['DÉCOUVREZ LA PLATEFORME','13urgent.fr','Mise en relation entre professionnels.<br>Dépôt de demande gratuit.']]},
 {'id':'02-preparer-sa-demande','slides':[
 ['LE CONSEIL TRANSPORT','Une palette<br>à expédier ?','Préparez ces 5 informations.'],
 ['AVANT DE PUBLIER','Trajet.<br>Date.<br>Chargement.','Départ et arrivée.<br>Date d’enlèvement.<br>Nombre de palettes ou de colis.'],
 ['POUR UN BESOIN PRÉCIS','Dimensions.<br>Poids.<br>Accès.','Ajoutez les contraintes utiles :<br>hayon, horaires, rendez-vous.'],
 ['PRÉPAREZ VOTRE DEMANDE','13urgent.fr','Informations dans le profil.<br>Service réservé aux professionnels.']]},
 {'id':'03-transporteurs','slides':[
 ['TRANSPORTEURS PROFESSIONNELS','Découvrez<br>13 URGENT.','Une plateforme de mise en relation.'],
 ['AVANT DE PROPOSER','Votre dossier.<br>Vos accès.<br>Votre forfait.','Consultez les justificatifs demandés<br>et les conditions sur le site.'],
 ['REJOIGNEZ LA PLATEFORME','13urgent.fr','Propositions soumises à un dossier<br>et à des droits d’accès validés.']]}
]
(out/'sujets.json').write_text(json.dumps(subjects,ensure_ascii=False,indent=2))
(out/'MODE-EMPLOI.txt').write_text('''PACK 13 URGENT — PREMIÈRE SEMAINE

Aucune publication effectuée, aucun compte connecté, aucun abonnement activé.
Visuels : créations typographiques originales avec le logo fourni par le propriétaire.
Aucune photo de banque d’images, musique, voix ou séquence de tiers utilisée.

PNG 1080 × 1350 : pages de carrousels Instagram ou visuels LinkedIn.
MP4 1080 × 1920 : vidéos de texte sans son, adaptées aux formats verticaux TikTok/Reels.
Sur Instagram/TikTok, le texte renvoie au profil : y ajouter le lien du site si le compte le permet.
Sur LinkedIn, coller le lien du texte fourni. Les liens dans la vidéo ne sont pas cliquables.

Commencer par la page entreprise LinkedIn CHRONOSS. Le profil personnel peut relayer les publications.
Programmation gratuite : vérifier les options disponibles dans TikTok Studio, Meta Business Suite
(compte Instagram professionnel et liaison Meta si nécessaire) et LinkedIn.
Une programmation native n’est pas un agent autonome qui surveille continuellement les nouvelles courses.
Cette automatisation reste à connecter et à réaliser ; aucun service permanent n’est actif.

Fichiers textes-valides.md : textes éditoriaux approuvés. Les supports graphiques sont des adaptations
à relire visuellement avant diffusion. Aucune actualité ni course client n’a été inventée.
''')
print(out)

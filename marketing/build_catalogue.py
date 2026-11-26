#!/usr/bin/env python3
"""Prepare 31 days × two factual editorial angles. No live trend claim."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
ANGLES={
'urgent':[
('Une palette à expédier ?', 'Rassemblez départ, arrivée, date, marchandise, poids et volume avant de présenter votre besoin.'),
('Six informations pour commencer.', 'Un besoin précis aide les transporteurs à étudier le trajet et les moyens nécessaires.'),
('Le départ et l’arrivée, clairement.', 'Indiquez les lieux de prise en charge et de livraison, puis les contraintes utiles.'),
('La bonne date fait partie du besoin.', 'Précisez les dates et les créneaux souhaités sans présenter une demande comme déjà confirmée.'),
('Poids et volume : deux repères utiles.', 'Décrivez les marchandises et leurs dimensions pour préparer une demande exploitable.'),
('Un remplacement à organiser ?', 'Présentez votre besoin ponctuel ; les transporteurs pourront l’étudier selon leurs capacités.'),
('Des offres de prix confidentielles.', 'Le donneur d’ordre étudie les propositions reçues avant de choisir celle qui convient.'),
('Choisir avant d’attribuer.', 'Le dépôt d’une demande et l’attribution sont deux étapes distinctes du parcours.'),
('Après l’attribution, les documents.', 'Préparez la confirmation d’affrètement et les documents du transport attribué.'),
('Une confirmation d’affrètement intégrée.', 'Retrouvez les informations de la mission dans un document consultable et imprimable.'),
('Votre lettre de voiture et vos logos.', 'Préparez une lettre de voiture imprimable avec les identités et logos renseignés.'),
('Conducteur et véhicule, avant le départ.', 'Le transporteur peut compléter ces informations sur la lettre de voiture préparée.'),
('Des documents prêts à imprimer.', 'La préparation des documents accompagne le transporteur avant l’exécution de sa mission.'),
('Les contraintes d’accès comptent.', 'Précisez les contraintes de chargement et de livraison dès la présentation du besoin.'),
('Un espace pour les professionnels.', '13 URGENT s’adresse aux professionnels avec SIRET et accès validé.'),
('Le dépôt d’une demande est gratuit.', 'Les frais applicables sont présentés avant attribution ; une demande ne garantit pas une offre.'),
('Les références utiles au même endroit.', 'Ajoutez les références du transport pour faciliter les échanges autour de la demande.'),
('Vos missions, aussi sur mobile.', 'Consultez les informations utiles depuis l’interface mobile de la plateforme.'),
('Une demande à étudier, puis à confirmer.', 'Attendez une proposition adaptée et les confirmations utiles avant d’organiser l’exécution.'),
('Présenter une marchandise avec précision.', 'Nature, quantité et contraintes permettent de mieux décrire votre besoin professionnel.'),
('Du besoin au dossier de transport.', 'Déposez, étudiez les propositions reçues, attribuez puis préparez les documents.'),
('Un trajet ponctuel pour votre entreprise.', 'Décrivez l’envoi et laissez les transporteurs étudier les possibilités de prise en charge.'),
('Des échanges autour d’un besoin précis.', 'Le trajet, la date et les marchandises donnent un contexte concret aux propositions.'),
],
'mon_exploit':[
('Le planning entre bureau et terrain.', 'Mon Exploit propose de regrouper planning, missions et documents utiles aux chauffeurs.'),
('Le bon document, au bon moment.', 'Retrouver le PDF d’une mission fait partie des besoins quotidiens du bureau et du terrain.'),
('La mission accompagne le chauffeur.', 'L’application permet de consulter les missions et les informations transmises au chauffeur.'),
('Signer une eCMR sur smartphone.', 'Les signatures et les documents de transport font partie du parcours présenté dans Mon Exploit.'),
('Une photo pour compléter le dossier.', 'Les justificatifs et photos peuvent accompagner les informations d’une mission.'),
('Les tournées dans leur dossier.', 'Regroupez les chargements et les récépissés de tournée dans le périmètre confirmé.'),
('Une consigne à transmettre ?', 'Les messages contribuent aux échanges entre le bureau et les chauffeurs.'),
('Un défaut véhicule à signaler.', 'Les signalements remontent les informations utiles ; ils ne constituent pas un diagnostic automatique.'),
('Le bureau et le terrain, ensemble.', 'Missions, planning et documents sont présentés dans un parcours commun.'),
('Préparer les accès de votre équipe.', 'Le nombre d’utilisateurs et les fonctions disponibles sont confirmés avant l’ouverture de l’espace.'),
('Un essai pour vérifier vos besoins.', 'L’essai de 30 jours commence à la remise effective des accès, avec accompagnement.'),
('Commencer par votre besoin réel.', 'Décrivez votre activité et les points que vous souhaitez simplifier avant de démarrer.'),
('Des PDF accessibles sur téléphone.', 'Le chauffeur retrouve les documents transmis dans l’application, avec connexion Internet.'),
('Les informations avant le départ.', 'Planning, mission et documents aident à préparer le passage du bureau au terrain.'),
('Affecter une mission à son équipe.', 'Les fonctions disponibles pour les chauffeurs et les véhicules sont confirmées avec vous.'),
('Le retour des documents au bureau.', 'L’objectif est de regrouper les pièces utiles et l’historique de la mission.'),
('Une brochure pour préparer l’échange.', 'La page présente le fonctionnement et permet de préparer une demande d’essai par e-mail.'),
('Vérifier le périmètre avant l’essai.', 'Les adaptations et raccordements éventuels sont étudiés ; aucun EDI automatique n’est promis.'),
('Moins de documents à rechercher.', 'L’objectif est de retrouver missions et pièces utiles dans un même espace, sans économie chiffrée promise.'),
('Le smartphone au service de la mission.', 'L’accès aux informations et aux documents accompagne le quotidien du chauffeur.'),
('Votre retour terrain nous intéresse.', 'Les transporteurs peuvent demander un essai accompagné et partager leurs besoins.'),
('Faire le point avant de s’équiper.', 'Consultez la brochure et présentez votre organisation avant la mise à disposition des accès.'),
('Des échanges utiles à chaque étape.', 'Une information claire entre le bureau et le chauffeur aide à préparer le travail.'),
],
'chronoss':[
('Un déménagement à préparer ?', 'CHRONOSS étudie le trajet, les objets et les accès avant toute proposition.'),
('Un canapé à transporter ?', 'Précisez ses dimensions, le départ et l’arrivée pour préparer une demande de devis.'),
('Un colis trop volumineux ?', 'Décrivez l’objet et les moyens nécessaires ; la solution est étudiée avant engagement.'),
('Vos meubles changent d’adresse.', 'Un inventaire clair aide à présenter le volume et les contraintes du projet.'),
('Les étages font partie du trajet.', 'Indiquez les étages et la présence d’un ascenseur au départ comme à l’arrivée.'),
('Mesurer avant de déplacer.', 'Les dimensions des objets et les accès sont utiles à l’étude de votre transport.'),
('Une date souhaitée à préciser.', 'Présentez votre calendrier et votre éventuelle flexibilité pour préparer l’échange.'),
('Le volume, sans deviner.', 'Listez les meubles et objets afin de décrire votre besoin le plus précisément possible.'),
('Les accès méritent une précision.', 'Escaliers, stationnement et cheminement font partie des contraintes à communiquer.'),
('Besoin de manutention ?', 'Précisez l’aide nécessaire ; les moyens sont étudiés et confirmés avant engagement.'),
('Un objet volumineux à faire voyager.', 'Poids, dimensions et conditions d’accès permettent de préparer la demande.'),
('Préparer son inventaire.', 'Une liste des objets facilite la description d’un déménagement ou d’un transport volumineux.'),
('Au départ et à l’arrivée.', 'Communiquez les deux adresses et les contraintes propres à chaque lieu.'),
('Votre demande de devis, simplement.', 'Le parcours particulier ne demande pas de compte professionnel pour présenter un besoin.'),
('Un devis avant de confirmer.', 'CHRONOSS étudie la demande ; aucun prix instantané ni transport garanti n’est annoncé.'),
('Un meuble acheté à déplacer ?', 'Décrivez l’objet, les lieux et la date avant d’organiser son enlèvement.'),
('Des objets fragiles à signaler.', 'Précisez leur nature et l’emballage prévu ; les modalités sont étudiées avant confirmation.'),
('Un projet à organiser en France.', 'Présentez le trajet et les objets ; la faisabilité est étudiée selon les moyens disponibles.'),
('Ne pas oublier les dimensions.', 'Longueur, largeur et hauteur complètent le poids et les contraintes d’accès.'),
('Vos questions avant le devis.', 'Présentez les points particuliers de votre projet pour préparer l’étude du besoin.'),
('Le transport commence par une description.', 'Départ, arrivée, date et objets sont les premières informations utiles à CHRONOSS.'),
('Un projet, puis une proposition.', 'La demande sert à étudier le besoin ; elle ne constitue pas une réservation automatique.'),
('Anticiper un déplacement volumineux.', 'Précisez ce qui doit être déplacé et les accès avant la confirmation de la prestation.'),
]}

def build():
    services=['urgent','mon_exploit','chronoss']
    assigned=[services[i%3] for i in range(62)]
    for i,service in {2:'mon_exploit',3:'urgent',8:'urgent',9:'chronoss',12:'chronoss'}.items():assigned[i]=service
    counters={s:0 for s in services};topics=[]
    for index,service in enumerate(assigned):
        n=counters[service];counters[service]+=1
        hook,body=ANGLES[service][n]
        if service=='urgent':
            url='https://13urgent.fr/deposer.html';brand='13 URGENT';conditions='Professionnels avec SIRET. Dépôt gratuit, frais présentés avant attribution. Offres selon les capacités disponibles, sans transport garanti.';tags='#Transport #Logistique #Expedition #13URGENT'
        elif service=='mon_exploit':
            url='https://13urgent.fr/mon-exploit.html';brand='MON EXPLOIT';conditions='30 jours d’essai gratuits à la remise effective des accès, sans renouvellement payant automatique. Périmètre confirmé avant ouverture. La demande prépare un e-mail à vérifier et envoyer depuis votre messagerie.';tags='#TransportRoutier #TMS #MonExploit'
        else:
            url='https://13urgent.fr/demander-un-devis.html';brand='CHRONOSS';conditions='Étude et devis avant engagement, selon les moyens disponibles. Aucun prix ni disponibilité garanti avant confirmation.';tags='#CHRONOSS #Demenagement #ColisVolumineux #Transport'
        linkedin=hook+'\n\n'+body+'\n\n'+conditions+'\n\n👉 '+url+'\n\n'+tags
        tiktok=hook+'\n\n'+body+'\n\n'+conditions+'\n\n'+url+'\nSi le lien n’est pas cliquable, saisis cette adresse dans ton navigateur.\n\n'+tags
        topics.append({'id':f'rotation-{index+1:02d}-{service.replace("_","-")}','index':index,'day_index':index//2,'slot':index%2,'service':service,'brand':brand,'hook':hook,'body':body,'cta_url':url,'linkedin':linkedin,'tiktok':tiktok,'voice_source':service,'visual_style':index%4,'palette':(index//2)%4,'scene_labels':[hook,body],'claim_basis':'Fonctions et parcours confirmés par le propriétaire ; aucune performance ou disponibilité garantie.'})
    provided=ROOT/'particuliers_drafts.json'
    if provided.exists():
        drafts=json.loads(provided.read_text());moving=[t for t in topics if t['service']=='chronoss'][:2]
        for topic,draft in zip(moving,drafts):
            topic['cta_url']=draft['destination_url'];topic['linkedin']=draft['text']+'\n\nÉtude et devis avant engagement, selon les moyens disponibles.'
            topic['tiktok']=draft['text']+'\nÉtude et devis avant engagement. Si le lien n’est pas cliquable, saisis l’adresse dans ton navigateur.'
            topic['scene_labels']=draft['suggested_video_scenes'];topic['caption_origin']=draft['id']
    return {'schema_version':2,'prepared_on':'2026-11-26','starts_on':'2026-11-27','cycle_days':31,'topics_per_day':2,'status':'catalogue_editorial_prepare','limitations':['Rotation éditoriale préparée ; aucune veille autonome des tendances.','Les pistes CHRONOSS utilisent la voix validée du parcours particulier (déménagement/colis volumineux), sans narration trompeuse sur un transport express.','Les sources voix sont préexistantes et approuvées ; seule une musique instrumentale originale est ajoutée en fond.'],'topics':topics}

if __name__=='__main__':
    data=build();(ROOT/'rotation_catalogue.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'topics':len(data['topics']),'services':{s:sum(t['service']==s for t in data['topics']) for s in ANGLES}}))

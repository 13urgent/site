"""Build the public, curated 13 URGENT presentation catalogue; no network calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def topic(identifier, audience, feature, hook, body, founder_intro, cta, scenes,
          landing_url="https://13urgent.fr/", tags="#Transport #Logistique #13URGENT"):
    page = f"{hook}\n\n{body}\n\n{cta}\n{landing_url}\n\n{tags}"
    founder = f"{hook}\n\n{founder_intro}\n\n{body}\n\n{cta}\n{landing_url}\n\n{tags}"
    tiktok = f"{hook} {cta}\n{landing_url}\n{tags}"
    return {
        "id": identifier, "audience": audience, "feature": feature,
        "landing_url": landing_url, "linkedin_founder": founder,
        "linkedin_page": page, "tiktok": tiktok, "scenes": scenes,
        "cta": cta,
        "claim_basis": "Fonction décrite dans le brief produit CHRONOSS / 13 URGENT du 6 novembre 2026 ; aucune mesure de performance revendiquée.",
    }


TOPICS = [
    topic(
        "deposer-transport", "donneur_ordre", "depot_course",
        "Un transport à organiser ? Commencez par une demande précise.",
        "Sur 13 URGENT, les professionnels dont l’accès est validé peuvent déposer un besoin de transport, recevoir des offres confidentielles et attribuer la course.",
        "Avec CHRONOSS, nous développons 13 URGENT pour faciliter ces échanges entre professionnels.",
        "Découvrez comment déposer votre demande.",
        ["Un transport à organiser ?", "Précisez le départ et l’arrivée", "Décrivez les marchandises et les contraintes", "Recevez les offres et choisissez", "13urgent.fr · Découvrez la plateforme"],
    ),
    topic(
        "remplacement-ponctuel", "donneur_ordre", "demande_remplacement",
        "Un remplacement transport à organiser ?",
        "Présentez votre besoin ponctuel sur 13 URGENT : trajet, date, marchandise et contraintes. Les transporteurs peuvent étudier la demande et proposer leur tarif, selon leur disponibilité.",
        "Les imprévus font partie de l’exploitation. Nous avons conçu un espace pour présenter clairement le besoin.",
        "Décrivez votre besoin sur 13 URGENT.",
        ["Un remplacement à organiser ?", "Indiquez le trajet et la date", "Ajoutez volume, poids et contraintes", "Étudiez les offres reçues", "13urgent.fr · Présentez votre besoin"],
    ),
    topic(
        "consulter-demandes", "transporteur", "consultation_demandes",
        "Transporteurs : cherchez des demandes adaptées à votre activité.",
        "Une fois votre accès validé sur 13 URGENT, consultez les demandes et étudiez les trajets, les dates et les marchandises avant de proposer votre tarif, selon votre forfait.",
        "Notre objectif avec 13 URGENT : permettre aux transporteurs d’identifier les besoins qu’ils peuvent réellement prendre en charge.",
        "Découvrez l’espace transporteur.",
        ["Transporteur : quelle est votre activité ?", "Consultez les demandes disponibles", "Vérifiez trajet, dates et marchandise", "Proposez votre tarif selon votre forfait", "13urgent.fr · Découvrez l’espace transporteur"],
    ),
    topic(
        "offres-confidentielles", "donneur_ordre", "offres_privees",
        "Comparer des offres de transport dans un espace dédié.",
        "Sur 13 URGENT, les offres de prix sont confidentielles. Le donneur d’ordre peut étudier les propositions reçues avant d’attribuer son transport.",
        "Nous voulons garder les échanges commerciaux utiles et structurés au même endroit.",
        "Découvrez le parcours d’une demande.",
        ["Votre demande de transport", "Les transporteurs étudient le besoin", "Les offres de prix restent confidentielles", "Vous étudiez puis attribuez", "13urgent.fr · Découvrez le parcours"],
    ),
    topic(
        "attribution-transport", "donneur_ordre", "attribution",
        "De la demande de transport à son attribution.",
        "Déposez votre besoin, échangez avec les transporteurs et choisissez une proposition. 13 URGENT permet ensuite de préparer les documents du transport attribué.",
        "Avec 13 URGENT, nous rapprochons les étapes qui suivent une demande de transport.",
        "Découvrez comment organiser votre prochain transport.",
        ["Déposez un besoin précis", "Échangez avec les transporteurs", "Choisissez une proposition", "Préparez les documents après attribution", "13urgent.fr · Découvrez le fonctionnement"],
    ),
    topic(
        "confirmation-affretement", "donneur_ordre", "confirmation_affretement",
        "Votre transport attribué, préparez sa confirmation d’affrètement.",
        "13 URGENT intègre la préparation de la confirmation d’affrètement. Retrouvez les informations du transport dans un document que le transporteur peut consulter et imprimer.",
        "Les documents font partie du travail quotidien. Nous les avons intégrés au parcours de 13 URGENT.",
        "Découvrez les documents intégrés à la plateforme.",
        ["Le transport est attribué", "Préparez la confirmation d’affrètement", "Retrouvez les informations de la mission", "Un document consultable et imprimable", "13urgent.fr · Découvrez les documents"],
    ),
    topic(
        "lettre-voiture-logo", "donneur_ordre", "lettre_voiture_logo",
        "Une lettre de voiture aux couleurs de votre entreprise.",
        "Préparez une lettre de voiture imprimable depuis 13 URGENT, avec les logos renseignés dans les espaces d’identité. Les informations du transport restent regroupées pour préparer la mission.",
        "Nous avons voulu des documents utiles sur le terrain, avec une place pour l’identité de votre entreprise.",
        "Découvrez la préparation de la lettre de voiture.",
        ["Préparez votre lettre de voiture", "Retrouvez les informations du transport", "Affichez les logos renseignés", "Imprimez le document pour la mission", "13urgent.fr · Découvrez les documents"],
    ),
    topic(
        "conducteur-vehicule", "transporteur", "conducteur_vehicule",
        "Préparer le conducteur et le véhicule avant le départ.",
        "Le transporteur peut compléter les informations du conducteur et du véhicule sur la lettre de voiture préparée dans 13 URGENT, puis imprimer le document pour la mission.",
        "Un document préparé doit rester utile à celui qui effectue le transport. C’est l’un des points que nous avons intégrés.",
        "Découvrez la préparation des documents côté transporteur.",
        ["Un transport vous est attribué", "Ouvrez la lettre de voiture", "Complétez conducteur et véhicule", "Imprimez votre document avant le départ", "13urgent.fr · Découvrez le parcours transporteur"],
    ),
    topic(
        "acces-mobile", "transporteur", "interface_mobile",
        "13 URGENT s’utilise aussi depuis votre mobile.",
        "Consultez la plateforme depuis votre téléphone pour retrouver vos demandes et vos missions. L’interface mobile permet de garder les informations utiles à portée de main.",
        "Au bureau ou sur le terrain, l’accès aux informations doit rester pratique. Nous avons prévu une interface mobile.",
        "Découvrez 13 URGENT sur votre téléphone.",
        ["Au bureau ou sur le terrain", "Ouvrez 13 URGENT sur votre mobile", "Retrouvez vos demandes et vos missions", "Consultez les informations utiles", "13urgent.fr · Découvrez l’interface mobile"],
    ),
    topic(
        "profil-professionnel", "transporteur", "identite_professionnelle",
        "Transporteurs : préparez votre identité professionnelle.",
        "Renseignez votre entreprise et les justificatifs demandés sur 13 URGENT. La validation de l’accès et les conditions applicables restent nécessaires avant de proposer vos services.",
        "Nous souhaitons des échanges entre professionnels identifiés. Compléter son dossier est une première étape utile.",
        "Découvrez les étapes de l’inscription transporteur.",
        ["Vous êtes transporteur ?", "Renseignez votre entreprise", "Complétez les justificatifs demandés", "Finalisez les étapes de validation", "13urgent.fr · Découvrez l’inscription"],
    ),
    topic(
        "devis-demenagement", "particulier", "devis_demenagement",
        "Un déménagement à préparer ? Décrivez votre projet.",
        "CHRONOSS propose une demande de devis sur 13 URGENT, sans compte professionnel. Précisez les adresses, les dates, le volume et les conditions d’accès pour permettre l’étude de votre besoin, selon les disponibilités.",
        "Nous ouvrons aussi un parcours de demande de devis aux particuliers, avec CHRONOSS.",
        "Présentez votre projet pour demander un devis.",
        ["Un déménagement à préparer ?", "Précisez départ, arrivée et dates", "Décrivez le volume et les accès", "Votre besoin est étudié avant le devis", "13urgent.fr · Demandez un devis CHRONOSS"],
        landing_url="https://13urgent.fr/demenagement.html",
        tags="#Demenagement #Transport #13URGENT",
    ),
    topic(
        "devis-colis-volumineux", "particulier", "devis_colis_volumineux",
        "Un meuble ou un colis volumineux à transporter ?",
        "Décrivez votre demande de devis CHRONOSS sur 13 URGENT : dimensions, poids, photos et conditions d’accès. La demande est étudiée avant proposition, selon les disponibilités.",
        "Un objet encombrant mérite une demande précise. Notre parcours permet de présenter les informations utiles à l’étude du transport.",
        "Décrivez votre objet pour demander un devis.",
        ["Un objet encombrant à transporter ?", "Indiquez ses dimensions et son poids", "Ajoutez les informations d’accès", "Une étude avant toute proposition", "13urgent.fr · Demandez un devis CHRONOSS"],
        landing_url="https://13urgent.fr/demander-un-devis.html",
        tags="#ColisVolumineux #Transport #13URGENT",
    ),
]


def build_catalogue():
    return {
        "schema_version": 1,
        "brand": "13 URGENT",
        "operator": "CHRONOSS",
        "prepared_on": "2026-11-06",
        "status": "catalogue_editorial_prepare_non_publie",
        "review_mode": "controle_deterministe_du_brief_et_des_formats",
        "limitations": [
            "Ce catalogue est une sélection éditoriale préparée ; il ne constitue pas un agent IA permanent.",
            "Aucune veille réelle des tendances ni mesure actuelle de performance n’a été exécutée pour ces sujets.",
            "Le validateur contrôle des règles explicites ; il ne certifie ni le fonctionnement de la production ni l’exhaustivité des faits.",
            "Aucun envoi, aucune programmation et aucune dépense ne sont effectués par ces fichiers.",
        ],
        "topics": TOPICS,
    }


if __name__ == "__main__":
    output = ROOT / "catalogue.json"
    output.write_text(json.dumps(build_catalogue(), ensure_ascii=False, indent=2) + "\n")
    print(f"{len(TOPICS)} sujets préparés : {output}")

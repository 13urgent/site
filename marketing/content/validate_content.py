"""Deterministic editorial checks. This is not a factual or AI certification."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_URLS = {
    "https://13urgent.fr/",
    "https://13urgent.fr/demenagement.html",
    "https://13urgent.fr/demander-un-devis.html",
}
AUDIENCES = {"donneur_ordre", "transporteur", "particulier"}
FEATURES = {
    "depot_course", "demande_remplacement", "consultation_demandes", "offres_privees",
    "attribution", "confirmation_affretement", "lettre_voiture_logo", "conducteur_vehicule",
    "interface_mobile", "identite_professionnelle", "devis_demenagement", "devis_colis_volumineux",
}
PROHIBITED = (
    "transport garanti", "transporteur garanti", "courses garanties", "livraison garantie",
    "réponse garantie", "revenu garanti", "revenus garantis", "tarif instantané",
    "devis instantané", "réservation instantanée", "signature ecmr", "edi intégré",
    "stock intégré", "comptabilité intégrée", "tendance du moment", "meilleur prix garanti",
    "leader français", "numéro un", "n°1", "sans frais", "100 % gratuit",
)
TEXT_FIELDS = ("linkedin_founder", "linkedin_page", "tiktok")


def validate_catalogue(catalogue):
    errors = []
    if not isinstance(catalogue, dict):
        return ["La racine doit être un objet JSON."]
    if catalogue.get("schema_version") != 1:
        errors.append("schema_version doit être 1.")
    topics = catalogue.get("topics")
    if not isinstance(topics, list):
        return errors + ["topics doit être une liste."]
    if len(topics) != 12:
        errors.append("Le catalogue doit contenir exactement 12 sujets.")
    identifiers, features = set(), set()
    public_count = 0
    for index, item in enumerate(topics):
        prefix = f"Sujet {index + 1}"
        if not isinstance(item, dict):
            errors.append(prefix + " doit être un objet.")
            continue
        identifier = item.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
            errors.append(prefix + " : identifiant invalide.")
        elif identifier in identifiers:
            errors.append(prefix + " : identifiant dupliqué.")
        identifiers.add(str(identifier))
        audience = item.get("audience")
        if audience not in AUDIENCES:
            errors.append(prefix + " : public invalide.")
        public_count += audience == "particulier"
        feature = item.get("feature")
        if feature not in FEATURES:
            errors.append(prefix + " : fonction absente du brief autorisé.")
        features.add(str(feature))
        url = item.get("landing_url")
        if url not in ALLOWED_URLS:
            errors.append(prefix + " : URL de destination non autorisée.")
        elif audience == "particulier" and url == "https://13urgent.fr/":
            errors.append(prefix + " : un particulier doit être orienté vers le parcours devis.")
        for field in TEXT_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(prefix + f" : {field} vide ou invalide.")
                continue
            limit = 350 if field == "tiktok" else 900
            if len(value) > limit:
                errors.append(prefix + f" : {field} dépasse {limit} caractères.")
            if len(value.splitlines()[0]) > 120:
                errors.append(prefix + f" : accroche {field} trop longue.")
            if url not in value:
                errors.append(prefix + f" : destination manquante dans {field}.")
            urls = re.findall(r"https?://[^\s]+", value)
            if len(urls) != 1 or any(candidate not in ALLOWED_URLS for candidate in urls):
                errors.append(prefix + f" : {field} doit contenir un seul lien approuvé.")
            parsed = urlsplit(urls[0]) if urls else None
            if parsed and (parsed.query or parsed.fragment or parsed.username):
                errors.append(prefix + f" : paramètres de lien non autorisés dans {field}.")
            if re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?:\+33|0[1-9])(?:[ .-]?\d){8}", value):
                errors.append(prefix + f" : coordonnées privées potentielles dans {field}.")
        scenes = item.get("scenes")
        if not isinstance(scenes, list) or not 4 <= len(scenes) <= 5:
            errors.append(prefix + " : prévoir 4 à 5 scènes.")
        elif any(not isinstance(scene, str) or not scene.strip() or len(scene) > 80 for scene in scenes):
            errors.append(prefix + " : scène vide, invalide ou trop longue.")
        cta = item.get("cta")
        if not isinstance(cta, str) or not cta.strip():
            errors.append(prefix + " : appel à l’action manquant.")
        if not isinstance(item.get("claim_basis"), str) or not item["claim_basis"].strip():
            errors.append(prefix + " : fondement éditorial manquant.")
        combined = " ".join(str(item.get(field, "")) for field in TEXT_FIELDS)
        combined += " " + " ".join(str(scene) for scene in scenes or [] if isinstance(scenes, list))
        folded = combined.casefold()
        for phrase in PROHIBITED:
            if phrase in folded:
                errors.append(prefix + f" : promesse ou fonction à exclure ({phrase}).")
        if re.search(r"\d\s*(?:€|%|clients|transporteurs|courses|minutes)", folded):
            errors.append(prefix + " : chiffre commercial non vérifié.")
    if public_count > 2:
        errors.append("Deux sujets particuliers au maximum.")
    if not FEATURES.issubset(features):
        errors.append("Certains sujets métier requis sont absents.")
    for name in ("limitations", "review_mode", "status"):
        if not catalogue.get(name):
            errors.append(f"Mention de transparence manquante : {name}.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=str(Path(__file__).with_name("catalogue.json")))
    args = parser.parse_args()
    try:
        catalogue = json.loads(Path(args.path).read_text())
    except (OSError, ValueError) as exc:
        print(f"Catalogue illisible : {exc}")
        return 1
    errors = validate_catalogue(catalogue)
    if errors:
        print("REFUS ÉDITORIAL\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print(f"OK — {len(catalogue['topics'])} sujets conformes aux règles déclarées. Aucun envoi effectué.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

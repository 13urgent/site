# 13 URGENT — plateforme professionnelle en développement

Site statique HTML/CSS/JavaScript avec Supabase pour les comptes, les justificatifs et les brouillons externes. Logo et interface adaptés aux ordinateurs et mobiles. Service particuliers non ouvert.

**Les paiements, abonnements payés et réservations commerciales ne sont pas activés.** Le taux de mise en relation envisagé pour les donneurs d'ordre professionnels est de 1,5 % HT du tarif HT du transport. Les conditions contractuelles et la TVA restent à valider.

## Démarrer

Sous Windows : extraire le dépôt complet, conserver les dossiers `assets`, puis lancer `start-local.cmd` (Python installé dans PATH). Garder la fenêtre ouverte et saisir l'adresse indiquée dans le navigateur. Ne pas utiliser `file://` pour valider les connexions.

Dans l'environnement cloud :

```
python -m http.server 8000 --bind 127.0.0.1 --directory /workspace/site
```

La configuration publique Supabase est dans `config.js`. Ne jamais y placer une clé secrète ou service_role. Les rôles autorisés sont définis par la base, pas par le formulaire ou les métadonnées utilisateur.

## Deux modes distincts

- **Démonstration locale (défaut)** : `URGENT_MARKETPLACE_PILOT = false`. Les courses sont conservées uniquement dans le navigateur. Les offres réelles restent désactivées. Le choix Start/Drive/Boost/Premium dans le compte est une demande déclarative, sans abonnement actif.
- **Pilote partagé gratuit** : après migration et autorisation des établissements, `URGENT_MARKETPLACE_PILOT = true` permet publication, propositions confidentielles, sélection et suivi. Aucune perception de frais ou confirmation d'affrètement automatique. [Procédure complète et limites](docs/PILOTE-COURSES.md).

Les comptes et documents Supabase ainsi que les brouillons externes partagés ne dépendent pas de ce commutateur. Le stockage des documents utilise le bucket privé `carrier-documents`, PDF/JPG/PNG jusqu'à 10 Mo ; son fonctionnement requiert les politiques existantes de stockage et de tables.

## Administration et vérifications

L'administration est réservée aux profils serveur `admin`. Accepter un document ne valide pas toute l'entreprise. Les attestations de validité, les autorisations transport et le registre doivent être réellement contrôlés. Une immatriculation saisie ou une case cochée ne constitue pas une vérification indépendante.

Le pilote ajoute une autorisation propre, distincte des états existants et des abonnements. Les documents doivent être approuvés et valides au moment d'une offre et d'une attribution. Aucune mise à jour des comptes existants, de leurs rôles ou des anciennes courses locales n'est effectuée automatiquement.

## Ressources

- [Déploiement provisoire GitHub Pages](docs/DEPLOIEMENT-PILOTE.md)

- [Mise à jour du 19 octobre — une intervention groupée](docs/MISE-A-JOUR-19-OCTOBRE.md)
- [État réel du projet et blocages](docs/AVANCEMENT.md)
- [Pilote des courses et offres — migration groupée, contrôles et tests](docs/PILOTE-COURSES.md)
- [Ouverture professionnelle et SIRET](supabase/OUVERTURE-PRO.md)
- [Recette d'inscription](docs/recette-inscription-professionnelle.md)
- [Brouillons B2PWeb/Rubiwin](supabase/README.md)
- [Relance du ticket OVH](docs/relance-ovh-S16949971.md)

Les migrations sont ordonnées et à appliquer une seule fois après inspection ; certaines ont déjà été exécutées dans le projet de l'utilisateur. Ne pas rejouer tout le dossier aveuglément. Les tests utilisent PostgreSQL embarqué PGlite et Chromium ; ils ne remplacent pas la recette sur le projet distant, les essais de concurrence multi-connexions, le SMTP de production ni le contrôle juridique.

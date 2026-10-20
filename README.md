# 13 URGENT — plateforme professionnelle en développement

Site statique HTML/CSS/JavaScript avec Supabase pour les comptes, les justificatifs et les brouillons externes. Logo et interface adaptés aux ordinateurs et mobiles. Service particuliers non ouvert.

**Les paiements, abonnements payés et réservations commerciales ne sont pas activés.** Le taux de mise en relation envisagé pour les donneurs d'ordre professionnels est de 1,5 % HT du tarif HT du transport. Les conditions contractuelles et la TVA restent à valider.

## Publication actuelle

Le domaine `13urgent.fr` est raccordé à GitHub Pages avec HTTPS, selon les vérifications utilisateur. Les inscriptions professionnelles sont ouvertes à sa demande le 20 octobre ; les droits d’accès restent contrôlés par Supabase et l’administration. **Conserver `--open-registration` lors des prochaines constructions** ; le défaut du constructeur reste fermé par précaution. Préserver les dossiers `videos/` et le fichier `CNAME` lors de la publication. L’ouverture des inscriptions ne change pas le mode commercial en base.

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

## Conditions professionnelles en préparation

Le modèle retenu pour les donneurs d’ordre est désormais le cumul mensuel des frais de 1,5 % HT, puis une facture unique de fin de mois. [Projet de CGU/CGV CHRONOSS](docs/juridique/CGU-CGV-PROJET.md), [règles mensuelles à implémenter](docs/juridique/FACTURATION-MENSUELLE-CADRE.md) et [validations restantes](docs/juridique/VALIDATION-AVANT-PUBLICATION.md). Ces documents ne sont pas publiés ni applicables au pilote gratuit ; le parcours mensuel est implémenté et testé localement ; la migration distante et la recette avant ouverture restent nécessaires.

## Mise à jour du 20 octobre — virements et facturation CHRONOSS

Le module manuel est implémenté et testé localement : périodes payées, contrôle documentaire et quotas, frais à 1,5 %, cumul mensuel et export pour l'outil existant. [Installation groupée et état réel](docs/MISE-A-JOUR-20-OCTOBRE.md). Une migration distante reste nécessaire ; ni l'ouverture commerciale ni le domaine ne sont modifiés automatiquement. La variante `--open-registration` prépare les inscriptions publiques ; la variante par défaut les garde masquées pendant l'attente OVH.

## Mode d’exploitation retenu

Factures émises avec l’outil CHRONOSS existant ; abonnements transporteurs réglés par virement et activés manuellement après rapprochement et vérification documentaire. [Décisions et écarts techniques à traiter](docs/OUVERTURE-MANUELLE.md). Le module Stripe ci-dessous reste désactivé et ne constitue plus un préalable au démarrage.

## Préparation des paiements

Un module Stripe **test uniquement** est préparé, désactivé par défaut. Il sépare les abonnements et les frais de 1,5 % sans encaisser le prix du transport. Aucun paiement ne valide les documents ou les accès. [Branchement sécurisé, recette et conditions restantes](docs/PAIEMENTS-TEST.md).

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

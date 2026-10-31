# 13 URGENT — plateforme de transport entre professionnels

Site HTML/CSS/JavaScript publié sur **https://13urgent.fr/** avec Supabase pour les comptes, les documents et la marketplace. Service réservé aux professionnels ; particuliers et applications mobiles ne sont pas ouverts.

## État confirmé au 23 octobre 2026

- Site sur GitHub Pages avec domaine et HTTPS confirmés par l'utilisateur ; inscriptions professionnelles ouvertes et indexation autorisée.
- **Mode commercial actif**, confirmé par le statut serveur de l'administration. Frais de service de **1,5 % HT du montant HT du transport**, enregistrés à l'attribution commerciale, cumulés pour la facturation mensuelle. Le transport reste facturé directement par le transporteur au donneur d'ordre.
- Abonnements transporteurs par **virement et activation manuelle** après rapprochement du règlement et vérification documentaire. Aucun prélèvement automatique ; Stripe reste désactivé.
- Protections d'accès et stockage documentaire privé limitant les fichiers aux PDF/JPEG/PNG de 10 Mo confirmés par les résultats SQL utilisateur.
- Alertes d'inscription et récapitulatif mensuel installés, activés et testés avec réception réelle. Le relevé du mois clôturé est prévu le 1er du mois à partir de 8 h, heure de Paris, avec HTML imprimable et CSV. Il prépare la facturation ; il n'émet pas de facture et n'envoie rien aux clients. [Fonctionnement et exploitation](docs/RECAPITULATIF-MENSUEL.md).

Ces confirmations ne remplacent pas la recette complète en production ni la validation du cadre juridique. Les tests locaux utilisent des données simulées ; ne pas annoncer tous les parcours vérifiés sur la seule base de leur réussite.

## Publication

`main` contient le source ; **`gh-pages` contient les fichiers réellement publiés**. Une modification sur `main` ne met pas automatiquement le site à jour.

```sh
python tools/build_pilot.py --output /workspace/releases/NOUVEAU-DOSSIER-VIDE --open-registration
node tests/deployment-browser.cjs /workspace/releases/NOUVEAU-DOSSIER-VIDE open
```

Conserver `--open-registration` et l'argument de test `open` : le constructeur ferme les inscriptions par défaut. **Préserver `videos/` et `CNAME` déjà présents dans `gh-pages`** ; les vidéos ne sont pas copiées par le constructeur. Contrôler le diff, publier uniquement les fichiers prévus puis attendre le succès GitHub Pages. [Procédure de déploiement](docs/DEPLOIEMENT-PILOTE.md).

Les migrations SQL, Edge Functions et secrets Supabase sont distincts de la publication statique. Ne pas rejouer aveuglément des migrations déjà appliquées, modifier le mode commercial ou changer de domaine pendant une simple actualisation.

## Développement local

Sous Windows : conserver les dossiers du dépôt et lancer `start-local.cmd` avec Python installé. Dans l'environnement cloud :

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory /workspace/site
```

Ne pas utiliser `file://` pour tester les connexions. La configuration publique est dans `config.js` ; n'y placer aucune clé secrète ou `service_role`. Le fichier source garde `URGENT_MARKETPLACE_PILOT=false` ; la construction publique l'active explicitement. Une configuration manquante bloque le formulaire en production plutôt que d'enregistrer une course seulement dans le navigateur. La démonstration locale exige `URGENT_LOCAL_DEMO=true` et une adresse localhost ; elle n'est pas le mode d'exploitation public.

Les administrateurs accèdent à la gestion via le lien **Administration**, qui ouvre `admin.html` après vérification de leur rôle serveur. Le panneau n’est plus inclus dans l’accueil. Après modification de la présentation partagée, régénérer la page locale avec `python tools/build_admin.py` ; le constructeur public le fait automatiquement.

La version 4 des conditions est préparée avec une migration d’activation distincte : [corrections et ordre de publication](docs/CORRECTIONS-PUBLICATION-23-OCTOBRE.md). Sa présence dans les fichiers ne signifie pas qu’elle est déjà la version contractuelle active dans Supabase.

## Accès, documents et facturation

Les rôles viennent de la base. L'administration est réservée aux profils serveur `admin`. Une immatriculation saisie, un document accepté ou un règlement enregistré ne suffisent pas à valider automatiquement toute l'entreprise. Vérifier le registre, les autorisations et les garanties ; les pièces doivent être approuvées et valides au moment des opérations qui les exigent.

Le commutateur JavaScript historique `URGENT_MARKETPLACE_PILOT` ouvre le module partagé ; il ne signifie pas que le service est gratuit. Le **mode commercial vient de Supabase**. Les droits et quotas dépendent des accès autorisés, des périodes payées et de la validité documentaire. La publication d'une demande n'entraîne pas de frais d'attribution. Un transporteur qui agit comme donneur d'ordre conserve les frais de ce rôle en complément de son abonnement.

Factures et avoirs sont émis dans l'outil CHRONOSS existant. Le relevé mensuel distingue frais, régularisations, références déjà facturées et suivi des abonnements pour éviter une double facturation. La TVA doit être déterminée dans l'outil de facturation selon la situation réelle. Les conditions professionnelles acceptées sont versionnées ; ne pas modifier rétroactivement leur document immuable sans nouvelle version et procédure d'acceptation.

## Statistiques privées

Le module de mesure facultative et le rapport quotidien à 08:00 Paris sont préparés. Ils nécessitent une activation Supabase distincte ; la présence du code ne prouve pas la collecte ou la réception d’un e-mail. [Installation et contrôle des statistiques](docs/STATISTIQUES-DU-SITE.md). Aucun compteur de clients ou de chiffre d’affaires n’est ajouté à l’accueil.

## Vérifications

```sh
python tools/check_launch.py
```

Les contrôles utilisent PostgreSQL embarqué PGlite et Chromium ; les dépendances doivent être installées dans l'environnement. Ils ne remplacent pas les essais avec des comptes réels, la concurrence entre connexions, les contrôles d'e-mails, les réglages distants et le conseil juridique. L'outil n'appelle pas le projet Supabase de production.

## Documentation

- [Audit de lancement du 23 octobre](docs/AUDIT-LANCEMENT-23-OCTOBRE.md)
- [Récapitulatif mensuel et surveillance](docs/RECAPITULATIF-MENSUEL.md)
- [Facturation manuelle — installation initiale du 20 octobre](docs/MISE-A-JOUR-20-OCTOBRE.md)
- [Choix du fonctionnement manuel](docs/OUVERTURE-MANUELLE.md)
- [Ouverture professionnelle et SIRET](supabase/OUVERTURE-PRO.md)
- [Recette d'inscription](docs/recette-inscription-professionnelle.md)
- [Historique du pilote partagé](docs/PILOTE-COURSES.md)
- [Paiements Stripe de test, désactivés](docs/PAIEMENTS-TEST.md)

Les documents datés décrivent parfois un état antérieur à l'ouverture commerciale. Utiliser l'état confirmé ci-dessus et les résultats de recette récents pour préparer une mise à jour ; conserver les réserves qui n'ont pas été effectivement levées.

### Services CHRONOSS, devis et capacités nationales

Le gabarit partagé est `tools/site-template.html` ; les contenus des nouvelles pages
sont dans `tools/service_pages.py`. Générer les pages avec `tools/build_site_pages.py`,
`tools/build_admin.py` et `tools/build_mobile.py`, puis construire le site avec
`tools/build_pilot.py --output CHEMIN_EXTERIEUR --open-registration`.
Les fichiers HTML publics sont générés. Voir `docs/SERVICES-FRANCE.md` pour les
frontières d'accès, l'activation SQL/Edge et les tests. L'ouverture aux particuliers
porte sur les demandes de devis CHRONOSS sans SIRET ; elle ne modifie pas les droits
des comptes professionnels et n'effectue aucune réservation ou facturation automatique.

### Dossier transport (première étape)

Identité/logo, confirmations versionnées et préparations de lettres de voiture : [livraison et limites](docs/produit/DOSSIER-TRANSPORT-LIVRAISON.md). [Feuille de route](docs/produit/ROADMAP-TRANSPORT.md) et [circuit iRoad / X Mobile / TransFollow](docs/produit/CONNECTEUR-IROAD-XMOBILE-TRANSFOLLOW.md). Activation séparée par la migration `202610310001_transport_dossier.sql` ; aucune e-CMR signée ou synchronisation fournisseur n’est activée par ce code.

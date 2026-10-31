# 13 URGENT — feuille de route transport

Établie le 31 octobre 2026 à la demande de Haeckel. Cette feuille de route décrit le produit cible, pas des fonctions toutes disponibles.

## But

Réutiliser les données d'une mission depuis la demande jusqu'aux pièces transport et à la comptabilité. Un commerçant conserve un parcours simple ; un exploitant dispose de fonctions métier supplémentaires. Les droits et abonnements ne seront jamais déduits des seuls boutons visibles.

## État et livraisons

1. **Fondations existantes** : demandes professionnelles, devis particuliers, offres confidentielles, attribution, suivi partagé, dépôts privés, réserves et photos, application web mobile et notifications. Leur présence ne prouve pas l'arrivée de chaque futur e-mail ni le fonctionnement de chaque compte privé.
2. **Livraison documentaire du 31 octobre** : code et migration `202610310001_transport_dossier.sql`. Identité et logo PNG privé de chaque entreprise, confirmation préremplie par le donneur d'ordre, brouillon ou version émise, préparation de lettre de voiture par le transporteur avec chauffeur/véhicule/quantités/réserves, références client/ordre, conservation des versions et impression PDF. Activation SQL distincte et accès de test accordés entreprise par entreprise par l’administration requis. Aucun paiement, signature, contrat signé ou EDI simulé.
3. **Connexion iRoad / X Mobile / TransFollow** : identification exacte des interfaces et licences ; environnement de test ; correspondances de références ; préparation de mission ; retour des statuts et PDF signé original ; idempotence des échanges, reprise après panne et journal de preuves. Non connectée à ce stade.
4. **Flotte** : fiches véhicules, types/capacités, documents et échéances, affectations historisées, disponibilités et remplacement en tournée. Les données nécessaires aux rendez-vous seront partagées avec des droits explicites, pas exposées à tout inscrit.
5. **Facturation / comptabilité** : rôles comptables séparés, pro formas, factures à numérotation unique, avoirs, pièces d'achat photographiées et rapprochement. Cadrage fiscal et intégration de facturation électronique selon obligations applicables avant lancement. Ne pas confondre facture CHRONOSS plateforme et transport facturé par le transporteur.
6. **Rentabilité** : carburant (litres, montant et kilomètres), péages, entretien, assurances, location, rémunération et kilomètres à vide ; coûts au km et marge estimée. Qualité et complétude des données visibles. Un ticket isolé ne prouve pas une consommation exacte.
7. **Tournées / messagerie / EDI** : positions, étiquettes et scans, départ/retour, souffrances, alertes ; un partenaire/format EDI pilote avant généralisation ; dédoublonnage, accusés techniques et métier, journal des rejets.
8. **Logistique** : clients, articles, unités, lots si requis, emplacements, réceptions et sorties, préparation, mouvements immuables, inventaires et corrections tracées. Pas de stocks négatifs silencieux ni de quantité déduite sans mouvement.
9. **Appels d'offres** : consultations privées, date de clôture, pièces, confidentialité des réponses, choix motivé. Les marchés publics constitueront un chantier distinct avec sources officielles et règles de réutilisation.
10. **Qualité documentaire et avis** : rappels semestriels et dates d'expiration, file d'analyse et escalade, décision humaine traçable ; avis uniquement sur prestations réellement réalisées, une évaluation par partie/prestation, droit de réponse et modération. Validité documentaire et notes commerciales restent distinctes.

## Sécurité transversale

- Cloisonnement par entreprise, rôle, mission et finalité. Invitation limitée pour expéditeur/destinataire/comptabilité ; aucune URL publique permanente vers des pièces privées.
- Jetons de partage à durée limitée, révocables, sans données personnelles dans l'URL ; nouvelle analyse et migration avant d'ouvrir des accès sans compte.
- Géolocalisation limitée au périmètre et à la durée prévus, informations du chauffeur, permissions du téléphone et comportement d'arrière-plan iOS/Android vérifiés.
- Versions émises et documents signés conservés ; corrections par nouvelle version ; preuves de signatures conservées avec le fichier d'origine.
- Plan de conservation par catégorie, sauvegardes séparées, restauration testée, surveillance et journal d'accès. Le simple stockage cloud n'est ni une sauvegarde suffisante ni un archivage probant.
- L'IA prépare et signale ; elle ne fabrique pas les signatures, ne modifie pas silencieusement une attribution et ne prend pas de décision financière ou documentaire sans règle explicite.

## Chiffrage et abonnements à construire

Aucun tarif existant n'est changé par cette livraison. Avant de fixer les nouveaux abonnements :

| Poste | Mesure pour établir le coût |
|---|---|
| Base, stockage et sauvegardes | entreprises, missions/mois, taille des PDF/photos, durée de conservation et tests de restauration |
| IA documentaire | pages analysées, tokens et taux de reprise/validation humaine |
| Signatures / e-CMR | conditions réelles des licences iRoad, X Mobile et TransFollow, coût par document/utilisateur |
| Cartographie et suivi | utilisateurs actifs, fréquence des points, durée des missions et fournisseurs |
| EDI | coût d'ouverture par partenaire, format, volume, support et engagements |
| Facturation électronique | raccordement et coûts de la plateforme agréée retenue |
| Exploitation / support | supervision, incidents, assistance, disponibilité et délais d'intervention |

Prix à étudier : socle plateforme, module Exploitation, module Gestion, module Logistique, options EDI et services à usage mesuré. Ne pas annoncer de prix définitif sans ce calcul.

## Commercialisation

Une vidéo par action réellement disponible, avec données fictives : demander un transport, émettre l'affrètement, préparer le chauffeur, récupérer le PDF signé, retrouver les factures, suivre un véhicule et gérer les stocks. Chaque vidéo doit correspondre à une livraison activée et testée. Ne pas annoncer aujourd'hui une e-CMR intégrée, de la facturation complète, de l'EDI ou une gestion de stock opérationnels.

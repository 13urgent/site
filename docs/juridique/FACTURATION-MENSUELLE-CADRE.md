# Cadre de facturation mensuelle et protections à implémenter

**Spécification de travail — 19 octobre 2026. Aucun frais réel créé par ce document.**

Exploitant : CHRONOSS, SAS à associé unique, capital de 12 600,00 €, siège au 27 Boulevard Charles Moretti, 13014 Marseille, RCS Marseille 918 710 393, selon le Kbis fourni à jour au 7 octobre 2026. Le SIRET déclaré 91871039300052 n’est pas indiqué dans cet extrait ; son rattachement reste à confirmer. Numéro de TVA intracommunautaire communiqué par l’exploitant : FR60918710393. Contact et réclamations : contact@13urgent.fr (échange aller-retour montré par l’utilisateur). Régime fiscal applicable et compte bancaire au nom de l’Exploitant restent à confirmer. Le choix du prestataire de paiement reste ouvert ; le compte Qonto peut être conservé. Aucun IBAN ni secret n'est enregistré dans ces documents.

## Décision de modèle

Le donneur d'ordre professionnel publie gratuitement et paie 1,5 % HT du transport HT pour chaque mise en relation aboutie. Les frais s'accumulent sur le mois civil à l'heure de Paris. Une facture regroupe les frais à la clôture du mois, avec échéance proposée à 7 jours de sa date d'émission. Pas de paiement par carte des frais à chaque course. Le transport reste facturé et payé directement entre client et transporteur.

Le module Stripe test préparé auparavant n'est pas une implémentation de ce modèle mensuel. Il ne doit pas être activé pour encaisser les frais course par course. Ses tarifs d'abonnement et ses contrôles de webhook pourront être réutilisés après choix du prestataire, mais le cumul, les factures et le recouvrement restent à développer.

## Événements et règles financières

| Situation | Écriture attendue | Protection / preuve |
| --- | --- | --- |
| Annonce, consultation ou offre sans attribution | Aucune créance | Pas de frais à la simple inscription |
| Attribution réciproque confirmée et coordonnées mises à disposition | Une ligne à 1,5 %, arrondie au centime | Accord sur prix, information et acceptation des frais, identifiants des parties et preuve d'accès aux coordonnées |
| Double clic, reprise réseau, événement rejoué | Aucune ligne supplémentaire | Clé unique du fait générateur et transaction atomique |
| Offre modifiée avant attribution | Pas de frais sur l'ancien prix | Confirmation du nouveau prix avant engagement |
| Prix modifié après attribution | Ajustement seulement après accord documenté | Conserver ancien prix, nouveau prix, motif et accord ; pas de majoration décidée unilatéralement |
| Annulation avant mise en relation aboutie | Aucune créance | Historique d'annulation |
| Annulation de convenance après mise en relation | Ligne maintenue selon CGV | Service acquis et information tarifaire démontrables |
| Même course exécutée hors plateforme après fausse annulation | Frais ordinaires maintenus si justifiés | Examen contradictoire, sans amende ni débit automatique sur soupçon |
| Transporteur défaillant avant enlèvement sans solution acceptée | Annulation de ligne ou avoir après examen | Éléments pertinents variés ; pas de CMR d'un tiers imposée |
| Réattribution après échec avant enlèvement | Crédit initial si applicable puis ligne justifiée pour nouvelle mise en relation | Pas de double facturation d'un même service |
| Transport litigieux, retard, force majeure | Dossier à examiner | Pas de suppression ni de maintien systématique par un statut seul |
| Exercice fictif ou pilote gratuit, même terminé | Jamais de créance | Exclusion serveur, pas seulement visuelle ; aucune rétroactivité |
| Correction après émission de facture | Avoir numéroté et/ou complément traçable | Pas de réécriture ou suppression d'une facture émise |

Le taux est appliqué au tarif HT accepté, hors TVA du transport. Exemple : 450,00 € × 1,5 % = 6,75 € HT. Trois courses à 450,00 €, 800,00 € et 1 200,00 € donnent 6,75 € + 12,00 € + 18,00 € = **36,75 € HT**, puis 44,10 € TTC uniquement si une TVA de 20 % sur les frais est effectivement applicable.

Pas de minimum de 0,50 € par course : l'ancien plancher technique du paiement unitaire ne doit pas être transposé à la créance mensuelle. Les arrondis sont monétaires décimaux, pas des flottants binaires. La somme est celle des lignes arrondies, sans recalcul silencieux différent sur le total des transports.

## Registre et clôture à développer

- Associer chaque écriture à l'établissement payeur, à la course, à l'attribution, au transporteur, au tarif HT et à la version acceptée des conditions. Distinguer date du fait générateur, date d'enregistrement et période comptable.
- Créer la créance côté serveur uniquement lors d'un événement valide. Aucun montant, rôle, quota ou statut fourni par le navigateur ne doit suffire. Le pilote actuel ne doit jamais produire de créance commerciale.
- Conserver les écritures initiales ; corriger par écritures liées et motifs, avec identité de l'auteur. Limiter les accès administrateur et tracer toute décision de régularisation.
- Versionner le taux et les règles ; ne pas modifier rétroactivement les attributions passées en changeant un paramètre global.
- Clôturer selon les bornes calendaires Europe/Paris, y compris les changements d'heure. Verrouiller les lignes incluses dans une facture et protéger le traitement contre les exécutions simultanées ou répétées.
- Émettre une seule facture mensuelle par établissement et périmètre fiscal pertinent, avec numérotation unique, chronologique et continue selon les règles comptables. Une écriture tardive doit être identifiée sur la période suivante ou régularisée suivant les instructions comptables, sans antidatation.
- Afficher dans le compte : encours provisoire, détail des courses, frais, éléments contestés, factures, avoirs, échéances et paiements rapprochés. Le document provisoire ne porte pas un numéro de facture définitive.
- Prévoir un circuit de facturation électronique conforme aux obligations réellement applicables à CHRONOSS et ses clients. Un PDF envoyé par e-mail n'est pas présumé suffisant au regard de la réforme en vigueur.
- Ne pas assimiler émission de facture, ordre de virement, statut bancaire « en cours » et règlement définitivement rapproché. Enregistrer rejets, retours et paiements partiels sans effacer leur historique.

## Encours, relances et impayés

La facture en fin de mois crée un crédit client : elle réduit les frais de petits paiements mais n'empêche pas un impayé. Une clause ne garantit pas le recouvrement.

Avant ouverture, définir un plafond d'encours par établissement selon les vérifications disponibles et le risque accepté. Aucun seuil chiffré n'est arrêté sans décision de l'exploitant. Le plafond doit être affiché avant engagement. Une nouvelle attribution est refusée si elle ferait dépasser ce plafond ; le client reçoit une explication et un moyen de demander un examen. Les missions déjà engagées restent suivies.

Séquence proposée : information de l'encours, facture avec date exacte, rappel à l'approche de l'échéance, relance motivée après échéance accordant un délai précis, puis suspension des nouvelles attributions sur créances exigibles non contestées et non réglées. Ne pas couper aveuglément le suivi, les réclamations ou les documents. En cas de fraude ou sécurité, traiter l'urgence selon une procédure dédiée et motivée.

Les intérêts et l'indemnité légale ne s'ajoutent que dans les conditions applicables. Les 40 € concernent une facture en retard, jamais chaque course d'une même facture. Les frais réels de banque ne sont pas refacturés automatiquement sous une pénalité non convenue.

La partie sérieusement contestée est isolée pendant son examen ; la partie non contestée reste exigible. L'objectif de réponse est de 15 jours ouvrés. La recommandation de signaler sous 30 jours n'éteint pas un recours légal ultérieur.

Un prélèvement SEPA nécessite un mandat distinct, une référence et un créancier autorisé, la bonne information préalable et le traitement des rejets/contestations. Un virement vers Qonto nécessite un rapprochement fiable et un contrôle antifraude des changements d'IBAN. L'acceptation des CGV n'autorise pas le prélèvement.

## Abonnements et documents

Aucun abonnement payant ne débute avant admissibilité documentaire et souscription explicite. Le paiement ne valide pas les pièces. Avant expiration, alerter le transporteur ; à expiration, bloquer les nouvelles offres/attributions selon le contrôle serveur.

Si une suspension documentaire imputable au transporteur dure jusqu'à l'échéance suivante, interrompre le renouvellement payant jusqu'à régularisation et confirmation de reprise. Ne pas promettre cette fonction avant de l'avoir reliée au prestataire et testée. Les missions engagées, obligations de sécurité et régularisations restent accessibles selon les restrictions nécessaires.

Un remboursement n'est ni systématique ni systématiquement exclu : examiner la cause, la période de service effectivement ouverte, les fautes et les obligations applicables. Une erreur de la plateforme doit pouvoir produire remboursement ou avoir. Résiliation et changement de forfait doivent être réalisables, confirmés et enregistrés avant toute souscription commerciale.

## Acceptation et preuves

Texte proposé à l'inscription commerciale, case non précochée :

> J'agis pour les besoins de mon activité professionnelle et suis habilité à engager l'entreprise. J'ai lu et j'accepte les CGU/CGV professionnelles [version et lien téléchargeable].

Texte distinct à la confirmation d'une mise en relation :

> Je confirme cette mise en relation pour le transport à [PRIX] € HT et accepte les frais de plateforme de 1,5 %, soit [FRAIS] € HT, TVA [RÉGIME/MONTANT], regroupés sur ma facture de fin de mois payable sous 7 jours. Les règles d'annulation et de régularisation sont accessibles ici [LIEN]. Le transport sera facturé séparément par le transporteur.

Si le calcul de la TVA ne peut pas être affiché de façon fiable, ne pas ouvrir ce parcours commercial avant correction. Aucune case n'est précochée ; la souscription de l'abonnement a sa propre confirmation avec prix, période et renouvellement. Ne pas transformer une ancienne acceptation gratuite en acceptation des frais payants.

Conserver la version intégrale remise, son empreinte, l'horodatage serveur, le compte, l'entreprise et les événements de confirmation. L'adresse IP seule n'établit pas le pouvoir d'engager l'entreprise ; ne la collecter que si nécessaire avec information et durée proportionnée. Prévoir copie durable au client, journal à accès restreint et export d'un dossier de preuve. Pas de CMR tierce imposée ni d'extraction de données inutiles.

## Recette nécessaire avant ouverture commerciale

1. Vérification de l'exploitant, assurance de l'activité et validation juridique/comptable documentées.
2. Acceptation nouvelle obligatoire pour les comptes existants ; refus et correction de prix possibles ; preuve de version remise.
3. Aucune créance au dépôt, à l'offre, au retrait avant accord ou sur exercice fictif ; une seule créance par mise en relation aboutie, même sous concurrence réelle.
4. Cumul et arrondis sur plusieurs courses ; changement de prix, annulation, réattribution et avoir sans doublons.
5. Clôture fin de mois et changement d'heure ; relance du traitement sans deuxième facture, écritures tardives et facture immuable.
6. TVA et mentions vérifiées par l'expert-comptable ; transmission conforme au régime de facturation électronique applicable.
7. Deux établissements ne lisent jamais leurs encours et factures respectifs ; les droits administrateur sont limités et audités.
8. Paiement total/partiel, rapprochement, rejet et facture impayée ; partie contestée isolée et absence de coupure du suivi engagé.
9. Expiration de pièce à la date du renouvellement ; pas de débit suivant indû ; résiliation et reprise confirmées.
10. Sauvegardes, restauration d'une facture/écriture, conservation, limitation des accès et notification des erreurs opérationnelles.

Aucun de ces scénarios mensuels n'est annoncé testé par la seule rédaction de cette spécification. Les tests du précédent module Stripe ne prouvent pas leur fonctionnement.

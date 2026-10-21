# Assistant de contrôle des transporteurs — cadrage demandé le 21 octobre 2026

**Demande :** examiner les dossiers automatiquement, valider les dossiers conformes et garder la possibilité de correction/annulation par CHRONOSS. **État : parcours proposé, non implémenté et non activé.** Les alertes d'inscription sont un module séparé, préparé dans cette session ; elles ne constituent pas cet assistant.

## Parcours à construire

1. Déclenchement à réception d'un document ou modification d'une pièce, pas seulement lors de l'inscription.
2. Téléchargement serveur depuis le stockage privé, avec limites de taille/type. Un document est une donnée non fiable : les instructions qui pourraient y être écrites ne doivent jamais diriger l'assistant ni déclencher d'action.
3. Extraction du contenu et des dates avec trace de la page et du passage justificatif. Aucun nom de fichier ne suffit à classer/valider la pièce. Une assurance peut couvrir plusieurs catégories uniquement si les garanties sont explicites.
4. Contrôle d'identité de l'entreprise au registre compétent et rapprochement des identifiants. Vérification des autorisations de transport auprès d'une source adaptée ; un Kbis ne suffit pas à établir ces autorisations.
5. Pour les assurances : période de validité, identité de l'assuré, nature des garanties RC/transport de marchandises, montants, franchises, exclusions, catégories de véhicules et périmètre d'activité. Une attestation seule ne prouve pas une couverture toujours en vigueur ou l'absence de résiliation ; selon le risque, une confirmation émetteur est nécessaire. Ne pas transformer une limite de 15 000 € en garantie tous risques ou sans plafond.
6. Décision par règles explicites sur des faits vérifiables. Une sortie de modèle ou un score de confiance ne doit pas, seul, modifier les droits. Dates manquantes, document illisible, divergence d'identité, périmètre ambigu ou authenticité non vérifiable : dossier à examiner par CHRONOSS, sans rejet définitif automatique.
7. Journaliser les contrôles, les sources, leurs dates, la version des règles, les pièces exactes et les motifs. Si une pièce est remplacée pendant l'analyse, invalider le résultat périmé et recommencer sur la nouvelle version.
8. Boutons administrateur pour corriger, approuver, suspendre et annuler, avec motif conservé. Une décision manuelle doit avoir priorité et ne pas être écrasée au prochain passage ; possibilité de désactiver l'automatisation.
9. Réévaluation aux expirations et lors de changements de pièces. La validation documentaire reste distincte des conditions commerciales et de la vérification du crédit bancaire effectif pour l'abonnement.

## Mise en service progressive

Commencer en mode observation sur les dossiers déjà examinés, sans modifier les droits. Inclure au minimum les anciennes pièces Orus rejetées, les attestations AXA classées, les incohérences de dates et d'identité et les documents fictifs. Contrôler les faux positifs avant d'autoriser des décisions automatiques limitées à des règles vérifiables. Une intervention humaine restera nécessaire pour les dossiers qui sortent de ce périmètre.

La mise en service nécessite un accès serveur aux pièces privées, un service d'extraction/analyse configuré et des sources de vérification accessibles et autorisées. Leur disponibilité, coût et conditions d'accès ne sont pas encore vérifiés. L'assistant ne peut pas être annoncé opérationnel avant cette configuration et la recette sur le projet réel.

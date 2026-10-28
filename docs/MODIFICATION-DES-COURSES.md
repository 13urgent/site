# Modifier une course publiée

## Usage

Le bouton « Modifier ma course » apparaît sur les courses ouvertes appartenant à l’entreprise connectée : dans la liste des courses lorsque l’enlèvement n’est pas passé, et dans le suivi de ses demandes. Il est réservé à l’entreprise propriétaire, y compris lorsqu’elle publie avec un profil transporteur ou administrateur. L’administrateur d’une autre entreprise ne peut pas modifier cette course par ce mécanisme.

Les champs modifiables sont le trajet, la date et l’heure d’enlèvement, le véhicule, le nombre de palettes, le poids, la raison sociale, l’e-mail et les précisions privées. Une date future est requise. Les valeurs sans changement ne produisent ni retrait d’offre ni événement de modification. Le formulaire conserve les valeurs en cas de refus et affiche le retour au même endroit.

La même course et son identifiant sont conservés. La modification n’est pas une nouvelle publication, ne déclenche pas de conversion Google Ads, et ne crée pas de frais ni de modification d’abonnement.

## Offres et attribution

Si une course est effectivement modifiée, les offres encore soumises sont retirées, sans effacement de leur ligne. L’auteur doit accepter explicitement ce retrait si des offres existent au moment de l’enregistrement, y compris si elles sont arrivées pendant sa saisie. Les transporteurs doivent proposer à nouveau après lecture des nouvelles informations. Les écrans mentionnent qu’une course révisée a changé. Aucune notification e-mail de modification n’est ajoutée par cette version.

Une course attribuée, annulée ou clôturée n’est pas modifiable par cette fonction. Le contrôle est effectué en base, pas seulement par la présence du bouton. Les droits de consultation des coordonnées privées restent inchangés.

Une révision entière est vérifiée sous verrou de la course : un formulaire ancien ne peut pas écraser une modification plus récente. Une ancienne offre ne peut pas être acceptée après retrait. Le dépôt d’offre exige la révision consultée sur une course déjà modifiée, pour éviter une proposition faite depuis un ancien écran.

L’événement « Course modifiée » est horodaté dans l’historique. Cet événement ne contient pas une copie complète des anciennes coordonnées et instructions.

## Activation

Exécuter intégralement `supabase/migrations/202610280001_edit_shipments.sql` dans SQL Editor. Le résultat attendu contient `enabled=true` et `revision=true`. Aucune Edge Function ni clé supplémentaire nécessaire pour cette option.

La migration ajoute la révision, la fonction de modification et un contrôle de version au dépôt d’offre. La fonction à deux paramètres de dépôt d’offre est remplacée par la version à trois paramètres, dont la révision est facultative seulement pour une course jamais modifiée : les anciens clients restent donc compatibles avec les courses non révisées. Les écrans anciens doivent être actualisés avant de proposer sur une course modifiée.

Le site vérifie la présence de la migration avant d’envoyer le paramètre supplémentaire. Avant activation, les dépôts d’offres existants restent sur leur ancien appel ; le bouton de modification explique que l’activation serveur manque. Aucun faux enregistrement local.

La migration est transactionnelle, n’utilise pas CASCADE et n’attribue aucun droit de modification directe des tables. Ne pas exécuter seulement une partie du fichier.

## Vérification

Test SQL : refus anonyme et autre entreprise (y compris admin), modification autorisée client/transporteur/admin propriétaire, confirmation des offres, retrait sans effacement, données privées conservées, identité inchangée, absence de frais, refus d’ancienne révision, refus d’ancienne offre, absence de changement atomique en cas d’erreur, refus après attribution.

Test navigateur avec SQL local : état explicite avant installation, modification réelle d’une course de test via le formulaire, relecture de la valeur enregistrée et absence de nouvelle conversion ; cycle d’offres, attribution, suivi et affichage mobile préservé. Aucun compte ou course de production modifié par ces tests.

La migration ne peut pas être installée depuis cette session sans accès administratif Supabase. La publication statique du bouton ne signifie donc pas que la fonction SQL est déjà activée.

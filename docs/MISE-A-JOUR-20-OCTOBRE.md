# Mise à jour groupée — 20 octobre 2026

## Ce qui est terminé dans le code

- Abonnements transporteurs après virement : période mensuelle de date à date, référence bancaire unique, référence de facture CHRONOSS, confirmation du crédit effectif, dates et révocation tracées. Pas de prélèvement automatique.
- Le serveur refuse les accès lorsque la période est future/terminée/révoquée ou les documents ne sont pas valides. Le forfait enregistré par l'administrateur fixe le quota : Drive 5, Boost 30, Premium sans plafond ; Start gratuit reste distinct. Une demande de forfait n'accorde aucun droit.
- Conditions version PRO-B2B-2026-10-20-v3 consultables et imprimables. Acceptation et empreinte SHA-256 du document enregistrées côté serveur ; version HTML v3 conservée sous une URL distincte. Confirmation distincte des frais avant attribution commerciale.
- Frais 1,5 % HT calculés côté serveur lors de la mise en relation, registre privé et cumul mensuel client. Aucune facturation des anciens pilotes ni des exercices fictifs.
- Relevé CSV mensuel pour l'outil CHRONOSS, par mois civil Europe/Paris, avec références client/course, frais, corrections et références de factures/avoirs externes. Ce CSV n'est pas une facture et ne calcule pas votre TVA.
- Corrections des frais sans suppression de l'original, plafonnées au montant initial. Une réduction intégrale libère la consommation de quota correspondante dans la période concernée. Pas d'annulation automatique du contrat de transport ni de remboursement bancaire par cette fonction.
- Enregistrement de la référence de facture/avoir émise dans votre outil, avec protection contre un double rapprochement sous une autre référence.
- Deux variantes de publication testables : inscriptions masquées pendant l'attente OVH, ou demandes professionnelles ouvertes. Leur ouverture n'accorde aucun droit commercial.

## État distant et intervention unique nécessaire

La session cloud ne peut pas appliquer la migration à votre Supabase : l'accès réseau au projet retourne toujours CONNECT 403. Aucune migration distante ni période payée réelle n'est annoncée appliquée par cette session.

Après sauvegarde/contrôle des migrations déjà installées, exécuter une seule fois dans Supabase SQL Editor le fichier :

[202610200001_manual_commerce.sql](../supabase/migrations/202610200001_manual_commerce.sql)

Il dépend du pilote et des correctifs documentaires et exercices du 19 octobre, jusqu'à **202610190003_test_exception.sql**. Il ne nécessite **pas** la migration Stripe `202610190004_billing_test.sql`. Ne pas rejouer toutes les migrations ni supprimer les anciennes tables.

L'installation est transactionnelle et conserve **enabled=false**. Elle ne facture rien, ne déclare aucun virement reçu et ne transforme aucun ancien pilote en opération payante.

Contrôle après installation :

```sql
select public.urgent_commercial_status();
```

La réponse doit indiquer `enabled: false` et la version `PRO-B2B-2026-10-20-v3`. Aucun enregistrement bancaire ni frais n'est attendu tant qu'aucune opération commerciale n'a eu lieu.

## Utilisation de l'administration après installation

1. Se connecter avec le compte administrateur existant. « Espace professionnel — abonnements et frais » apparaît en bas de page.
2. Le transporteur accepte les conditions depuis son propre compte. Contrôler les documents et l'établissement comme auparavant. L'autorisation d'entreprise et l'abonnement payé sont deux décisions distinctes.
3. CHRONOSS adresse son RIB et le document de paiement adapté. Relever le TTC attendu dans son outil de facturation ; le site n'invente pas un taux de TVA. Vérifier le crédit effectif en banque, pas uniquement la preuve transmise par le transporteur.
4. Dans « Activation après virement », sélectionner l'entreprise, le forfait, le premier jour, le TTC attendu et reçu, la référence bancaire et la référence de facture externe. Cocher la vérification bancaire. La période finit au début du jour correspondant du mois suivant, à l'heure de Paris, fin exclue ; pour un jour absent du mois suivant, le dernier jour est utilisé. La fin exacte est affichée. Aucun chevauchement n'est accepté.
5. Pour renouveler, enregistrer le nouveau règlement et la période suivante. Pas de rappel ni débit automatique : les demandes de renouvellement restent gérées par CHRONOSS. À expiration, les nouvelles offres/attributions sont bloquées, pas le suivi des courses engagées.
6. Start gratuit ne demande pas de virement. Il nécessite une autorisation d'entreprise Start, les conditions et les documents valides. Après un forfait payé expiré, aucun retour automatique au gratuit n'est accordé ; examiner une éventuelle demande de changement au lieu de laisser un accès permanent.

Une référence bancaire identique avec les mêmes données est idempotente. En cas d'erreur réseau, consulter les périodes avant de recommencer avec une autre référence. En cas de montant partiel/excédentaire, traiter l'écart dans la banque et la facturation avant d'enregistrer une période : le formulaire exige un crédit rapproché égal au TTC attendu.

## Ouverture après OVH et recette distante

La préparation actuelle ne modifie ni le domaine ni les paramètres e-mail OVH. La variante publiée pendant l'attente conserve les inscriptions masquées et le pilote gratuit. Les vidéos déjà téléchargeables sont préservées.

Au moment retenu pour l'ouverture, construire la variante avec demandes professionnelles accessibles :

```
python tools/build_pilot.py --open-registration --output /workspace/releases/NOUVEAU-DOSSIER-VIDE
```

Faire la vérification de la version effectivement publiée : nouveau compte professionnel, confirmation d'e-mail, rôle/entreprise et documents en attente sans accès indu. Le test CHRONOSS antérieur reste acquis, mais ne prouve pas que ce commutateur de publication est ouvert. Conserver `/videos/` lors du déploiement ; ne pas publier les SQL, docs internes ou pièces jointes.

Pour la recette distante du mode commercial, utiliser des données de recette isolées et une procédure contrôlée : l'activation du mode n'est pas un mode de simulation des virements. Ne jamais déclarer un virement réel reçu sans l'avoir rapproché. Valider également les informations contractuelles, la confidentialité, les messages de la version publiée et la procédure de facturation existante avant d'ouvrir le mode.

Le bouton administrateur « Ouverture commerciale » requiert la confirmation explicite :

```
CHRONOSS - VIREMENTS ET FACTURATION MANUELLE
```

Cette action active les contrôles commerciaux et les frais des futures attributions ordinaires uniquement. Elle ne modifie ni DNS, ni inscriptions, ni e-mails, ni les anciennes courses gratuites. Sans acceptation des conditions et confirmation des frais, l'attribution commerciale est refusée. L'ancien bouton du pilote ne peut pas la contourner.

## Relevé de fin de mois

Sélectionner le mois dans « Relevé mensuel », puis télécharger le CSV. Le mois est calculé côté serveur à l'heure de Paris et inclut frais et réductions du mois, sans faire disparaître un ancien montant. Les totaux affichés sont HT ; l'outil CHRONOSS reste responsable de l'émission, TVA, numérotation, échéance, facturation électronique applicable, envoi, rapprochement bancaire et relances.

Les valeurs textuelles pouvant être interprétées comme formules sont neutralisées dans le CSV. Les montants HT signés sont des valeurs numériques décimales avec virgule. Ne pas retraiter les lignes déjà rapprochées sans vérifier leur référence externe.

Émettre la facture/avoir dans votre outil, cocher uniquement les lignes du client concerné et enregistrer sa référence dans le site. Une ligne déjà rapprochée ne peut pas être rattachée à une autre facture. Une correction après facturation exige un avoir dans l'outil externe : le bouton de réduction ne l'émet pas.

## Vérification effectuée et limites

SQL embarqué et Chromium vérifient le parcours, les rôles, l'absence d'écriture directe, périodes et chevauchements, paiement rapproché explicite, documents et dates, quota Drive, frais et absence de double attribution, lecture privée, export CSV, rapprochement externe, réduction et effacement des données à changement de compte. Le pilote existant et les variantes de déploiement restent testés.

Ces vérifications ne remplacent pas l'application et la recette sur le projet distant, les tests de concurrence multi-connexions et le fonctionnement de votre banque/outil comptable. Aucun paiement réel, e-mail automatique, relance, sauvegarde distante ou migration OVH n'est effectué par ce module. La gestion bancaire, les relances d'impayés et les décisions sur les litiges restent manuelles ; pas de moteur automatique de recouvrement.

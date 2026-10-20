# Ouverture avec facturation CHRONOSS et virements — décision du 20 octobre 2026

## Fonctionnement retenu par l'exploitant

L'exploitant confirme disposer déjà d'un système de facturation chez CHRONOSS. Il rapporte un retour favorable de son expert-comptable sur les conditions. Cette information est retenue dans le projet, sans revendiquer un audit indépendant de ce retour ou de son périmètre.

Aucun nouveau logiciel d'émission de factures ni intégration Stripe n'est requis pour ce démarrage. Le raccordement du domaine reste en cours de traitement avec OVH à la demande de l'exploitant.

### Donneurs d'ordre

Inscription et publication gratuites ; frais de mise en relation de 1,5 % HT regroupés sur le mois. CHRONOSS établit la facture dans son système existant. Le transporteur facture directement le transport à son client. Le suivi des courses, des prix convenus, annulations et corrections doit permettre de justifier les frais facturés. Ne pas facturer rétroactivement les exercices fictifs ou le pilote explicitement gratuit.

La plateforme doit fournir un relevé mensuel exploitable par la facturation existante, pas se substituer à cet outil. Avant son développement, une extraction administrative contrôlée et une vérification manuelle sont nécessaires ; aucun export commercial mensuel prêt n'est revendiqué aujourd'hui. Toute facture émise reste gérée et numérotée dans l'outil CHRONOSS pour éviter deux séquences concurrentes.

### Transporteurs

1. Le transporteur s'inscrit et choisit le forfait demandé.
2. CHRONOSS contrôle le dossier professionnel et les documents, leur portée et leurs échéances.
3. CHRONOSS confirme le forfait, le prix HT/TVA/TTC, la période et les conditions ; elle adresse le document de paiement adapté et son RIB par un canal de confiance.
4. Le transporteur effectue un virement avec une référence permettant le rapprochement.
5. Un administrateur vérifie le crédit effectif et son montant dans le compte bancaire CHRONOSS. Un justificatif de virement fourni par le transporteur ne suffit pas à lui seul.
6. L'administrateur enregistre le forfait accordé, le règlement rapproché, la date de début et la date de fin, ainsi que la référence de facture selon les règles de l'outil comptable. L'accès n'est activé que si les documents et vérifications restent valables.
7. Le renouvellement exige un nouveau règlement rapproché. Pas de prélèvement automatique ni de mandat implicite. Sans paiement à l'échéance, les nouvelles propositions/attributions sont bloquées selon les conditions ; le suivi des courses engagées est préservé.

Le forfait Start gratuit ne demande pas de virement ; il reste soumis aux vérifications et à son quota. Le changement de forfait et un paiement incomplet ou en trop nécessitent une décision documentée, sans déblocage automatique. Ne jamais placer un IBAN deviné ou une référence bancaire privée dans le dépôt.

## État technique constaté

Le test CHRONOSS a validé l'existence du parcours d'inscription, de confirmation d'e-mail, de dépôt et de revue de documents. Le parcours fictif a atteint la confirmation de réalisation. Ces tests ne sont pas à refaire intégralement sans changement qui le justifie.

Le 20 octobre, le fichier config.js de la branche de publication gh-pages porte toujours :

```
window.URGENT_MARKETPLACE_PILOT = true;
window.URGENT_BILLING_TEST_UI = false;
window.URGENT_ALLOW_REGISTRATION = false;
```

Les inscriptions restent donc masquées et refusées par l'interface publique. Cela ne désactive pas l'API d'inscription Supabase. L'administration actuelle utilise urgent_review_pilot : elle accorde un accès pilote gratuit, pas une période d'abonnement payée contrôlée à l'échéance.

## Adaptations encore nécessaires avant de présenter le service comme commercial

- Rendre les inscriptions publiques accessibles avec les informations contractuelles du mode commercial et tester cette version publiée. Le succès d'une inscription antérieure ne prouve pas que le commutateur public est ouvert.
- Ajouter le traitement administratif du virement, la période d'abonnement et les vérifications serveur de fin de droits et de quota ; le choix d'un forfait ou une capture bancaire ne doit pas activer les droits.
- Fournir le relevé mensuel des frais destiné à l'outil CHRONOSS, avec exclusion des tests et corrections traçables.
- Mettre en cohérence les confirmations et mentions de gratuité du pilote avec le futur parcours commercial avant toute créance. Aucun frais ne devient exigible par la seule modification d'un texte.

Ce fichier enregistre la décision opérationnelle. Il ne déploie pas ces adaptations, n'active aucun paiement, ne crée aucune facture et ne change aucun droit du pilote.

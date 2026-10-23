# Récapitulatif mensuel de préparation à la facturation

Préparé le 23 octobre 2026. **Pas encore installé/activé à distance.** Ne pas annoncer l'envoi automatique avant les étapes et la recette ci-dessous.

## Résultat demandé

Le 1er du mois à partir de 08:00, heure de Paris, envoi à **saschronoss@outlook.com**, via l'expéditeur Resend déjà configuré. Un récapitulatif interne regroupe les entreprises, avec un détail par entreprise dans le document joint. Aucun e-mail n'est envoyé aux clients. Aucun numéro de facture, facture comptable, prélèvement, frais supplémentaire ou paiement n'est créé par ce traitement.

Deux pièces jointes :

- Un relevé HTML autonome, ouvrable dans un navigateur et imprimable en PDF (une section par entreprise), marqué **DOCUMENT PRÉPARATOIRE — NE CONSTITUE PAS UNE FACTURE**. Les bases sont HT ; la TVA reste à déterminer dans l'outil de facturation suivant la situation réelle.
- Un CSV des écritures de frais et régularisations : entreprise, SIRET déclaré, références course/offre/écriture, trajet, date Paris, nature, prix transport de référence, frais HT, référence de facture déjà rapprochée et origine des régularisations. Les valeurs textuelles sont protégées contre les formules de tableur.

Le relevé distingue net du mois et montant non rapproché d'une facture à sa génération. Les lignes déjà facturées ne doivent pas être émises une deuxième fois. Un solde négatif appelle l'examen d'un avoir. Les périodes d'abonnement enregistrées ou révoquées dans le mois sont dans une section de suivi distincte avec leur référence de facture et règlement enregistré TTC ; elles ne s'ajoutent pas de nouveau à la base de frais HT.

Le mois est délimité selon le calendrier **Europe/Paris**, avec début inclus et fin exclue, y compris les changements d'heure. Les dates d'écriture déterminent le mois ; une régularisation tardive apparaît dans son mois avec sa référence d'origine. Les exercices fictifs sont exclus. Les 1,5 % ne sont pas recalculés sur les annonces : le traitement reprend les frais déjà enregistrés au moment de l'attribution.

## Installation groupée, sans nouvelle clé et sans nouveau cron

1. Dans Supabase SQL Editor, exécuter **`supabase/migrations/202610230004_monthly_billing_reports.sql`**. Nécessite la migration commerciale du 20 octobre et les tables existantes. Elle n'active pas le mode commercial et ne change aucun frais. Le mois de début est initialisé au mois de l'installation : pas d'envoi automatique rétroactif des anciens mois.
2. Dans Edge Functions → **bright-service → Code**, remplacer tout `index.ts` par **`supabase/functions/registration-alerts/index.ts`** mis à jour. Déployer les mises à jour. Garder « Verify JWT with legacy secret » désactivé : le secret serveur existant protège toujours l'appel.
3. Dans Edge Functions → Secrets, ajouter **`MONTHLY_REPORTS_ENABLED=true`**. Garder les autres secrets et `REGISTRATION_ALERTS_ENABLED` inchangés. Le fournisseur, l'expéditeur, le destinataire et le secret de déclenchement sont réutilisés.
4. Le cron `urgent-registration-alerts`, déjà appelé chaque minute via Vault, traite aussi les rapports dès leur échéance. Aucun nouveau job n'est nécessaire. Les deux types d'envoi sont activables séparément ; un échec de rapport ne doit pas empêcher le traitement normal des inscriptions.
5. Pour la recette réelle, exécuter **`supabase/setup/test-monthly-billing-report.sql`**. Cela met en file un rapport marqué TEST sur le dernier mois clôturé, sans inventer de course ni frais. Il peut être vide. Vérifier sa réception et les deux pièces jointes dans Outlook. La contrainte unique du mois empêche de créer un doublon en réexécutant le script ; un ancien rapport de ce mois n'est pas écrasé.

Avec une installation en octobre 2026, le premier rapport normal porte sur octobre et devient éligible le **1er novembre 2026 à 08:00 Paris**, puis à chaque mois clôturé. Le cron traite à la minute suivante, sans garantie de livraison immédiate si le fournisseur ou le serveur est indisponible.

## Fiabilité et contrôles

Les snapshots et files sont privés : aucun accès anon/authenticated, RPC réservées au service serveur. Un snapshot figé permet les reprises sans changer le contenu des montants entre deux tentatives. Les références d'écritures servent au rapprochement avec l'outil de facturation ; toujours vérifier les émissions réalisées après la génération du relevé.

Une clé d'idempotence stable par rapport est envoyée à Resend. Le bail dure cinq minutes ; huit tentatives maximum, temporisation progressive, et arrêt automatique après 23 heures pour rester sous la fenêtre d'idempotence fournisseur. `sent` signifie accepté par le fournisseur, pas livraison garantie dans Outlook. Les erreurs réseau/API sont réessayées ; un document invalide ou dépassant 6 Mo avant encodage est placé en échec, sans rapport partiel ni troncature. Ces cas doivent être surveillés dans la file. Pour un fort volume, il faudra adapter l'export et la livraison ; ne pas réinitialiser aveuglément un rapport déjà accepté.

Surveillance dans SQL Editor :

```sql
select month,status,attempts,sent_at,last_error_code
from public.urgent_monthly_reports order by month desc;
```

Pause : `MONTHLY_REPORTS_ENABLED=false`, sans interrompre les alertes d'inscription. Aucune preuve de virement ou décision d'assurance n'est automatisée par ce relevé. Aucune IA n'est nécessaire pour additionner les écritures : les montants sont calculés de manière déterministe.

## Vérifications locales

- `tests/monthly-reports-sql.cjs` : mois clôturé, bornes UTC/Paris, écritures à la frontière, régularisations, distinction abonnements, confidentialité, absence de reprise historique, snapshot stable, bail/reprises, un seul rapport par mois et aucun frais modifié.
- `tests/monthly-reports-http.cjs` : totaux HT, document préparatoire, séparation abonnements, HTML/CSV sûrs, destinataire fixe, idempotence et erreur fournisseur, rapports possibles même avec alertes d'inscription suspendues.
- `tests/registration-alerts-http.cjs` : non-régression des alertes existantes avec la fonction mise à jour.

Les tests n'ont envoyé aucun e-mail réel et n'ont pas modifié la base distante. L'installation et la recette ci-dessus restent nécessaires.

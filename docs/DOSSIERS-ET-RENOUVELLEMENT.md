# Classement des établissements et renouvellement documentaire

L’administration affiche les pièces à examiner, les dossiers à compléter/actualiser et les dossiers documentaires validés. Les établissements autorisés sont classés dans une rubrique repliée ; ils restent consultables et modifiables. Une nouvelle pièce remet le dossier documentaire dans la file à examiner. Les anciennes versions restent consultables séparément, sans servir de repli quand une nouvelle version est en attente.

La règle demandée est de six mois calendaires après le dépôt de chaque catégorie, y compris l’immatriculation, avec une expiration plus proche prioritaire. La réapprobation d’un ancien fichier ne repousse pas sa date ; déposer une nouvelle copie nécessite toujours son examen. Le navigateur affiche le calendrier, mais le contrôle des nouveaux droits de proposition est effectué en base lors des actions. Les droits commerciaux et les missions déjà engagées ne sont pas réinitialisés par ce classement.

## Activation serveur

Exécuter une fois `supabase/migrations/202610270002_document_renewal.sql` dans SQL Editor. Elle protège les dates de dépôt et renforce la checklist et le contrôle documentaire existants. Ne pas rejouer les anciennes migrations. Le résultat attendu contient enabled=true et months=6. Les anciennes pièces déjà déposées depuis six mois peuvent nécessiter un renouvellement ; les fichiers et décisions historiques ne sont pas supprimés. Les rappels sont affichés sur le site ; cette version ne programme pas de relance e-mail périodique aux transporteurs.

## Réponses d’assistance par e-mail

Redéployer uniquement `support-assistant` avec son fichier complet à jour. L’action `reply_ticket`, réservée aux administrateurs, enregistre la réponse puis récupère l’adresse confirmée du vrai créateur de la demande dans Auth. Aucun destinataire saisi par le navigateur n’est utilisé. L’interface affiche l’adresse destinataire et si Resend a accepté l’envoi. Une réponse reste consultable même si l’e-mail échoue. Une acceptation du fournisseur ne prouve pas la livraison en boîte de réception. Une clé d’idempotence limite les doublons de notification pour une réponse identique au même compte.

Sans mise à jour de la fonction, l’interface conserve l’enregistrement sur le site mais indique que l’envoi e-mail nécessite la mise à jour du service. Aucun secret supplémentaire ni modification de bright-service n’est nécessaire.

## Validation des établissements

Créer/confirmer un compte ne valide pas son établissement. Le formulaire vérifie l’accès disponible avant publication et indique le compte connecté. Un administrateur peut ouvrir directement la validation de son propre établissement. Le SIRET et la qualité du représentant doivent être contrôlés avant d’autoriser l’accès. Aucune inscription ni analyse IA ne confère automatiquement ces droits.

Tests : `dossier-renewal.cjs` couvre les six mois, les fins de mois, l’expiration plus proche, les dates non falsifiables, les changements de pièces et le classement. Les tests d’assistance couvrent la réponse admin, le vrai auteur comme destinataire, les erreurs d’envoi, l’idempotence et les permissions. Les essais locaux n’envoient aucun courrier réel.

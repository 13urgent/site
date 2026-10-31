# Start après une ancienne période payée

L'audit du 31 octobre 2026 a reproduit un blocage permanent : le calcul des droits ne reconnaissait Start qu'en l'absence de toute ligne historique de souscription payée. Réenregistrer une décision administrative Start ne suffisait pas après une période terminée ou révoquée.

La migration `202610310003_start_reauthorization.sql` remplace ce veto définitif par l'exigence d'une décision Start postérieure aux événements payants pertinents : enregistrement, retrait et fin d'une période non révoquée déjà terminée. Les égalités de dates ne sont pas considérées comme une preuve d'antériorité ; une nouvelle décision est alors nécessaire.

Un Start expressément réapprouvé peut couvrir l'attente d'une période future. Au terme de cette période, son événement de fin rend nécessaire une nouvelle décision. Un Start antérieur à une période payée ne reprend donc pas automatiquement après son expiration. Les périodes payées et internes actives conservent leurs priorités et leurs quotas. Le calcul des usages mensuels n'est pas remis à zéro.

Les documents, l'autorisation de l'établissement, les conditions et le rôle transporteur restent requis. Une demande déclarative dans Auth ne peut pas activer Start. La migration ne modifie aucun compte, plan sélectionné, paiement ou document et n'accepte aucune condition.

Les dates des décisions et des règlements restent issues du modèle existant (`now()`, début de transaction). Les tests couvrent les transitions séquentielles et les égalités ; ils ne prouvent pas un ordre absolu entre plusieurs transactions administratives concurrentes. La réautorisation utilise le formulaire administratif existant.

Validation : `tests/start-reauthorization-sql.cjs`, `tests/subscription-plans-sql.cjs`, `tests/internal-premium-sql.cjs`. La politique publique `urgent_start_access_policy` permet de constater l'installation, sans divulguer de dossier privé. La réussite des tests ne confirme pas le blocage précis d'un client sans ses données réelles.

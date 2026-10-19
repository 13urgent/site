# Exception de test CHRONOSS — demande du propriétaire

Cette exception est strictement limitée aux exercices fictifs, sans transport réel, sans paiement, sans validation de documents. La fonction normale urgent_carrier_ready reste inchangée et le dossier peut continuer à afficher « non admissible » : ce n'est pas une approbation d'assurance.

## Activation unique

Après les migrations précédentes, exécuter `docs/sql/deblocage-chronoss-test.sql` dans SQL Editor. Ce script ajoute le support des exercices et active une exception de 48 heures uniquement sur l'entreprise CHRONOSS identifiée par son UUID et son SIRET déjà autorisés au pilote. Si l'entreprise, son SIRET ou ses autorisations ne correspondent pas, l'ensemble est annulé. La date de fin en heure de Paris est affichée à la fin. Ne pas relancer pour prolonger automatiquement.

Le script générique `supabase/migrations/202610190003_test_exception.sql` installe seulement le mécanisme, sans autoriser de société. Si le script ciblé a déjà été exécuté, ne pas appliquer à nouveau le script générique.

## Parcours

1. Sur le site public mis à jour, se connecter comme administrateur et actualiser (Ctrl+F5).
2. Dans le formulaire de course, cocher **Créer un exercice fictif sans transport réel**. Cette option est réservée aux administrateurs et contrôlée en base. Elle ne nécessite pas de créer un nouveau compte client pour cet exercice.
3. Utiliser des villes et contacts de test, une date future et des instructions indiquant clairement qu'aucun transport ne sera exécuté. Une étiquette « EXERCICE FICTIF » est affichée dans la liste et le suivi.
4. Avec le compte transporteur CHRONOSS, proposer un tarif uniquement sur cet exercice. Une proposition sur une course ordinaire reste soumise à toutes les validations documentaires.
5. Revenir comme administrateur pour sélectionner l'offre de l'exercice et tester le suivi. Les attributions fictives ne consomment pas les quotas commerciaux et ne produisent aucune facture.

Après expiration, nouvelles offres et attributions sous exception sont refusées. Le suivi d'un exercice déjà attribué reste possible pour conserver l'historique. Ne pas utiliser ces données comme contrat réel.

## Garanties testées

L'expiration est contrôlée au dépôt d'offre et à l'attribution. Une exception d'une autre société ne donne pas de droit à CHRONOSS. L'exception ne change ni la revue des assurances, ni la licence, ni le SIRET. Les utilisateurs ne peuvent pas modifier directement is_test ni leur date d'exception. La création d'exercices est réservée à l'administration, et l'exception reste soumise à l'autorisation de pilote préexistante.

La dernière attestation RC reçue ne suffit toujours pas à confirmer la garantie marchandises ni une activité tout tonnage. Cet outil ne modifie pas ce constat.

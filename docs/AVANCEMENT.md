# Point d'avancement — 17 octobre 2026

## Vérifié sur le projet réel avec l'utilisateur

- Inscription transporteur CHRONOSS, confirmation e-mail, profil carrier, SIRET et demande Start enregistrés, entreprise pending.
- Dépôt et lecture du Kbis depuis l'administration ; l'approbation globale de l'entreprise n'est pas acquise.
- Dépôt, lecture et refus d'un document sur les comptes de test précédents ; accès au PDF par lien signé.
- Brouillon externe partagé avec budget privé ; règles PostgreSQL contrôlées via tests de rôles dans SQL Editor.

## Développé et testé localement, non activé à distance

Courses partagées, prix confidentiels, attribution unique avec contrôle du prix affiché, accès pilote administrateur, admissibilité documentaire et quotas, contacts restreints après attribution, suivi horodaté et confirmation client. Voir PILOTE-COURSES.md pour la seule nouvelle migration et l'activation groupée.

Des protections d'affichage ont été ajoutées pour effacer les dossiers au changement de session. Aucune fonctionnalité d'agent de surveillance autonome n'a été déployée : sujet explicitement reporté.

## Blocages externes

- OVH : ticket S16949971 pour refus FTP/SFTP ; relance préparée et envoyée par l'utilisateur.
- Proxy cloud : les requêtes vers le projet Supabase restent refusées (CONNECT 403), malgré le domaine enregistré. L'accès navigateur de l'utilisateur fonctionne. Les opérations SQL distantes restent à exécuter par l'utilisateur.
- Aucun prestataire de paiement ni SMTP de production configuré par cette session.

## À ne pas annoncer comme prêt

Abonnements payés, frais de 1,5 % encaissés, factures, contrats, assurance de conformité juridique, livraison GPS ou preuve de livraison signée, site public OVH opérationnel. Les particuliers restent exclus.

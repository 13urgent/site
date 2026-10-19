# Point d'avancement — 19 octobre 2026

## Conditions commerciales et facturation mensuelle — préparation

Le Kbis fourni (à jour au 7 octobre 2026) a permis de compléter les conditions v2 : CHRONOSS, SAS à associé unique, capital 12 600,00 €, siège 27 Boulevard Charles Moretti, 13014 Marseille, RCS Marseille 918 710 393. TVA, e-mail contractuel et rattachement du SIRET restent à confirmer. Aucun PDF ni renseignement personnel de dirigeant n’est publié.

CHRONOSS est désigné par l’utilisateur comme exploitant, sous réserve de vérification de ses mentions légales. Les donneurs d’ordre cumuleront les frais de 1,5 % HT pour une facture unique de fin de mois ; ce choix remplace le paiement unitaire des frais. Le [projet de CGU/CGV](juridique/CGU-CGV-PROJET.md), le [cadre à implémenter](juridique/FACTURATION-MENSUELLE-CADRE.md) et le [dossier de validation](juridique/VALIDATION-AVANT-PUBLICATION.md) sont rédigés. Ils couvrent annulations, preuve, contournement limité à la course apportée, impayés et suspension proportionnée, sans clause générale de non-remboursement. Documents de travail uniquement : pas de validation juridique ni de publication contractuelle ; le cumul mensuel et son recouvrement ne sont pas encore développés.

## Dernier état confirmé

Le site est accessible sur https://13urgent.github.io/site/ ; l'utilisateur a confirmé son fonctionnement sur téléphone. Le parcours fictif CHRONOSS a été effectué jusqu'au statut « Réalisation confirmée par le client » (course e9fa89c6-b78b-4e13-bc0f-971d01d632bc). Cela ne valide pas les documents ni un transport réel. L'exception documentaire temporaire est limitée aux exercices fictifs et expire le 21 octobre à 15:23:32, heure de Paris.

La préparation Stripe test est ajoutée : commandes serveur, tarifs fixes, frais de 1,5 %, webhook signé et journal idempotent, sans effet sur les droits du pilote. Pas de branchement Stripe ni de migration de facturation distante. Paiements réels, ouverture des inscriptions et activation commerciale restent à terminer. Voir [PAIEMENTS-TEST.md](PAIEMENTS-TEST.md).

Validation locale de cette préparation : 13 scripts réussis (PostgreSQL embarqué, HTTP simulé et Chromium), dont le parcours complet du pilote et le paquet statique sans interface de paiement visible. Aucun paiement réel ni appel Stripe réel vérifié.

Les sections ci-dessous conservent l'historique des étapes antérieures.

## Vérifié sur le projet réel avec l'utilisateur

- Inscription transporteur CHRONOSS, confirmation e-mail, profil carrier, SIRET et demande Start enregistrés, entreprise pending.
- Dépôt et lecture du Kbis depuis l'administration ; l'approbation globale de l'entreprise n'est pas acquise.
- Dépôt, lecture et refus d'un document sur les comptes de test précédents ; accès au PDF par lien signé.
- Brouillon externe partagé avec budget privé ; règles PostgreSQL contrôlées via tests de rôles dans SQL Editor.

## Pilote appliqué, recette réelle partielle

Courses partagées, prix confidentiels, attribution unique avec contrôle du prix affiché, accès pilote administrateur, admissibilité documentaire et quotas, contacts restreints après attribution, suivi horodaté et confirmation client. La migration pilote a été appliquée par l’utilisateur et la bannière affichée localement. À ce stade antérieur, la course complète restait non testée ; la recette fictive est désormais confirmée ci-dessus.

Des protections d'affichage ont été ajoutées pour effacer les dossiers au changement de session. Aucune fonctionnalité d'agent de surveillance autonome n'a été déployée : sujet explicitement reporté.

## Blocages externes

- OVH : ticket S16949971 pour refus FTP/SFTP ; relance préparée et envoyée par l'utilisateur.
- Proxy cloud : les requêtes vers le projet Supabase restent refusées (CONNECT 403), malgré le domaine enregistré. L'accès navigateur de l'utilisateur fonctionne. Les opérations SQL distantes restent à exécuter par l'utilisateur.
- Aucun prestataire de paiement ni SMTP de production configuré par cette session.

## À ne pas annoncer comme prêt

Abonnements payés, frais de 1,5 % encaissés, factures, contrats, assurance de conformité juridique, livraison GPS ou preuve de livraison signée, site public OVH opérationnel. Les particuliers restent exclus.

## Dernière livraison préparée

Outils de correction des catégories et dates par administrateur, diagnostic des pièces bloquantes, contrôle des dates obligatoires du pilote et signalements privés de prestation. Une seule nouvelle migration à appliquer et trois fichiers d’interface à mettre à jour : voir [la procédure groupée](MISE-A-JOUR-19-OCTOBRE.md). La garantie marchandises de CHRONOSS n’est pas établie par l’attestation RC reçue ; ne pas la déclarer validée pour débloquer le test.

## Préparation de la publication provisoire

Les dix scripts de tests ont été exécutés avec succès : 4 PostgreSQL embarqué et 6 navigateurs, dont le paquet d'hébergement en sous-dossier. Aucune requête de test contre la base distante n'a réussi depuis la session : le proxy retourne toujours CONNECT 403. La dernière migration est annoncée appliquée par l'utilisateur ; cela ne prouve pas la recette réelle complète.

Une version de publication pilote est construite séparément, avec paiements désactivés et inscriptions fermées dans l'interface. Voir DEPLOIEMENT-PILOTE.md pour l'activation Pages et les liens d'e-mail. Aucun DNS OVH n'est modifié.

## Publication Pages confirmée

Le 19 octobre, la branche gh-pages a été poussée (commit 13e75d4). GitHub Actions « pages build and deployment » n°39241061027 termine avec Success et indique https://13urgent.github.io/site/. Le contrôle de l'arborescence publiée confirme seulement les 11 fichiers statiques attendus. Les requêtes directes vers github.io et Supabase restent refusées par le proxy : l'ouverture HTTP et la recette réelle depuis cette adresse ne sont pas encore vérifiées par cette session. Le domaine 13urgent.fr reste chez OVH et n'a pas été modifié.

## Exception de recette demandée pour CHRONOSS

Mécanisme préparé pour une exception documentaire de 48 heures uniquement sur des exercices fictifs créés par l’administrateur, sans paiement ni transport réel. Les tests SQL confirment le refus sur les courses ordinaires et après expiration ; la validation normale des documents reste inchangée. Voir TEST-CHRONOSS.md et le script ciblé. Aucun déblocage distant effectué par la session cloud.

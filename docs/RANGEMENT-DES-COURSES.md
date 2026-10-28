# Rangement des courses annulées et fictives

L’entreprise propriétaire peut retirer une course annulée ou un exercice fictif des listes courantes. La fiche passe dans « Courses retirées / exercices rangés », une rubrique repliée du suivi. Le bouton « Réafficher dans l’historique » permet de la retrouver sans réouvrir une course annulée ni réactiver ses offres.

Il s’agit d’un rangement conservant les données : aucune suppression définitive de course, de coordonnées, d’offre, d’événement ou de frais. Le retrait d’un exercice encore ouvert l’annule avant rangement. Les offres soumises sont retirées ; les offres acceptées et les écritures comptables restent inchangées. Les fictifs déjà en cours conservent leur état et peuvent être retrouvés dans l’historique. Les boutons de progression ne sont pas présentés sur les fiches rangées.

L’archive est portée par la course : les utilisateurs autorisés à son historique la retrouvent dans la rubrique repliée. Ce n’est pas une suppression locale liée à un navigateur. Seule l’entreprise propriétaire peut retirer ou restaurer ; un administrateur d’une autre entreprise ne peut pas utiliser cette action. Les permissions de consultation et de suppression directe restent inchangées.

Activation : exécuter le fichier complet `supabase/migrations/202610280002_archive_shipments.sql` dans SQL Editor. Le résultat attendu contient `enabled=true`, `restore=true`. Aucun remplacement de fonction Edge ni nouveau secret nécessaire. Avant activation, le site explique que le rangement nécessite la mise à jour serveur, sans annoncer un faux succès.

Contrôles : SQL propriétaire/autre entreprise/admin autre entreprise/anon, réel actif refusé, retrait idempotent, restauration sans réouverture, fictif ouvert annulé, données conservées, conservation d’une vraie écriture de frais de test après annulation administrative simulée. Navigateur avec SQL local : annulation, retrait du suivi courant, archive repliée puis réaffichage, mobile. Aucun dossier réel modifié pendant ces tests. 35 contrôles réussis ; le sélecteur du test d’offre a été précisé après ajout des nouveaux retours d’état, puis le scénario a été rejoué avec succès.

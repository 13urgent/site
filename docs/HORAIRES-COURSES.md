# Départ et arrivée prévus — 30 octobre 2026

Le départ existant reste dans urgent_shipments.pickup ; delivery_at contient l’arrivée
prévue, facultative sur les anciennes lignes. Aucun horaire réel de chargement ou
de livraison n’est déduit de ces prévisions. Les étapes opérationnelles restent distinctes.

## Activation Supabase

Dans SQL Editor, exécuter intégralement :

    supabase/migrations/202610300001_shipment_schedule.sql

Résultat attendu : horaires_des_courses.enabled = true,
version = 20261030-shipment-schedule, timezone = Europe/Paris.
Aucun changement d’Edge Function, secret, abonnement ni frais n’est nécessaire.

Avant activation, le site affiche déjà le départ et « Arrivée prévue : Non renseignée ».
Le formulaire continue à fonctionner avec l’ancien service, en indiquant que
l’enregistrement de l’arrivée n’est pas encore activé. Aucune arrivée saisie n’est
annoncée comme enregistrée par une API qui ne la prendrait pas en charge.
Après activation, départ et arrivée sont obligatoires pour les nouveaux dépôts et
pour les modifications effectuées par l’interface à jour, y compris sur une ancienne
course dont l’arrivée n’a jamais été renseignée.

## Contrôles

Les deux horaires sont exprimés en heure de Paris, indépendamment du fuseau du téléphone.
La conversion tient compte de l’heure d’été/hiver. Une heure inexistante ou ambiguë
lors du changement d’heure est refusée avec un message explicite ; un horaire existant
inchangé conserve son instant exact, même dans cette plage.

La nouvelle publication est atomique : l’API appelle la publication existante et
renseigne l’arrivée dans la même transaction. La modification garde les contrôles
propriétaire, statut ouvert et révision ; changer seulement l’arrivée augmente
la révision et impose le retrait explicite des offres déjà reçues. L’arrivée doit
être strictement postérieure au départ (contrôle navigateur, RPC et contrainte SQL).
Les API historiques restent disponibles pour les anciennes interfaces.

Vérifications locales : tests/shipment-schedule-sql.cjs,
tests/shipment-schedule-timezone.cjs, tests/site-pages-browser.cjs DOSSIER --schedule,
ainsi que les parcours historiques sans activation et les contrôles mobile/PWA.
Les tests n’écrivent aucune course et n’envoient aucun e-mail en production.

# Services CHRONOSS et 13 URGENT — France entière

Périmètre accepté par Haeckel : France entière pour tous les services.

Les nouvelles pages services-chronoss.html, demenagement.html, demander-un-devis.html
et retours-a-vide.html utilisent le menu et la connexion partagés. Les services
CHRONOSS comprennent le transport routier/express, les projets réguliers et tournées,
les déménagements/transferts de bureaux et le transport d'objets volumineux, sur devis.
Aucun moyen matériel, délai garanti ou disponibilité universelle n'est affirmé.

## Professionnels

Une course peut décrire des codes postaux, huit arrêts intermédiaires au maximum,
un besoin ponctuel/régulier, une date de fin, un aller-retour et un volume.
La récurrence décrit le besoin à chiffrer, sans créer automatiquement une série de
courses, de frais ou de contrats. L'arrivée reste postérieure au départ, heure de Paris.
La modification du périmètre est atomique et retire les propositions après confirmation,
avec une nouvelle révision. Les anciennes courses conservent leurs informations.

Les transporteurs choisissent leurs alertes de façon explicite : départements et
véhicules, critères vides = tous. Jusqu'à dix alertes par jour sont mises en file.
Les exercices fictifs, entreprises non admissibles, courses expirées/attribuées,
préférences retirées et rattachements modifiés sont exclus à l'envoi. Les prévisions
sont lues au moment du traitement, après la validation de la transaction.

Les disponibilités de retour/capacité demandent un dossier transporteur admissible.
Elles n'affichent que villes/codes postaux, créneaux et caractéristiques utiles aux
comptes professionnels connectés. Une disponibilité n'est pas une attribution.
Les annonces expirées, fermées ou d'entreprises qui ne sont plus admissibles ne sont
plus présentées aux tiers. Le propriétaire conserve l'accès à son historique.

La messagerie de course est réservée aux parties après attribution et à l'administration.
Les messages sont du texte, avec un identifiant de reprise après réponse perdue.
Les accusés de lecture ne dépassent pas la dernière ligne effectivement chargée.
Le tableau de bord compte demandes ouvertes, offres reçues, courses actives et messages
non lus pour l'entreprise du compte connecté. Les droits serveur restent décisifs.

## Particuliers et devis directs

Le particulier peut déposer un devis CHRONOSS sans SIRET et sans compte professionnel.
Cette extension ne crée pas un compte consommateur Supabase et n'assouplit pas le
contrôle existant des inscriptions professionnelles. Le parcours porte sur une demande
et un contact commercial, sans commande ni paiement en ligne. Les photos et adresses
exactes sont demandées ultérieurement dans un canal adapté si elles sont nécessaires.

Les devis contiennent contact, trajet et code postal, date, description, volume,
étages/ascenseurs, emballage/démontage et fréquence éventuelle. Les adresses réseau
sont transformées en empreintes HMAC pour les limites (jamais enregistrées en clair).
Le module enregistre les demandes avec une référence idempotente et des limites par
empreinte et globales. Le statut du devis et la note restent administratifs.
L'API publique ne permet ni lecture d'un devis ni envoi d'e-mail à un tiers désigné.
Les seules alertes anonymes vont à l'administration fixe ; le demandeur reçoit sa
référence dans la page, sans ajout automatique à une prospection.

Avant acceptation d'une prestation particulière, CHRONOSS doit transmettre un devis
et des conditions adaptés : contenu/manutention, accès, prix TTC, assurances, réserves,
annulation, information et traitement des réclamations, médiation de consommation et
règles de rétractation applicables selon le contrat. Les CGV B2B existantes ne sont pas
présentées comme des CGV consommateur. Aucun nom de médiateur non choisi n'est inventé.
La conservation et les demandes de suppression des devis restent à gérer par
l'administration selon la notice de confidentialité, sans purge automatique annoncée.

## Activation et exploitation

Appliquer supabase/migrations/202610300002_platform_services.sql après la migration
d'horaires. Déployer le worker complet registration-alerts/index.ts sous son nom
existant bright-service. Déployer service-requests/index.ts sous service-requests,
avec verify_jwt=false. Ajouter PLATFORM_ALERTS_ENABLED=true sans retirer les secrets
existants ni le cron. Le fichier LIRE-EN-PREMIER.txt du pack précise l'ordre et les contrôles.
Le site garde un contact par e-mail/téléphone si le formulaire de devis n'est pas encore
activé. Les panneaux professionnels sont conditionnés par la politique serveur.
L'acceptation par Resend n'est jamais présentée comme une preuve d'arrivée en boîte.

Tests : platform-services-sql.cjs, platform-services-http.cjs et site-pages-browser.cjs
DOSSIER --services (PostgreSQL et navigateur locaux, aucune émission réelle), puis
parcours historiques de courses/facturation/documents et mobile/PWA.

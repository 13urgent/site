# Navigation publique par pages — 29 octobre 2026

Chaque rubrique du menu ouvre un fichier HTML distinct : index.html, fonctionnement.html,
courses.html, mes-courses.html, deposer.html, donneurs-ordre.html, transporteurs.html,
mon-espace.html. La rubrique courante porte aria-current="page". Un menu repliable
est disponible sur petit écran, avec fermeture au clavier ; les liens restent natifs.

L’accueil présente uniquement l’introduction. Mon espace regroupe l’accès au compte,
aux justificatifs et aux conditions / abonnements / frais. Les liens historiques
/#courses, /#suivi, /#deposer, /#tarifs et /#abonnement-transporteur sont redirigés vers
la nouvelle page, sans perdre les paramètres de provenance. Les URL de connexion
et de récupération de mot de passe ne sont pas réécrites.

## Sources et construction

Modifier le contenu partagé dans tools/site-template.html, puis exécuter :

    python tools/build_site_pages.py
    python tools/build_admin.py
    python tools/build_mobile.py
    python tools/build_pilot.py --output /chemin/exterieur-vide --open-registration

index.html et les sept pages publiques sont générés. Les styles de séparation sont
dans site-pages.css et le menu mobile / compatibilité des ancres dans site-navigation.js.
Les liens internes et les URL canoniques sont adaptés lors de la génération.

Les modules métier historiques attendent des points de montage communs. Les éléments
hors rubrique restent dans le document, masqués y compris pour les technologies
d’assistance ; ils ne sont pas proposés comme une seconde page à faire défiler.
Cette présentation ne remplace aucune politique Supabase. Connexion, rôles, refus
d’inscription, documents, offres et abonnements conservent leurs contrôles serveur.
L’application mobile garde sa navigation existante et ses liens de réinitialisation.

L’assistant est accessible sur les nouvelles pages. La mesure Google Ads conserve
son consentement distinct et ne déclenche une conversion qu’après publication
confirmée. La mesure interne d’audience reste limitée aux pages déjà autorisées
par la base ; ce changement n’ajoute ni traceur ni extension de collecte serveur.

## Vérification

site-pages-browser.cjs vérifie huit pages à la racine et en sous-dossier, les liens,
la rubrique visible, la connexion simulée conservée entre pages, et un parcours
publication → modification → offre avec PostgreSQL local. Les requêtes extérieures
sont interceptées : aucune course, inscription, conversion publicitaire ou émission
d’e-mail de production n’est créée.

marketplace-pilot-browser.cjs reste le banc de composants partagé sur le gabarit
complet ; site-pages-browser.cjs vérifie la navigation publique réellement générée.
manual-commerce-browser.cjs suit maintenant Mes courses → Mon espace (acceptation
des conditions) → Mes courses pour l’attribution commerciale. Les contrôles mobile,
installation PWA, administration, refus d’inscription, mot de passe et consentement
publicitaire sont également conservés.

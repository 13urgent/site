# Incident : bouton d’offre confidentielle — 28 octobre 2026

Signalement : le propriétaire ne voit aucun résultat après tentative d’offre à 450 € depuis son compte transporteur. La cause exacte du refus de ce compte en production ne peut pas être déterminée sans sa session ou le message renvoyé lors de sa tentative. Aucun droit documentaire ni abonnement n’a été modifié.

Défauts constatés dans le code : le refus était affiché dans le suivi, loin du formulaire ; la validation HTML pouvait empêcher le gestionnaire d’envoi de s’exécuter sans explication persistante ; les courses encore marquées ouvertes dont l’enlèvement est passé restaient proposées alors que le serveur les refuse.

Corrections : retours locaux dans chaque formulaire (validation, progression, erreur, succès), saisie conservée après refus, tarifs français et symbole € acceptés, anti-double envoi, requête bornée dans le temps, contrôles de changement de session, détail des justificatifs et des conditions si le serveur refuse l’accès, exclusion des courses dont l’enlèvement est passé. Le serveur conserve tous ses contrôles de rôle, propriété, documents et droits.

Régression reproduite sous navigateur et PostgreSQL local : valeur invalide expliquée ; refus avec Kbis non approuvé visible au bon endroit sans offre créée ; montant « 450€ » conservé ; approbation de la pièce puis « 450,00 » enregistré à 450 HT ; confirmation visible dans la carte ; confidentialité et parcours d’attribution préservés. Aucun compte réel ni course réelle modifiés pendant ces essais.

Autres contrôles réussis : commerce navigateur/SQL, absence de faux enregistrement local en production, validation d’établissement, consentement Google Ads et construction du site publié.

La correction d’interface ne vaut pas validation du compte signalant le problème. Il reste à lire le retour réel de sa tentative si son compte est refusé. Aucun nouveau SQL ni déploiement de fonction Supabase requis pour cette correction.

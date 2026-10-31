# Préparation et partage des documents par le donneur d'ordre

Migration `202610310005_document_delivery.sql`, après les services/messages privés et le dossier transport déjà installés.

Le donneur d'ordre de la mission attribuée peut préparer la lettre de voiture, tout comme le transporteur attribué. La confirmation reste réservée au donneur d'ordre. L'auteur réel est conservé dans la ligne/version et `prepared_by` ; l'identité imprimée pour le transporteur et son logo sont repris du dossier serveur du transporteur choisi. L'identité du donneur d'ordre ne se substitue pas à celle du transporteur.

Un partage référence une confirmation émise et la dernière lettre enregistrée, sans réécrire les versions. Il est réservé à l'entreprise donneur d'ordre autorisée au module. La course est verrouillée pendant le contrôle des versions. Les rejeux et doubles partages du même lot ne produisent pas de deuxième message. Le transporteur destinataire est déduit de l'offre attribuée et son rattachement actuel est vérifié ; aucune adresse arbitraire n'est acceptée.

La mise à disposition et le message privé sont atomiques. Le message utilise la file de notifications existante ; les exercices sont exclus des e-mails. Aucun PDF n'est rendu public ni joint à une adresse fournie librement. Il ne s'agit pas d'un envoi de deux pièces jointes par e-mail : les documents se récupèrent dans le dossier après connexion. Le résultat du partage ne prouve pas l'arrivée d'un mail dans la boîte du destinataire.

`tests/document-delivery-sql.cjs` : droits des deux entreprises, identité et provenance, états/versions, rejouabilité et notification privée. `tests/site-pages-browser.cjs BUILD --delivery` : parcours complet sur SQL local et sessions simulées, perte de réponse après partage sans doublon, réception transporteur et préparation. Aucune écriture de production ni message réel utilisé dans ces tests.

Le logo et l'adresse du donneur d'ordre sont capturés dans les nouvelles versions par `202610310006_shipper_logo.sql`. La lettre affiche ce logo dans la case donneur d'ordre, distinct des logos du transporteur et de 13 URGENT. Les logos sont retirés de la réponse de liste et chargés avec le seul document complet. Les anciennes versions ne sont pas réécrites ; une nouvelle version est nécessaire après activation.


## Ouverture aux entreprises validées

La migration `202610310007_open_transport_documents.sql` remplace les invitations individuelles du pilote par un accès automatique aux comptes professionnels dont l’établissement est autorisé et l’e-mail confirmé. Les entreprises inscrites après le déploiement bénéficient de la même règle après validation. Une suspension documentaire explicite reste prioritaire ; rejouer l’activation ne la supprime pas. La lecture des documents déjà partagés reste possible aux parties.

Le donneur d’ordre prépare la confirmation et la lettre ; le transporteur attribué peut compléter conducteur, véhicule, poids, quantités et réserves sans invitation supplémentaire au pilote. Les restrictions sur les documents d’une autre entreprise, les rôles, les dossiers clôturés, les versions et les abonnements pour proposer/recevoir une course restent contrôlées sur le serveur. Cette ouverture ne crée aucune nouvelle facturation.

`supabase/setup/open-transport-documents.sql` est la requête unique rejouable : elle installe le partage et le logo s’ils manquent, puis ouvre le module dans une transaction. Elle conserve les versions et les décisions de suspension existantes. `tests/open-transport-documents-sql.cjs` teste ce fichier exact, depuis une installation avec ou sans le logo déjà activé.

Les événements Supabase `TOKEN_REFRESHED` et `SIGNED_IN` répétés pour le même utilisateur ne doivent pas effacer les formulaires. Le changement de compte et la déconnexion continuent à effacer les vues privées. Ce comportement est couvert par le test dédié et le parcours navigateur complet `--opening` : offre en cours, identité/logo, chauffeur/véhicule, outils de mission et formulaire administratif.

Pour le contrôle complet, construire une version de publication puis lancer `python tools/check_launch.py RAPPORT.json DOSSIER_DE_BUILD`. Le script inclut les nouvelles suites automatiquement ; l’export réel des politiques PostgreSQL reste un contrôle distinct nécessitant des métadonnées de production récentes.

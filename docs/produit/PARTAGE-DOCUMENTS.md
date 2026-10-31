# Préparation et partage des documents par le donneur d'ordre

Migration `202610310005_document_delivery.sql`, après les services/messages privés et le dossier transport déjà installés.

Le donneur d'ordre de la mission attribuée peut préparer la lettre de voiture, tout comme le transporteur attribué. La confirmation reste réservée au donneur d'ordre. L'auteur réel est conservé dans la ligne/version et `prepared_by` ; l'identité imprimée pour le transporteur et son logo sont repris du dossier serveur du transporteur choisi. L'identité du donneur d'ordre ne se substitue pas à celle du transporteur.

Un partage référence une confirmation émise et la dernière lettre enregistrée, sans réécrire les versions. Il est réservé à l'entreprise donneur d'ordre autorisée au module. La course est verrouillée pendant le contrôle des versions. Les rejeux et doubles partages du même lot ne produisent pas de deuxième message. Le transporteur destinataire est déduit de l'offre attribuée et son rattachement actuel est vérifié ; aucune adresse arbitraire n'est acceptée.

La mise à disposition et le message privé sont atomiques. Le message utilise la file de notifications existante ; les exercices sont exclus des e-mails. Aucun PDF n'est rendu public ni joint à une adresse fournie librement. Il ne s'agit pas d'un envoi de deux pièces jointes par e-mail : les documents se récupèrent dans le dossier après connexion. Le résultat du partage ne prouve pas l'arrivée d'un mail dans la boîte du destinataire.

`tests/document-delivery-sql.cjs` : droits des deux entreprises, identité et provenance, états/versions, rejouabilité et notification privée. `tests/site-pages-browser.cjs BUILD --delivery` : parcours complet sur SQL local et sessions simulées, perte de réponse après partage sans doublon, réception transporteur et préparation. Aucune écriture de production ni message réel utilisé dans ces tests.

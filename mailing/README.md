# Envois commerciaux autorisés

L’utilisateur a demandé l’envoi aux prospects identifiés, puis choisi `contact@13urgent.fr` comme expéditeur avec consultation des copies dans « Envoyés ». La boîte commerciale distincte n’est plus nécessaire à ce circuit. Les données de prospection restent privées.

Le workflow nécessite deux secrets GitHub Actions :

- `CONTACT_MAIL_PASSWORD` : mot de passe de la boîte e-mail contact, pas celui du compte administrateur OVH.
- `PROSPECTION_CAMPAIGN_JSON` : campagne privée préparée (30 dossiers, uniquement les adresses professionnelles publiées et vérifiées sont éligibles). Ce fichier et ses aperçus ne sont pas dans ce dépôt public.

Le mode `probe` vérifie SMTP et l’accès au dossier IMAP « Envoyés », sans envoyer de message. Le mode `send` respecte la date de campagne et ses destinataires autorisés. Le déclenchement prévu est le lundi vers 8 h 30 Paris ; GitHub peut retarder un passage. Tant que les accès ne sont pas configurés, aucun envoi ne peut partir.

L’envoi utilise OVH SMTP SSL 465 et IMAP SSL 993, avec vérification TLS. Une copie est ajoutée au dossier Sent existant identifié par son attribut IMAP ou son nom conventionnel. Le dossier doit être accessible avant tout envoi externe. Le champ Cc reste contact@13urgent.fr selon la demande initiale.

Une intention est enregistrée avant chaque envoi. Après acceptation SMTP, le message est copié dans Sent ; une panne d’archivage se répare sans réexpédier le message au prospect. Une réponse SMTP incertaine est bloquée sans renvoi automatique. Les états et empreintes du suivi public ne contiennent aucune adresse de prospect, aucun texte de message ni secret. Les exécutions partagent le verrou des workflows marketing pour préserver le registre.

Le statut « accepté et archivé » ne prouve ni réception ni lecture par le destinataire. Les adresses non vérifiées et rôles inadaptés sont laissés en attente. Toute opposition doit être respectée dans la campagne privée avant une nouvelle démarche. Aucune relance automatique ni recherche autonome de nouveaux destinataires n’est déclenchée ici.

Les tests emploient uniquement des transports simulés ; ils n’envoient aucun e-mail et n’accèdent à aucune boîte réelle. La connexion de production doit être vérifiée après ajout des accès.

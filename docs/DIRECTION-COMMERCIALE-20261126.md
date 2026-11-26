# Direction commerciale déléguée — 26 novembre 2026

Autorisation du dirigeant dans la conversation : organisation commerciale et envoi de messages aux transporteurs, donneurs d’ordre et prospects des services CHRONOSS. Aucun budget payant engagé.

`commercial-direction.yml` est borné du 26/11 au 10/12/2026 inclus. Passage les jours ouvrés à 07h30, 12h30 et 16h30 UTC (08h30, 13h30, 17h30 Paris sur cette période). Aucun démarchage froid n’est déclenché par ce workflow.

Il lit au plus 600 en-têtes dans INBOX, puis au plus 40 messages : réponses aux campagnes commerciales reconnues dans le registre et sujets explicites d’essai/demande Mon Exploit. Les messages juridiques, RH et factures sans lien commercial reconnu restent hors sélection. Les pièces jointes ne sont pas exportées.

Le mode `review` ne transmet aucun e-mail : un rapport est chiffré avec un certificat public fourni et conservé un jour dans les artefacts. Aucun contenu de boîte ne figure en clair dans Git ou les logs.

Le mode `run` traite dix nouveaux messages au maximum, envoie au plus cinq questionnaires Mon Exploit par passage et un compte rendu au propriétaire. Un questionnaire est limité à une première demande par correspondant ; il demande les effectifs, le volume, le besoin et les EDI, sans proposer d’accès automatique ni promettre une date ou une fonction indisponible. Les demandes sans validation DMARC passent au compte rendu sans réponse automatique. Une réponse transporteuse ou expéditeur n’obtient aucune offre ni confirmation automatique.

La lecture IMAP est seule (`BODY.PEEK`, INBOX readonly). Les envois utilisent le circuit existant : intention durable avant SMTP, archivage dans Envoyés et blocage après résultat incertain. Les oppositions sont stockées par empreinte et empêchent les futures campagnes chiffrées. La boîte ne reçoit un compte rendu que s’il existe de nouveaux messages sélectionnés. Aucun abonnement payant ni compte client créé.

Les données du registre public se limitent aux empreintes, catégories et états. Les prix transport, confirmations de moyens et conditions négociées restent soumis à la validation du dirigeant.

Arrêt : désactiver le workflow depuis Actions, ou attendre le 10/12 ; le code refuse tout traitement hors période même si la planification subsiste. La pause de la campagne TikTok est indépendante et reste inchangée.

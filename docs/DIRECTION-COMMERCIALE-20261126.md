# Direction commerciale déléguée — 26 novembre 2026

Autorisation du dirigeant dans la conversation : organisation commerciale et envoi de messages aux transporteurs, donneurs d’ordre et prospects des services CHRONOSS. Aucun budget payant engagé.

`commercial-direction.yml` est activé à partir du 26/11/2026. Premier bilan prévu le 10/12/2026, sans arrêt automatique du suivi entrant à cette date. Passage les jours ouvrés à 07h30, 12h30 et 16h30 UTC (08h30, 13h30, 17h30 Paris sur cette période). Aucun démarchage froid n’est déclenché par ce workflow. La poursuite du suivi entrant est autorisée par la délégation de direction commerciale du propriétaire ; volumes fixes par passage, aucun budget engagé.

Il lit au plus 600 en-têtes dans INBOX, puis au plus 40 messages : réponses aux campagnes commerciales reconnues dans le registre et sujets explicites d’essai/demande Mon Exploit. Les messages juridiques, RH et factures sans lien commercial reconnu restent hors sélection. Les pièces jointes ne sont pas exportées.

Le mode `review` ne transmet aucun e-mail : un rapport est chiffré avec un certificat public fourni et conservé un jour dans les artefacts. Aucun contenu de boîte ne figure en clair dans Git ou les logs.

Le mode `run` traite dix nouveaux messages au maximum, envoie au plus cinq questionnaires Mon Exploit par passage et un compte rendu au propriétaire. Un questionnaire est limité à une première demande par correspondant ; il demande les effectifs, le volume, le besoin et les EDI, sans proposer d’accès automatique ni promettre une date ou une fonction indisponible. Les demandes sans validation DMARC passent au compte rendu sans réponse automatique. Une réponse transporteuse ou expéditeur n’obtient aucune offre ni confirmation automatique.

La lecture IMAP est seule (`BODY.PEEK`, INBOX readonly). Les envois utilisent le circuit existant : intention durable avant SMTP, archivage dans Envoyés et blocage après résultat incertain. Les oppositions sont stockées par empreinte et empêchent les futures campagnes chiffrées. La boîte ne reçoit un compte rendu que s’il existe de nouveaux messages sélectionnés. Aucun abonnement payant ni compte client créé.

Les données du registre public se limitent aux empreintes, catégories et états. Les prix transport, confirmations de moyens et conditions négociées restent soumis à la validation du dirigeant.

Arrêt : désactiver le workflow depuis Actions sur demande du propriétaire. Le premier bilan du 10/12 est une échéance de mesure et non une date de fin du projet ou du suivi entrant. La pause de la campagne TikTok est indépendante et reste inchangée.

## Prospection et relance autorisées ensuite dans la conversation

Le dirigeant a explicitement demandé l’envoi à tous les contacts professionnels connus, avec PDF et vidéo, puis une relance en l’absence de réponse. Les contacts sont rapprochés avec l’historique, les rejets et les oppositions ; les coordonnées sont vérifiées sur des sources professionnelles. Un premier lot de dix est préparé ; il ne constitue pas une limite nationale ni une promesse de résultat.

Chaque message de campagne peut joindre un PDF appartenant au catalogue public fermé `PDF_ATTACHMENTS`. URL exacte, taille ≤1Mo, signature PDF et SHA-256 sont vérifiés avant tout envoi ; aucune pièce provenant d’une URL libre ni donnée client n’est acceptée. La vidéo reste un lien dans le corps.

Seules les nouvelles campagnes explicitement marquées `followup_after_days: 7` deviennent éligibles à une relance unique. Le workflow `commercial-followup.yml` passe les jours ouvrés à 08h UTC. Il actualise les réponses avant décision, attend au moins sept jours après le premier envoi accepté et archivé et ne traite que dix relances par passage. Réponse, opposition, rejet définitif, résultat incertain, adresse discordante dans Envoyés ou tentative de relance déjà enregistrée empêchent l’envoi. Aucun rattrapage des anciennes campagnes n’est déclenché automatiquement. Le maximum est un premier message et une relance par contact pour ce cycle.

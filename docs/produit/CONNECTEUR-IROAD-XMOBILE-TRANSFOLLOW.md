# Circuit CHRONOSS : iRoad, X Mobile et TransFollow

Informations fournies par Haeckel le 31 octobre 2026 : exploitation iRoad, application chauffeur X Mobile, signature TransFollow. Le PDF fourni en privé est une lettre de voiture nationale générée par TransFollow, sur deux pages. Aucun accès API ni connexion à ces trois services n'a été établi.

## Ce que montre le document final

- Numéro de lettre de voiture, numéro d'ordre transport et référence client.
- Donneur d'ordre, expéditeur, destinataire, lieux et horaires prévus, transporteur, véhicule/remorque, consignes.
- Marchandise, colis/palettes, poids et volume éventuel.
- Réserves distinguant l'étape, l'auteur et l'heure ; annexes éventuelles.
- Intervenants aux signatures, heures et positions ; statut final.

Les données personnelles, signatures, immatriculations et positions du document source ne sont pas reprises dans cette documentation ni dans les démonstrations.

## Échange cible à valider avec les éditeurs

1. 13 URGENT conserve son UUID de mission et les références d'ordre/client.
2. Une demande d'échange est placée dans une file transactionnelle avec un identifiant stable.
3. Le connecteur autorisé transmet les champs convenus vers iRoad et/ou l'interface désignée par Akanea. Aucun format maison n'est présenté comme un EDI Akanea compatible.
4. La mission rejoint X Mobile et le circuit TransFollow selon les interfaces souscrites et documentées.
5. Les statuts retournés sont rapprochés de la bonne mission, avec accusé et dédoublonnage.
6. Le PDF signé et ses preuves disponibles sont récupérés dans le stockage privé, sans réécriture du contenu signé. La préparation 13 URGENT et le document signé restent deux objets distincts.
7. Le donneur d'ordre et la comptabilité autorisée retrouvent les pièces selon leurs permissions ; un expéditeur/destinataire invité ne voit pas les tarifs et autres missions.

## Informations nécessaires avant de développer la connexion

- Édition/version iRoad, contrat d'interface et documentation API/EDI ; interlocuteur Akanea.
- Point d'entrée réel de création d'e-CMR dans la configuration CHRONOSS.
- API TransFollow accessible directement ou exclusivement par le connecteur Akanea.
- Environnement de test, authentification serveur, permissions et conditions commerciales.
- Champs obligatoires, limites, unités, fuseaux, numérotation et identifiants externes.
- Webhooks ou interrogation périodique ; signature des webhooks, répétitions, délais et états métier.
- Téléchargement du document final et éventuelles preuves, conservation, réversibilité et suppression.

Les secrets resteront dans une configuration serveur dédiée. Ne jamais les déposer dans le JavaScript public ou dans le chat.

## En attendant

Le transporteur peut télécharger le PDF final depuis son outil habituel et le déposer comme « Lettre de voiture » dans la mission 13 URGENT. Il s'agit d'un dépôt manuel privé, pas d'une synchronisation. Les heures et coordonnées de signature ne doivent jamais être inventées à partir des seuls boutons de suivi.

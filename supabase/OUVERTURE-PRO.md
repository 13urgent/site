# Préparation de l'ouverture professionnelle

Décision : uniquement établissements avec SIRET, pour les besoins de leur activité. Particuliers non ouverts. Donneurs d'ordre : dépôt gratuit et frais de mise en relation prévus de 1,5 % du prix HT du transport, TVA sur frais à déterminer. Transporteurs : abonnement mensuel envisagé, tarif non arrêté. Paiement et réservation restent désactivés.

Le formulaire recueille raison sociale, SIRET et déclaration professionnelle dans les métadonnées de nouvelle inscription. Ces données sont déclaratives et modifiables par l'utilisateur : elles ne doivent jamais servir à attribuer un rôle, à valider l'entreprise ni à autoriser une offre. Le contrôle de 14 chiffres n'établit ni l'existence du SIRET, ni son état actif, ni le mandat du déclarant. Prévoir une vérification registre et des autorisations transport avant activation.

La migration 202610170001_business_registration.sql ajoute un trigger BEFORE INSERT sur auth.users : elle refuse les nouvelles inscriptions sans déclaration complète, y compris via appels API directs. Aucun changement des utilisateurs existants. Les invitations ou créations administratives doivent également fournir les métadonnées requises.

Avant application : examiner les triggers existants de création des profils et sociétés, notamment leur utilisation de requested_account_type et des métadonnées role. Le nouveau formulaire transmet seulement le type demandé ; il ne transmet plus de rôle comme s'il était autorisé. Tester ensuite une nouvelle inscription client ET transporteur dans le projet réel. Ne pas déclarer ce parcours opérationnel avant validation de la création des profils et entreprises. Les comptes existants devront faire l'objet d'une vérification professionnelle séparée.

Tests locaux : PostgreSQL embarqué PGlite confirme refus des nouvelles inscriptions incomplètes et conservation des comptes existants. Navigateur avec API simulée : formulaire incomplet refusé, déclarations transmises, aucun rôle attribué par le formulaire, affichage 1,5 %, pas de débordement horizontal à 390 pixels. Aucun test de nouvelle inscription distante réalisé.

Le site est toujours un prototype : demandes de transport locales, offres non activées. Ne pas collecter de frais réels avant validation du parcours métier, des contrats et de la TVA.

Compatibilité contrôlée avec la fonction create_user_profile exportée du projet : celle-ci utilise account_type et company_name. Le formulaire transmet désormais ces deux champs en plus des déclarations professionnelles, sans transmettre de rôle administrateur. Test PGlite signup-compatibility.cjs : création client et carrier, nom entreprise correct, statut pending dans les deux cas. Aucun droit d’offre n’est conféré par ces métadonnées.

## Choix de forfait transporteur
Catalogue mensuel demandé : Découverte gratuite (1 transport/mois), Bronze 12,50 € HT/mois (5), Argent 33,33 € HT/mois (30), Or 62,50 € HT/mois (illimité). Les montants payants sont des prix mensuels proposés à partir des repères annuels de la newsletter, pas une confirmation des conditions actuelles Rubiwin. Arrondi mensuel de la formule Argent : 399,96 € sur douze mois. Pas d'engagement ni de paiement activé. Définition du transport comptabilisé à arrêter avant application des quotas.

Le choix est conservé comme demande déclarative dans les métadonnées du compte (subscription_plan_request, version catalogue), accessible aux administrateurs du projet Supabase via Authentication/Users/Raw JSON. Il ne crée ni abonnement payé, ni autorisation d'offre, ni validation entreprise. Une future gestion serveur des souscriptions et de leur approbation reste à développer ; ne jamais autoriser une offre à partir des métadonnées utilisateur. Les anciennes demandes sans version devront être confirmées avec les conditions définitives. Aucun tarif public détaillé sur l'accueil.

Documents à jour obligatoires même en cas d'abonnement payé. La suspension, les remboursements et les exceptions doivent être définis contractuellement avant souscription ; pas de promesse absolue d'absence de remboursement en cas de désactivation quel qu'en soit le motif.

# Assistant d’assistance et de précontrôle documentaire

## Partie publiée sur le site statique

Le bouton « Besoin d’aide ? » est disponible sur l’accueil et dans les fenêtres
d’inscription et de documents. Il fournit immédiatement, sans inscription ni
clé IA, les réponses documentées sur l’inscription, les liens de connexion,
la confirmation e-mail, le dépôt, les offres, les justificatifs et les tarifs.
Les questions non reconnues sont orientées vers le service privé ou le contact
contact@13urgent.fr. Aucun délai de résolution n’est promis.

Les échanges rapides restent en mémoire dans l’onglet, sans historique local
persistant. La conversation et les résultats privés sont effacés au changement
de compte. Les mots de passe, codes de connexion et liens de confirmation ne
doivent jamais être saisis dans l’assistant.

Avant un envoi documentaire, le navigateur vérifie fichier non vide, taille,
extension, signature PDF/JPEG/PNG, décodage des images lorsque disponible et
date de validité déclarée. Il ne réalise pas d’OCR ni de certification. Le RPC
existant `urgent_document_checklist` fournit aussi la liste des catégories
manquantes, en attente, refusées ou expirées du seul dossier autorisé.

## Activation du suivi privé dans Supabase

L’installation serveur est distincte de GitHub Pages. La session de développement
ne dispose pas d’une connexion d’administration Supabase pour l’effectuer.

1. Dans SQL Editor, exécuter une seule fois
   `supabase/migrations/202610270001_support_assistant.sql`. Ne pas rejouer les
   migrations antérieures. Ce fichier ajoute les tables privées, RPC et quotas ;
   il ne modifie ni les droits commerciaux ni les approbations documentaires.
2. Créer et déployer une **nouvelle** Edge Function nommée `support-assistant`,
   avec le contenu complet de `supabase/functions/support-assistant/index.ts`.
   Ne pas remplacer `bright-service`, qui conserve les alertes d’inscription et
   rapports. Désactiver la vérification JWT legacy de la nouvelle fonction : le
   handler vérifie lui-même les JWT réels via `/auth/v1/user`. Le statut public
   ne révèle aucune donnée personnelle.
3. Conserver les secrets serveur Supabase existants. Le service fonctionne sans
   clé OpenAI : réponses factuelles, précontrôles de métadonnées et demandes
   privées d’assistance. Les nouvelles demandes peuvent notifier uniquement
   `saschronoss@outlook.com`, avec les secrets globaux Resend déjà utilisés
   (`RESEND_API_KEY`, `REGISTRATION_ALERTS_FROM`). Aucun destinataire fourni par
   le navigateur n’est accepté.

Après installation, l’assistant détecte automatiquement le statut du service.
Les boutons de transmission et de suivi apparaissent. Un compte connecté peut
enregistrer une demande puis lire la réponse dans « Mes échanges avec
l’administration ». L’administrateur trouve « Demandes d’assistance » sur
`admin.html` et peut répondre/clôturer. Une panne d’e-mail n’efface pas le ticket
et ne produit pas de fausse confirmation de notification.

Les personnes bloquées avant inscription ont les réponses rapides et le lien
de contact ; elles n’obtiennent pas de ticket privé anonyme ni d’accès à un
dossier par simple recherche d’adresse e-mail.

## Lecture de pièces et questions libres avec IA — option distincte

Cette option utilise l’API OpenAI, facturée séparément d’un abonnement ChatGPT.
Elle reste désactivée tant que les paramètres suivants ne sont pas configurés
dans **Edge Functions → Secrets** :

```text
OPENAI_API_KEY=<clé API privée, à saisir uniquement dans Supabase>
SUPPORT_AI_ENABLED=true
SUPPORT_DOCUMENT_AI_ENABLED=true
```

Le modèle par défaut est `gpt-4.1-mini` ; `OPENAI_SUPPORT_MODEL` permet de le
changer pour un modèle compatible Responses, vision, PDF et JSON Schema.
Ne jamais mettre la clé dans `config.js`, dans GitHub ou dans une conversation.

Les questions connues sont traitées sans appel IA. Les autres sont limitées à
1500 caractères et les coordonnées simples sont masquées avant traitement.
Les réponses utilisent une base métier bornée, sans outil capable de modifier
les comptes, rôles, abonnements, courses ou approbations.

Une préanalyse documentaire est demandée depuis « Mes documents » ou un dossier
administrateur. Le serveur contrôle l’identité et l’accès avant toute lecture,
puis peut rapprocher les mentions visibles de la catégorie, la date, la raison
sociale et le SIRET vérifié disponible au dossier. Les références absentes sont
signalées comme inconnues. Les fichiers restent dans le bucket privé ; leur
contenu est transmis à l’API pour l’analyse, avec `store:false`, sans création
d’un objet persistant via Files. Les règles de traitement/conservation du
prestataire restent applicables. Informer les utilisateurs dans la notice de
confidentialité avant activation.

Le service analyse au maximum 5 Mo par fichier ; un fichier de 5 à 10 Mo reste
admissible au dépôt mais nécessite l’examen manuel. Quotas atomiques : 30
questions, 5 préanalyses et 5 tickets par compte/jour ; 10 appels IA par
compte/jour et 20 tous comptes confondus/jour. Ces quotas ne sont pas un plafond
monétaire : configurer également les limites de dépense du fournisseur.

Le verdict de l’IA est toujours un avis préparatoire (`needs_attention` ou
`manual_review`). **Il ne devient jamais `approved`.** L’authenticité, les
garanties et les cas ambigus exigent une décision administrative et, si
nécessaire, une vérification auprès des sources officielles. Les nouvelles
pièces restent en attente et les protections serveur existantes sont conservées.

## Vérification réelle après activation

1. Ouvrir « Besoin d’aide ? » sans compte : réponse immédiate à une question
   d’inscription ; aucune demande de mot de passe ou de lien secret.
2. Avec un compte de contrôle, transmettre un problème clairement identifié
   comme contrôle de fonctionnement. Vérifier son enregistrement et la réception
   de l’alerte propriétaire, sans inventer un incident client.
3. Répondre depuis l’administration ; vérifier la lecture depuis le compte
   concerné. Un autre compte ne doit rien voir.
4. Demander un avis sur une pièce autorisée si l’IA est activée. Vérifier les
   mentions inconnues et l’absence de changement du statut d’approbation.

Les tests locaux interceptent OpenAI, Resend et Supabase. Ils ne prouvent ni
leur déploiement ni une livraison réelle. `tests/support-assistant-http.cjs`
vérifie aussi les RLS/quotas sur PostgreSQL local ; `tests/support-browser.cjs`
couvre les changements de compte, le rendu texte et l’escalade ;
`tests/document-assistant-browser.cjs` couvre les fichiers et dates.

Arrêt : `SUPPORT_ASSISTANT_ENABLED=false` coupe les actions serveur. Les réponses
rapides locales restent utilisables. `SUPPORT_AI_ENABLED=false` et
`SUPPORT_DOCUMENT_AI_ENABLED=false` coupent seulement les appels IA.
La migration prévoit une purge quotidienne lorsque `pg_cron` est disponible :
tickets après 180 jours sans mise à jour, avis après 90 jours et quotas après
8 jours. Les copies d’e-mails nécessitent leur propre gestion de conservation.

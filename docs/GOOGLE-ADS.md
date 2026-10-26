# Mesure des demandes publiées — Google Ads

Compte fourni par l’exploitant : `AW-18537989618`. Action « Demande de devis » :
`AW-18537989618/iTMnCKiasaodEPKLzYdF`.

La campagne est maintenue en veille dans Google Ads par l’exploitant. Le déploiement
du site ne réactive pas la campagne et ne change ni budget, enchères, facturation,
date de fin ou réglages de conversion du compte.

## Déclenchement

`marketplace.js` appelle le module facultatif uniquement après le succès du RPC
`urgent_publish_shipment`, avec l’UUID renvoyé par le serveur. Un échec, une simple
visite, un clic sur le formulaire, une inscription ou un rafraîchissement ne sont
pas une conversion. Les publications administrateur et exercices fictifs sont
exclus. Une panne du module ne doit jamais bloquer une publication.

Le montant de 1 EUR est conservé pour correspondre à l’extrait fourni ; il s’agit
d’une valeur technique, pas de chiffre d’affaires ni du prix du transport.
`transaction_id` utilise la référence aléatoire de la demande, pour dédupliquer
les envois. Aucun contenu du formulaire ni donnée d’identité n’est ajouté au
message de conversion. Les paramètres d’URL et le fragment sont exclus de la
valeur `page_location` explicitement fournie à la balise.

## Consentement

`google-ads.js` est livré uniquement sur l’accueil public. Il ne charge la
bibliothèque Google qu’après un accord publicitaire distinct de l’audience
interne. Le panneau est placé avant le pied de page ; « Gérer la mesure
publicitaire » permet de le rouvrir. L’absence de choix, le refus, l’expiration,
GPC et DNT empêchent le chargement. Aucune conversion n’est mise en attente pour
un consentement ultérieur. Le service reste utilisable après refus.

Mode de consentement basique : `ad_storage` et `ad_user_data` ne sont accordés
qu’après consentement ; `analytics_storage` et `ad_personalization` restent
refusés. Personnalisation et suivi avancé par coordonnées sont désactivés dans
la configuration. Le retrait efface les cookies Google Ads de première partie
accessibles, le registre local des conversions, puis recharge la page pour
décharger la bibliothèque. Le bouton de retrait annonce ce rechargement.

## Validation et limites

- `tests/google-ads-browser.cjs` intercepte tout appel Google : accord distinct,
  refus, retrait, expiration, GPC, doublons, tests/admin, absence de coordonnées
  dans les paramètres explicitement émis et ergonomie mobile.
- `tests/marketplace-pilot-browser.cjs` publie sur une base PostgreSQL locale :
  un refus RPC n’émet rien ; le succès émet une conversion portant l’UUID retourné.
- `tools/check_launch.py` inclut ces contrôles. Les tests ne créent ni demande
  réelle en production ni conversion réelle dans Google Ads.

La réception effective doit être vérifiée dans Tag Assistant après consentement
et dans Google Ads lors d’une demande légitime. Un bloqueur, un refus ou une
erreur réseau peut empêcher une mesure. Une conversion émise n’est pas une
preuve d’attribution à une annonce. Ne pas créer de fausses demandes ni cliquer
sur sa propre annonce pour tester.

Avant diffusion, l’exploitant doit vérifier le français, la présence géographique
en France, le budget de 5 EUR/jour, une date de fin après sept jours, les mots-clés
à exclure et le réglage « Une » pour le comptage des prospects si souhaité. Le
budget quotidien est une moyenne ; ce n’est pas un plafond total de campagne.

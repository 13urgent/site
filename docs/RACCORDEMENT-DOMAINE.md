# Raccordement 13urgent.fr à GitHub Pages — 20 octobre 2026

Demande de l’utilisateur : utiliser le site existant sur GitHub Pages sans attendre le FTP OVH, en conservant OVH pour le domaine et les e-mails.

## État initial d’après la capture OVH

- NS dns103.ovh.net et ns103.ovh.net, à conserver.
- A @ et www : 51.91.236.255, à remplacer pour le Web.
- AAAA @ et www : 2001:41d0:301::29, anciennes cibles Web à retirer si aucun IPv6 GitHub n’est installé.
- TXT @ « 1|www.13urgent.fr » et www « 3|welcome » : anciennes redirections/accueil OVH à retirer dans ce raccordement.
- MX mx1.mail.ovh.net / mx2.mail.ovh.net / mx3.mail.ovh.net, SPF OVH, sélecteurs DKIM OVH : conserver intégralement. Ne pas réinitialiser la zone DNS.
- CNAME ftp vers 13urgent.fr : ce nom suivra le nouveau site ; pour l’ancien FTP, continuer à utiliser ftp.cluster129.hosting.ovh.net. Ce raccordement ne répare pas l’authentification FTP.

## Déclaration côté GitHub

Le fichier CNAME de publication contient 13urgent.fr et sera conservé par le constructeur. Vérifier dans le dépôt 13urgent/site → Settings → Pages que Custom domain affiche bien 13urgent.fr (sinon le saisir et enregistrer) avant de pointer les DNS. Le fichier ne prouve pas à lui seul que le domaine est accepté ni qu’un certificat est émis. L’API Pages est inaccessible depuis la session cloud (CONNECT 403).

## Cibles DNS Web

| Sous-domaine OVH | Type | Cible |
| --- | --- | --- |
| @ (champ sous-domaine vide dans le formulaire) | A | 185.199.108.153 |
| @ | A | 185.199.109.153 |
| @ | A | 185.199.110.153 |
| @ | A | 185.199.111.153 |
| www | CNAME | 13urgent.github.io. |

Le CNAME www ne doit pas coexister avec les anciens A, AAAA et TXT www. Ne pas y saisir https:// ou /site/. L’apex conserve les enregistrements mail et NS ; ne pas remplacer son contenu par un CNAME.

Les quatre A correspondent aux adresses publiées dans la documentation GitHub Pages : https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site . Recontrôler si GitHub signale une évolution ou un conflit de domaine.

Les changements DNS doivent être effectués par l’utilisateur dans sa zone OVH ; aucun accès d’écriture DNS n’est disponible dans cette session. Conserver une exportation de la zone avant modification et les anciennes cibles ci-dessus pour retour arrière.

## Vérifications après modification

Attendre la prise en compte DNS, vérifier GitHub Pages → DNS check, puis activer Enforce HTTPS lorsque le certificat est disponible. Aucun délai immédiat de propagation ou de délivrance de certificat n’est garanti.

Tester https://13urgent.fr/ et https://www.13urgent.fr/, logo, contact, conditions, vidéos et connexion. Le domaine personnalisé sert le site à la racine, sans /site/. Les inscriptions et le mode commercial restent ceux configurés précédemment ; les DNS ne les ouvrent pas.

Dans Supabase Authentication → URL Configuration, ajouter https://13urgent.fr/ et https://www.13urgent.fr/ aux Redirect URLs sans retirer les adresses de recette existantes. Définir la Site URL définitive sur https://13urgent.fr/ lors du basculement. Vérifier les e-mails de confirmation et liens de connexion ; leur configuration ne se déduit pas du DNS Web.

Envoyer et recevoir un message de test contact@13urgent.fr après raccordement. Les MX/SPF/DKIM restent inchangés. Ne publier les vidéos de lancement qu’après vérification du parcours réellement ouvert.

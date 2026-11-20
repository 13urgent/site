# Maintenance eCMR et TMS

L'accès a été demandé par le propriétaire. La clé privée dédiée est ajoutée manuellement dans GitHub Actions Secrets sous `CHRONOSS_MAINTENANCE_SSH_KEY`. Aucun secret ni code métier privé n'est publié ici.

L'identité SSH du serveur est épinglée dans `known_hosts` et son empreinte a été comparée à celle lue par le propriétaire dans sa session SSH. L'installation de `server.py --install` nécessite une première session root déjà authentifiée du propriétaire. Elle ajoute uniquement la clé publique avec `restrict` et une commande imposée. Les autres clés et réglages SSH sont conservés. Aucun redémarrage de l'application n'est réalisé pendant cette installation.

Commandes distantes permises : `status ecmr`, `status tms`, `diagnose ecmr`, `diagnose tms`, et `deploy <ecmr|tms> <sha256>` avec archive sur l'entrée standard. Ni shell interactif ni SCP/SFTP ni transfert de port ne sont disponibles avec cette clé. La capacité de mise à jour autorise le remplacement du code des applications, y compris le programme de migration eCMR exécuté avec les droits nécessaires ; conserver ce secret exclusivement dans des workflows de confiance.

Les mises à jour transitent dans une demande CMS chiffrée avec certificat éphémère du seul exécuteur GitHub. Seuls le CMS et les scripts génériques sont publiés. Le source privé, les bases, les fichiers `.env`, les clés applicatives, les paramètres Caddy et les fichiers Compose ne sont pas copiés dans le dépôt ni remplacés par cette procédure.

`deploy` vérifie les empreintes, les chemins et les limites de l'archive. Il conserve les sources précédentes. L'eCMR appelle son programme de sauvegarde/migration existant ; le TMS utilise sa sauvegarde SQLite existante avant toute modification et conserve l'image précédente pour retour en arrière si le démarrage échoue. Le retour à l'image précédente ne prétend pas annuler une migration de données. Une archive déjà appliquée ne rejoue pas ses migrations.

Les résultats techniques sont des artefacts à rétention courte. Ils ne constituent ni une preuve de réception des mails ni une vérification complète du fonctionnement métier.

Pour révoquer l'accès : supprimer le secret Actions ET retirer seulement la ligne contenant `chronoss-maintenance-20261120` dans `/root/.ssh/authorized_keys`. Ne pas effacer les autres clés. La clé privée n'est jamais à coller dans le chat, une issue ou un fichier Git.

# Suppression des connexions et conservation des archives

La migration `202610310008_account_cleanup.sql` installe les contrôles de comptes clos ; elle ne supprime aucun compte à elle seule. La commande `urgent_close_login_accounts` ne peut pas être appelée par un navigateur authentifié, un visiteur ou le rôle service : elle s’exécute depuis le SQL Editor avec les droits du propriétaire SQL.

La commande reçoit une référence stable, trois adresses à conserver, la liste exacte des autres adresses et l’administrateur conservé. Elle s’arrête avant toute mutation si un compte attendu manque ou si une adresse imprévue est présente. Une nouvelle exécution de la même référence rend le résultat déjà enregistré.

Les comptes retirés sont marqués supprimés dans Auth. Les moyens de connexion, mots de passe, jetons et identités sont supprimés ou neutralisés, et l’adresse de connexion est anonymisée. L’identifiant technique de l’utilisateur reste présent pour les clés étrangères et les acteurs de documents historiques. Les profils historiques restent conservés mais sortent des annuaires actifs.

Les trois comptes conservés ne sont pas modifiés. Les courses, offres, documents, fichiers, forfaits et écritures historiques ne sont pas effacés. Les validations de sociétés dont aucun compte actif ne subsiste sont suspendues. Les nouvelles inscriptions restent possibles après ce nettoyage ponctuel.

`urgent_account_is_active` protège les identités métier et ajoute une limite RLS restrictive aux tables publiques déjà protégées ainsi qu’aux objets Storage. Les anciens JWT des comptes retirés ne donnent plus de rôle/entreprise ni d’accès aux données. Les tables de clôture sont privées. Les annuaires métier utilisent la vue des profils actifs ; les documents et anciennes entreprises restent accessibles aux fonctions serveur d’historique autorisées.

`tests/account-cleanup-sql.cjs` vérifie les trois comptes conservés inchangés, les quatre moyens de connexion supprimés, la révocation des anciens accès, l’intégrité des courses/documents/acteurs, les annuaires filtrés, le refus d’un compte imprévu, l’absence de droit d’exécution depuis le navigateur et la reprise de la même demande. Le même test peut exercer un paquet opérateur exact avec un fichier de correspondance vers des comptes synthétiques, sans utiliser de données de production.

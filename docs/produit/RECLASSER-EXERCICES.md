# Reclasser un essai déclaré comme transport normal

Le nom « test » d'un fichier PDF ne change pas le marqueur `is_test` d'une mission. La migration `202610310004_reclassify_exercise.sql` crée une action administrative explicite pour corriger cette classification avant chargement.

Le serveur exige l'administrateur, un motif et une attestation. Il verrouille la mission et les écritures concernées, bloque les références à une facture externe, crédite le solde de frais non facturés avec l'API de crédit existante, puis conserve la décision et l'événement de suivi. L'ensemble est transactionnel et rejouable sans double crédit. Les offres, statuts et instantanés documentaires restent conservés. Une nouvelle version documentaire est nécessaire pour porter la mention fictive ; les anciens PDF ne sont pas réécrits.

L'action refuse les courses déjà chargées, en livraison, achevées, annulées ou archivées. L'installation n'effectue aucune reclassification et ne modifie aucun compte ni abonnement. L'accès au stockage privé n'est pas élargi.

Le classement en exercice et le rangement sont distincts. Un exercice encore ouvert peut rester visible comme fictif ; le rangement existant permet de le retirer des listes courantes une fois l'essai terminé.

Tests : `tests/reclassify-exercise-sql.cjs` couvre les rôles, états, reprises, soldes, factures externes, immutabilité et rollback atomique ; `tests/exercise-reclassification-browser.cjs` couvre le formulaire administratif, la capacité manquante, les erreurs et le suivi actualisé. Les données et utilisateurs de ces tests sont fictifs, sans écriture en production.

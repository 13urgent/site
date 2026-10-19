# Correction des catégories documentaires — 19 octobre 2026

La contrainte du projet réel autorise : registration, transport_licence, insurance_goods, insurance_rc et other. Le formulaire et la première version du pilote utilisaient insurance, valeur refusée par la base. Les tests antérieurs ne reproduisaient pas cette contrainte ; les fixtures SQL la reproduisent désormais.

## Installation sur un pilote déjà créé

1. Appliquer uniquement `supabase/migrations/202610190001_document_categories.sql` dans SQL Editor. Ne pas rejouer la migration de création du pilote.
2. Mettre à jour `index.html` et `documents.js` de la copie locale depuis GitHub, sans remplacer le config.js local déjà activé. Actualiser avec Ctrl+F5.
3. Le formulaire distingue assurance responsabilité civile et assurance marchandises. Le pilote vérifie les quatre catégories documentaires, les approbations et les expirations. Il s'agit d'une politique restrictive du pilote, pas d'une affirmation des obligations légales pour tous les métiers.
4. Aucun document existant n'est reclassé automatiquement. Dans le dossier CHRONOSS, la licence et une attestation d'assurance ont été envoyées comme registration. Leur correction précédente a échoué atomiquement, sans modification conservée.
5. Reclasser la licence comme transport_licence et la repasser en attente pour revue de sa bonne catégorie. Pour l'attestation Orus, vérifier les garanties effectivement couvertes avant de choisir insurance_rc, insurance_goods ou de justifier les deux. Ne pas supposer une couverture à partir du nom du fichier. Conserver les dates de validité exactes ; ne jamais inventer d'expiration.
6. Une même attestation peut soutenir deux catégories uniquement si elle justifie effectivement les deux garanties. La séparation des catégories ne signifie pas obligatoirement deux polices différentes. La validation est une décision humaine après lecture.

La correction ne supprime ni la contrainte ni les RLS ni les justificatifs. La création d'une catégorie artificielle insurance pour contourner l'erreur n'est pas nécessaire.

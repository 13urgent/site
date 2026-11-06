# Publication automatique 13 URGENT

Déployé pour l’activation demandée le 6 novembre 2026. Les accès Buffer sont fournis uniquement par le secret GitHub Actions `BUFFER_API_KEY`. La clé et les données de compte ne figurent jamais dans le code ou les journaux.

## Exécution

Le workflow `Marketing 13 URGENT` prépare les contenus du lendemain vers 8 h à Paris. Deux passages UTC couvrent l’heure d’été et d’hiver ; seul celui correspondant à 8 h à Paris est exécuté. GitHub peut retarder le déclenchement ; il ne s’agit pas d’une garantie à la minute.

- TikTok : une capsule à 18 h chaque jour.
- LinkedIn profil : lundi, mercredi, vendredi à 12 h 15.
- LinkedIn page : lundi, mercredi, vendredi à 17 h 15.
- Fuseau : Europe/Paris, conversion UTC gérée par Python.

Les vidéos sont produites en amont, puis programmées dans Buffer. Une réponse `scheduled` et `automatic` avec l’heure conforme est exigée. Le prochain passage compare les statuts des publications connues pour distinguer envoi effectif et erreur. Une programmation n’est pas présentée comme un envoi réalisé.

L’autorisation donnée par Haeckel permet la diffusion organique sans nouvelle validation manuelle. Pas d’envoi privé LinkedIn, ni de publicité payante, ni de campagne e-mail déclenchés par ce workflow.

## Production et contrôle

Douze sujets préparés couvrent les donneurs d’ordre, transporteurs et demandes de devis de particuliers. Un sujet est sélectionné par date. Chaque capsule illustrée dure 20 secondes, en 1080×1920, avec logo officiel, textes à l’écran et musique instrumentale synthétisée, sans voix off ni données de client. Cette musique n’est pas présentée comme un titre tendance.

Le contrôle éditorial applique des règles explicites : format, liens autorisés, promesses exclues et cohérence des publics. Cela automatise la production et la diffusion d’un catalogue préparé. Il ne constitue pas une veille autonome des tendances, ni une équipe d’IA permanente recherchant chaque jour de nouveaux sujets. Aucune API d’IA payante n’est appelée.

Les liens portent des paramètres UTM pour distinguer les campagnes ; ils ne prouvent pas à eux seuls une conversion. Les résultats commerciaux nécessitent les données de la plateforme et de Buffer. Aucune promesse de vues, de clients ou de chiffre d’affaires.

## Fiabilité

La branche `marketing-state` conserve uniquement les empreintes et états d’envoi. Une intention est enregistrée localement puis poussée avant chaque mutation Buffer. Une interruption, un délai réseau dépassé ou une réponse incertaine bloque le renvoi automatique du même contenu. Les exécutions GitHub sont sérialisées. Les vidéos sont ajoutées à `gh-pages` sans remplacer les autres fichiers ; leurs URL GitHub brutes sont vérifiées avant programmation.

Les erreurs et les états incertains doivent être examinés dans Buffer avant toute correction du registre. Ne pas supprimer une intention pour relancer à l’aveugle.

## Utilisation

- Test de connexion sans publication : lancer le workflow avec `mode: probe`.
- Préparation et programmation : `mode: publish`.
- Arrêt : désactiver `Marketing 13 URGENT` dans l’onglet Actions, ou mettre `enabled: false` dans `marketing/config.json`. Les posts déjà programmés restent à annuler dans Buffer si nécessaire.
- La clé Buffer expire selon le choix effectué à sa création ; la remplacer dans le même secret avant l’échéance.

## Vérifications locales

```sh
python -m pip install -r marketing/requirements.txt
python marketing/content/validate_content.py
python -m unittest discover -s marketing/publisher -p 'test_*.py'
python -m unittest discover -s marketing -p test_pipeline.py
python marketing/pipeline.py --mode preview --date 2026-11-07
```

Le mode preview ne contacte pas Buffer. FFmpeg et les fontes DejaVu sont nécessaires pour la vidéo. Le mode probe consulte les comptes sans mutation. Aucun secret ne doit être copié dans la conversation, un fichier du dépôt ou un journal.

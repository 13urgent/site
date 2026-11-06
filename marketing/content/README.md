# Catalogue de présentation 13 URGENT

Préparé le 6 novembre 2026 pour LinkedIn (profil de Haeckel Hamri et page Chronos) et TikTok (13urgentsite).

Le catalogue comporte 12 sujets : 6 pour les donneurs d’ordre, 4 pour les transporteurs et 2 pour les particuliers demandant un devis CHRONOSS. Chaque sujet fournit deux variantes LinkedIn, une description TikTok, cinq textes d’écran, une destination et un appel à l’action.

```sh
python content/build_catalogue.py
python content/validate_content.py
```

Depuis Python :

```python
import json
from pathlib import Path
from validate_content import validate_catalogue

catalogue = json.loads(Path("catalogue.json").read_text())
errors = validate_catalogue(catalogue)
if errors:
    raise ValueError(errors)
topic = catalogue["topics"][0]
print(topic["linkedin_founder"])
print(topic["scenes"])
```

Le contrôle refuse notamment les destinations non prévues, les formats trop longs, les champs requis manquants, les coordonnées personnelles potentielles et une liste de promesses ou de fonctions non autorisées. Il ne contacte aucun service et ne vérifie pas les pages en ligne.

**Portée réelle :** textes préparés et contrôle déterministe. Ces fichiers ne créent pas un agent IA permanent, ne réalisent pas de veille des tendances et ne prouvent pas le fonctionnement des fonctions en production. Ils n’envoient, ne programment et ne publient rien. Une évolution du produit impose de revoir le catalogue.

Les scripts d’écran sont des capsules de présentation : ne pas les présenter comme un enregistrement réel de l’interface ou comme un témoignage client. La musique et les médias doivent disposer des autorisations nécessaires à chacun des réseaux.

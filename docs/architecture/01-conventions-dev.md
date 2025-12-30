# Conventions de Développement (Persona)

## Objectif
Définir comment l’IA doit produire du code conforme au projet SoniqueBay : propre, maintenable, cohérent avec Docker, adapté RPi4.
## Environnment
Le développement est fait sous windows  avec VS Code ,  les commandes doivent être compatibles PowerShell ou Batck windows 

## Style & Qualité
- PEP8 obligatoire
- Formatter : black + isort + ruff
- Typage Python strict (`typing`)
- Docstrings pour modules, classes et fonctions
- Imports absolus

## Logs
- Interdiction de `print`
- Utiliser `utils/logging.py` dans chaque module principal
- Logs structurés (pas de texte brut)

## Docker
- 1 dépendance = ajout dans le bon service
- Ne jamais toucher Dockerfile/docker-compose sans justification explicite
- Build obligatoire avant commit: `docker-compose build && docker-compose up`

## Tests
- Pytest + pytest-xdist
- Exécution dans Docker aussi (pas seulement local)
- Tests dans `tests/` par module
- Pas de régression

## Structure Code
- Architecture modulaire (API / Worker / UI / DB)
- Pas de duplication de logique
- Services = classe métier
- Frontend ne parle qu’à l’API/WS/SSE

## Objectif pour l’IA
Chaque génération de code doit respecter :
1. Performance RPi4
2. Séparation des responsabilités
3. Conventions Docker
4. Tests possibles & lisibles

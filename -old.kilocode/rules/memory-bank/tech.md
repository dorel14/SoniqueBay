# Tech Context

## Stack Technique
- **Langage** : Python 3.x
- **Frontend** : NiceGUI (Web framework)
- **Backend** : FastAPI + Strawberry (GraphQL)
- **Agent IA** : PydanticAi
- **Vectorisation** : Ollama (LLM local)
- **Task Queue** : Celery
- **Database** : PostgreSQL
- **Cache/PubSub** : Redis
- **Search** : Postgresql FTS (Indexation locale légère) + Vectorisation (Embeddings)
- **Environnement de développement** : Windows
- **Environnement de production** : Raspberry Pi 4 + Docker + Docker Compose

## Environnement de Développement
- **OS Dev** : Windows (VS Code). Les commandes générées doivent être compatibles PowerShell/Batch.
- **Formatters** : Black, Isort, Ruff.
- **Containerisation** : Docker & Docker Compose obligatoires pour simuler la prod.

## Contraintes de Déploiement (Cible : Raspberry Pi 4)
- **CPU** : ARM Quad-core. Éviter les boucles bloquantes. Utiliser `asyncio`.
- **RAM** : Limitée (2-8 Go). Attention aux chargements en mémoire (ex: ne pas charger tous les vecteurs d'un coup).
- **Stockage (SD Card)** :
    - Minimiser les écritures de logs (rotation).
    - Optimiser les images Docker (tailles réduites).
- **Réseau** : Optimiser les payloads JSON et utiliser la pagination.

## Sécurité
- Authentification par token sur l'API locale.
- Pas d'exposition directe de la DB sur le réseau.
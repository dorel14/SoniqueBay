# Audit des Duplications backend/ vs backend_worker/

## Répertoires Présents dans les Deux

- `api/` : backend/api a la structure complète API (models, routers, schemas, services, utils, graphql, api_app.py). backend_worker/api a seulement schemas/ avec embedding_schema.py et vectorization_router.py

- `data/` : Les deux ont data/img/artist/ avec des fichiers .webp (probablement partagés)

- `services/` : backend/services a album_service.py. backend_worker/services a de nombreux services (scan_optimizer.py, entity_manager.py, etc.)

## Répertoires Uniques à backend/

- `ai/` : Logique AI (agents, orchestrateur, etc.)

- `opensubsonic/` : Implémentation OpenSubsonic

## Répertoires Uniques à backend_worker/

- `db/` : Accès DB direct pour workers (engine.py, session.py, repositories/)

- `taskiq_tasks/` : Tâches TaskIQ migrées

- `tasks/` : ?

- `utils/` : Utilitaires workers

- `workers/` : Logique workers

- `models/` : Modèles DB (probablement dupliqués avec backend/api/models/)

- `background_tasks/` : ?

- `logs/` : Logs workers

- `feature_flags.py` : Feature flags

- `taskiq_app.py` : Configuration TaskIQ

- `taskiq_worker.py` : Point d'entrée worker

- etc.

## Conclusion

Les duplications sont minimales. La structure est déjà bien séparée :

- `backend/` : API principale, AI, OpenSubsonic

- `backend_worker/` : Logique workers, tâches async, accès DB direct

Pour la fusion :

- Créer `backend/tasks/` pour accueillir `taskiq_tasks/`

- Créer `backend/workers/` pour accueillir `db/`, `utils/`, `workers/`, etc.

- Intégrer les parties API de backend_worker dans backend/api/ si nécessaire (vectorization_router.py → routers/)

- Supprimer backend_worker/ après migration
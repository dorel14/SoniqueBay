# Tickets Phase 6 — Documentation & Logs

## [TICKET-P6-001] Mettre à jour les docstrings (45+ fichiers)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: 45+ fichiers contiennent des références à "Celery" dans les docstrings et commentaires. Mettre à jour :
- Remplacer "Worker Celery" par "Worker TaskIQ"
- Remplacer "Tâches Celery" par "Tâches TaskIQ"
- Remplacer "worker Celery" par "worker TaskIQ"
- Remplacer "celery_app" par "taskiq_broker" dans les descriptions

Fichiers prioritaires :
- `backend_worker/workers/synonym_worker.py` (docstring ligne 3)
- `backend_worker/workers/artist_gmm/artist_gmm_worker.py` (docstring ligne 5)
- `backend_worker/tasks/maintenance_tasks.py` (docstring ligne 3)
- `backend_worker/tasks/diagnostic_tasks.py` (docstring ligne 2)
- `backend_worker/tasks/covers_tasks.py` (docstring ligne 2)
- `backend_worker/utils/logging.py` (références "workers Celery")
- `backend/api/services/scan_service.py` (docstring ligne 3)
- `backend/api/services/artist_embedding_service.py` (docstring ligne 8)
- `backend/api/services/vectorizer_service.py` (docstring ligne 5)
- `backend/api/services/track_vector_service.py` (16 références)
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.5 jour

---

## [TICKET-P6-002] Mettre à jour les logs
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Mettre à jour les préfixes de logs :
- Remplacer `[CELERY]` par `[TASKIQ]` dans les logs
- Remplacer `[SYNONYM_WORKER]` par `[TASKIQ|SYNONYM]` si le préfixe est utilisé
- Remplacer `[CELERY→TASKIQ]` par `[TASKIQ]`
- Remplacer "Fallback vers Celery" par "Exécution via TaskIQ"

Fichiers à vérifier :
- `backend_worker/tasks/maintenance_tasks.py` (lignes 35, 88, 188, 245, 300)
- `backend_worker/services/scan_optimizer.py` (lignes 135-191)
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour

---

## [TICKET-P6-003] Mettre à jour les schémas Pydantic
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Mettre à jour les références à Celery dans les schémas Pydantic :
- `backend/api/schemas/synonyms_schema.py` (ligne 9, 89, 91) : remplacer "Celery" par "TaskIQ"
- `backend/api/schemas/gmm_schema.py` (ligne 65) : remplacer "Celery" par "TaskIQ"
- `backend/api/schemas/track_embeddings_schema.py` (ligne 215) : remplacer "Celery" par "TaskIQ"
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P6-004] Mettre à jour les routers API (commentaires)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Mettre à jour les commentaires dans les routers API :
- `backend/api/routers/covers_api.py` (13 références "tâche Celery")
- `backend/api/routers/gmm_api.py` (11 références "tâche Celery")
- `backend/api/routers/synonyms_api.py` (8 références "Celery")
- `backend/api/routers/celery_admin_api.py` (à renommer en `taskiq_admin_api.py`)
**Dépendances**: CLEAN-2 (fichiers Celery supprimés)
**Durée estimée**: 0.25 jour

---

## [TICKET-P6-005] Mettre à jour README.md
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Mettre à jour le README.md principal :
- Remplacer les références à Celery par TaskIQ
- Mettre à jour les instructions de démarrage
- Mettre à jour l'architecture (TaskIQ au lieu de Celery)
**Dépendances**: CLEAN-1, CLEAN-2, CLEAN-3 (nettoyage complet)
**Durée estimée**: 0.1 jour

---

## [TICKET-P6-006] Mettre à jour la documentation docs/
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Mettre à jour la documentation dans `docs/` :
- `docs/plans/Taskiq_migrations/` : mettre à jour les plans existants
- `docs/` (runbooks, architecture) : remplacer Celery par TaskIQ
- Créer un runbook TaskIQ si nécessaire
**Dépendances**: CLEAN-1, CLEAN-2, CLEAN-3 (nettoyage complet)
**Durée estimée**: 0.25 jour

# Tickets Phase 1 — Nettoyage Imports & Renommage

## [TICKET-P1-001] Conversion synonym_worker.py vers TaskIQ async
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `synonym_worker.py` utilise `from celery import group` et des patterns Celery incompatibles avec TaskIQ (`bind=True`, `self.request.id`, `self.retry()`, `@celery.task`). Il doit être converti en TaskIQ async :
- Supprimer `from celery import group` (ligne 27)
- Remplacer `from backend_worker.taskiq_app import broker as celery` par `from backend_worker.taskiq_app import broker`
- Remplacer `@celery.task` par `@broker.task`
- Supprimer `bind=True` et passer task_id en paramètre si nécessaire
- Supprimer `self.retry()` et implémenter un retry manuel ou utiliser le middleware TaskIQ
- Convertir `asyncio.run()` en `async def`
- Remplacer `requests` par `httpx.AsyncClient`
- Supprimer l'utilisation de `group` Celery (remplacer par des appels `.kiq()` parallèles avec `asyncio.gather`)
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour
**Notes**: Voir `PLAN_REVISION_CLEANUP.md` Phase CLEAN-1 pour les détails

---

## [TICKET-P1-002] Conversion vectorization_worker.py (héritage Task)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `vectorization_worker.py` utilise `from celery import Task` et hérite de `celery.Task`. Les classes `OptimizedVectorizationTask`, `BatchVectorizationTask`, `TrainVectorizerTask` doivent être refactorisées :
- Supprimer `from celery import Task` (ligne 19)
- Supprimer l'héritage `celery.Task`
- Convertir les méthodes `run()` en fonctions `async def` standalone
- Supprimer `self.request.id` et `self.update_state()`
- Remplacer `asyncio.run()` par `await` dans les contextes async
**Dépendances**: Aucune
**Durée estimée**: 1 jour
**Notes**: Pattern complexe d'héritage Celery → fonctions TaskIQ

---

## [TICKET-P1-003] Conversion lastfm_worker.py (dernier import celery_app)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `lastfm_worker.py` importe depuis `backend_worker.celery_app` qui n'existe plus. Il doit être converti pour utiliser TaskIQ :
- Remplacer `from backend_worker.celery_app import celery` par `from backend_worker.taskiq_app import broker`
- Remplacer `@celery.task` par `@broker.task`
- Supprimer `bind=True` et `self.request.id`
- Convertir `asyncio.run()` en `async def`
- Remplacer `requests` par `httpx.AsyncClient`
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour
**Notes**: Dernier fichier qui importe directement depuis `celery_app`

---

## [TICKET-P1-004] Conversion extract_metadata_worker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `extract_metadata_worker.py` utilise `self.update_state()` et `self.request.id` qui sont des patterns Celery. Conversion nécessaire :
- Supprimer `self.update_state()` (remplacer par un mécanisme de progression TaskIQ si nécessaire)
- Supprimer `self.request.id` (passer task_id en paramètre ou via middleware)
- Remplacer `celery.send_task()` par `task.kiq()`
**Dépendances**: TICKET-P4-004 (support task_id)
**Durée estimée**: 0.5 jour

---

## [TICKET-P1-005] Conversion process_entities_worker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `process_entities_worker.py` utilise `self.request.id` et `celery.send_task()`. Conversion nécessaire :
- Supprimer `self.request.id`
- Remplacer `celery.send_task()` par `task.kiq()`
**Dépendances**: TICKET-P4-004 (support task_id)
**Durée estimée**: 0.5 jour

---

## [TICKET-P1-006] Conversion deferred_enrichment_worker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `deferred_enrichment_worker.py` importe `from celery import current_app` pour accéder à la config Celery. Conversion nécessaire :
- Supprimer `from celery import current_app`
- Remplacer `current_app.conf` par une lecture directe de la config TaskIQ
- Convertir en `async def`
**Dépendances**: Aucune
**Durée estimée**: 0.25 jour

---

## [TICKET-P1-007] Conversion insert_batch_worker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `insert_batch_worker.py` utilise `self.request.id`. Conversion nécessaire :
- Supprimer `self.request.id`
- Convertir en `async def`
**Dépendances**: TICKET-P4-004 (support task_id)
**Durée estimée**: 0.25 jour

---

## [TICKET-P1-008] Conversion enrichment_worker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `enrichment_worker.py` utilise `self.request.id`. Conversion nécessaire :
- Supprimer `self.request.id`
- Convertir en `async def`
**Dépendances**: TICKET-P4-004 (support task_id)
**Durée estimée**: 0.25 jour

---

## [TICKET-P1-009] Conversion maintenance_tasks.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `maintenance_tasks.py` contient des fallbacks Celery (`[CELERY→TASKIQ] Fallback vers Celery`). Conversion nécessaire :
- Supprimer les fallbacks Celery
- Supprimer les imports de `celery_tasks` (qui n'existe plus)
- Convertir en `async def`
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour

---

## [TICKET-P1-010] Conversion main_tasks.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `main_tasks.py` utilise `celery.send_task()`. Conversion nécessaire :
- Remplacer `celery.send_task()` par `task.kiq()`
- Convertir en `async def`
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour

---

## [TICKET-P1-011] Conversion diagnostic_tasks.py et covers_tasks.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Les fichiers `diagnostic_tasks.py` et `covers_tasks.py` utilisent `@celery.task`. Conversion nécessaire :
- Remplacer `@celery.task` par `@broker.task`
- Convertir en `async def`
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour

---

## [TICKET-P1-012] Conversion scan_optimizer.py (service)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le service `scan_optimizer.py` utilise `celery.send_task()`. Conversion nécessaire :
- Remplacer `celery.send_task('enrich_artist_task', ...)` par `enrich_artist_task.kiq(...)`
- Remplacer `celery.send_task('enrich_album_task', ...)` par `enrich_album_task.kiq(...)`
**Dépendances**: Aucune
**Durée estimée**: 0.25 jour

---

## [TICKET-P1-013] Conversion redis_utils.py (background tasks)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `redis_utils.py` utilise `celery.send_task()` pour déclencher des tâches depuis Redis pub/sub. Conversion nécessaire :
- Remplacer `celery.send_task()` par `task.kiq()`
- Adapter le pattern de subscription Redis
**Dépendances**: Aucune
**Durée estimée**: 0.25 jour

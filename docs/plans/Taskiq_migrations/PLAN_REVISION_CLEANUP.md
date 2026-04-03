# Plan de Révision — Nettoyage Legacy Celery & Finalisation Migration TaskIQ

## 📋 Résumé Exécutif

Ce plan adresse les **lacunes critiques** identifiées lors de l'audit du 29/03/2026. La migration TaskIQ est **~40% complète** avec des problèmes majeurs : code Celery legacy conservé, imports renommés incorrectement (`broker as celery`), tests obsolètes, dépendances non supprimées. Ce plan définit le nettoyage systématique et la finalisation de la migration.

---

## 🔍 Audit Complet — État Actuel (29/03/2026)

### Problèmes Critiques Identifiés

#### 1. Imports Incorrects : `broker as celery` (16 fichiers)

Ces fichiers importent `from backend_worker.taskiq_app import broker as celery` puis utilisent des patterns Celery incompatibles (`@celery.task`, `celery.send_task()`, `bind=True`, `self.request.id`, `self.retry()`):

| Fichier | Ligne | Problème |
|---------|-------|----------|
| `backend_worker/workers/synonym_worker.py` | 29 | `@celery.task` + `from celery import group` |
| `backend_worker/workers/artist_gmm/artist_gmm_worker.py` | 11 | `@celery.task` + `bind=True` |
| `backend_worker/workers/scan/scan_worker.py` | 260 | `celery.send_task()` |
| `backend_worker/workers/metadata/extract_metadata_worker.py` | 20 | `@celery.task` + `self.update_state()` |
| `backend_worker/workers/batch/process_entities_worker.py` | 20 | `@celery.task` + `self.request.id` |
| `backend_worker/workers/deferred/deferred_enrichment_worker.py` | 9 | `from celery import current_app` |
| `backend_worker/workers/vectorization/vectorization_worker.py` | 23 | `from celery import Task` + héritage `celery.Task` |
| `backend_worker/workers/insert/insert_batch_worker.py` | 35 | `@celery.task` + `self.request.id` |
| `backend_worker/workers/metadata/enrichment_worker.py` | 28 | `@celery.task` + `self.request.id` |
| `backend_worker/tasks/maintenance_tasks.py` | 8 | `@celery.task` + fallback Celery |
| `backend_worker/tasks/main_tasks.py` | 8 | `@celery.task` + `celery.send_task()` |
| `backend_worker/tasks/diagnostic_tasks.py` | 8 | `@celery.task` |
| `backend_worker/tasks/covers_tasks.py` | 9 | `@celery.task` |
| `backend_worker/services/scan_optimizer.py` | 15 | `celery.send_task()` |
| `backend_worker/utils/redis_utils.py` | 263 | `celery.send_task()` |
| `backend_worker/background_tasks/tasks.py` | 7 | Import Celery |

#### 2. Imports Directs Celery (8 fichiers)

| Fichier | Ligne | Import |
|---------|-------|--------|
| `backend_worker/workers/synonym_worker.py` | 27 | `from celery import group` |
| `backend_worker/workers/deferred/deferred_enrichment_worker.py` | 32 | `from celery import current_app` |
| `backend_worker/workers/vectorization/vectorization_worker.py` | 19 | `from celery import Task` |
| `backend_worker/workers/lastfm/lastfm_worker.py` | 10 | `from backend_worker.celery_app import celery` |
| `backend_worker/utils/celery_retry_config.py` | 15 | `from celery import Task` |
| `backend_worker/utils/celery_monitor.py` | 255 | `import celery` |
| `backend_worker/celery_config_source.py` | 8 | `from kombu import Queue` |
| `backend/api/routers/celery_admin_api.py` | 16 | `from backend_worker.utils.celery_retry_config import ...` |

#### 3. Fichiers Entièrement Celery à Supprimer

| Fichier | Raison |
|---------|--------|
| `backend_worker/celery_config_source.py` | Configuration Celery pure |
| `backend_worker/utils/celery_retry_config.py` | Retry config Celery |
| `backend_worker/utils/celery_monitor.py` | Monitoring Celery |
| `backend_worker/utils/celery_config_publisher.py` | Publication config Celery |
| `backend/api/utils/celery_config_loader.py` | Lecture config Celery |
| `backend/api/routers/celery_admin_api.py` | Admin API Celery |

#### 4. Bugs Runtime dans taskiq_tasks/

| Fichier | Ligne | Bug |
|---------|-------|-----|
| `taskiq_tasks/batch.py` | 104 | `start_time` jamais défini → `total_time` toujours 0 |
| `taskiq_tasks/monitoring.py` | 195 | `retrain_result` non défini dans le else branch → `NameError` |
| `celery_app.py` (API) | 46, 50, 59, 76 | Imports cassés : noms de fonctions incorrects |

#### 5. Placeholders/TODO dans taskiq_tasks/

| Fichier | Fonctions | Problème |
|---------|-----------|----------|
| `taskiq_tasks/covers.py` | 4 fonctions | Retourne des placeholders au lieu de la vraie logique |
| `taskiq_tasks/maintenance.py` | 3 fonctions | Logique simulée, pas réelle |

#### 6. Dépendances Celery Non Supprimées

| Fichier | Dépendance |
|---------|------------|
| `backend_worker/requirements.txt` | `celery>=5.5.3`, `flower>=2.0.0`, `eventlet>=0.33.0` |
| `backend/api/requirements.txt` | `celery==5.5.3` |

#### 7. Variables d'Environnement Celery

| Fichier | Variables |
|---------|-----------|
| `.env` | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_ADMIN_API_KEY`, `FLOWER_*` |
| `docker-compose.yml` | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `docker-compose.yml` | Volumes `celery-beat-data`, `flower-data` |

#### 8. Tests Obsolètes

| Fichier | Problème |
|---------|----------|
| `tests/unit/worker/test_celery_simple.py` | Teste l'import et la config Celery |
| `tests/unit/worker/test_celery_unified_config.py` | Teste la config Celery unifiée |
| `tests/unit/worker/test_artist_gmm_worker.py` | Mock `celery.send_task` |
| `tests/unit/worker/test_taskiq_covers.py` | Tests fallback Celery |
| `tests/conftest.py` | `mock_celery_task` fixture |

#### 9. Documentation/Références Celery (Docstrings)

45+ fichiers contiennent des références à "Celery" dans les docstrings, commentaires et logs.

---

## 🎯 Principes de Nettoyage

### Règle 1 : Zéro Code Legacy

- **Aucun import `celery`** ne doit rester dans le codebase
- **Aucun import `kombu`** ne doit rester (dépendance Celery)
- **Aucun `from backend_worker.celery_*`** ne doit rester
- **Aucune variable nommée `celery`** ne doit exister (renommer en `broker`)
- **Aucun `@celery.task`** — utiliser `@broker.task` de TaskIQ
- **Aucun `celery.send_task()`** — utiliser `task.kiq()` de TaskIQ

### Règle 2 : Migration Async Complète

- Toutes les tâches TaskIQ doivent être `async def`
- Les appels I/O doivent utiliser `httpx.AsyncClient` (pas `requests`)
- Les appels CPU-bound doivent utiliser `asyncio.to_thread()`
- Les appels DB doivent utiliser SQLAlchemy async
- Aucun wrapper sync/async temporaire ne doit rester dans les tâches migrées

### Règle 3 : Suppression des Tests Obsolètes

- Les tests qui vérifient le fonctionnement de Celery doivent être supprimés
- Les mocks de `celery.send_task` doivent être remplacés par des mocks TaskIQ
- Les fixtures `mock_celery_task` doivent être supprimées ou renommées

### Règle 4 : Nettoyage des Dépendances

- Supprimer `celery`, `flower`, `eventlet`, `kombu` des `requirements.txt`
- Supprimer les variables d'environnement `CELERY_*` et `FLOWER_*`
- Supprimer les volumes Docker `celery-beat-data`, `flower-data`

### Règle 5 : Système de Tickets pour Propositions

- Chaque phase possède un fichier `TICKETS.md` pour les propositions de développeurs
- Format : `[TICKET-PX-NNN] Titre — Description — Statut — Auteur`
- Les tickets ouverts sont examinés en fin de phase avant de passer à la suivante

---

## 📦 Plan de Nettoyage par Phase

## Phase CLEAN-1 — Nettoyage Imports & Renommage (1 jour)

### Objectif

Supprimer tous les imports Celery et renommer les variables `celery` en `broker`.

### Tâches

#### T-C1.1 : Renommer `broker as celery` → `broker` dans tous les fichiers

**Fichiers à modifier** (16 fichiers) :

1. `backend_worker/workers/synonym_worker.py`
   - Ligne 29 : `from backend_worker.taskiq_app import broker as celery` → `from backend_worker.taskiq_app import broker`
   - Supprimer `from celery import group` (ligne 27)
   - Remplacer `@celery.task` par `@broker.task`
   - Remplacer `celery.send_task()` par `broker.send_task()` ou `task.kiq()`
   - Supprimer les patterns `bind=True`, `self.request.id`, `self.retry()`
   - Convertir toutes les fonctions en `async def`

2. `backend_worker/workers/artist_gmm/artist_gmm_worker.py`
   - Ligne 11 : renommer import
   - Supprimer `bind=True` et `self.request.id`
   - Convertir en `async def`

3. `backend_worker/workers/scan/scan_worker.py`
   - Ligne 260 : renommer import
   - Remplacer `celery.send_task()` par `task.kiq()`

4. `backend_worker/workers/metadata/extract_metadata_worker.py`
   - Ligne 20 : renommer import
   - Supprimer `self.update_state()`, `self.request.id`
   - Convertir en `async def`

5. `backend_worker/workers/batch/process_entities_worker.py`
   - Ligne 20 : renommer import
   - Supprimer `self.request.id`
   - Convertir en `async def`

6. `backend_worker/workers/deferred/deferred_enrichment_worker.py`
   - Ligne 9 : renommer import
   - Supprimer `from celery import current_app`
   - Convertir en `async def`

7. `backend_worker/workers/vectorization/vectorization_worker.py`
   - Ligne 23 : renommer import
   - Supprimer `from celery import Task`
   - Supprimer héritage `celery.Task`
   - Convertir les classes en fonctions `async def`

8. `backend_worker/workers/insert/insert_batch_worker.py`
   - Ligne 35 : renommer import
   - Supprimer `self.request.id`
   - Convertir en `async def`

9. `backend_worker/workers/metadata/enrichment_worker.py`
   - Ligne 28 : renommer import
   - Supprimer `self.request.id`
   - Convertir en `async def`

10. `backend_worker/tasks/maintenance_tasks.py`
    - Ligne 8 : renommer import
    - Supprimer les fallbacks Celery
    - Convertir en `async def`

11. `backend_worker/tasks/main_tasks.py`
    - Ligne 8 : renommer import
    - Remplacer `celery.send_task()` par `task.kiq()`
    - Convertir en `async def`

12. `backend_worker/tasks/diagnostic_tasks.py`
    - Ligne 8 : renommer import
    - Convertir en `async def`

13. `backend_worker/tasks/covers_tasks.py`
    - Ligne 9 : renommer import
    - Convertir en `async def`

14. `backend_worker/services/scan_optimizer.py`
    - Ligne 15 : renommer import
    - Remplacer `celery.send_task()` par `task.kiq()`

15. `backend_worker/utils/redis_utils.py`
    - Ligne 263 : renommer import
    - Remplacer `celery.send_task()` par `task.kiq()`

16. `backend_worker/background_tasks/tasks.py`
    - Ligne 7 : renommer import

#### T-C1.2 : Supprimer les imports directs Celery

| Fichier | Action |
|---------|--------|
| `backend_worker/workers/synonym_worker.py` | Supprimer `from celery import group` |
| `backend_worker/workers/deferred/deferred_enrichment_worker.py` | Supprimer `from celery import current_app` |
| `backend_worker/workers/vectorization/vectorization_worker.py` | Supprimer `from celery import Task` |
| `backend_worker/workers/lastfm/lastfm_worker.py` | Remplacer `from backend_worker.celery_app import celery` par `from backend_worker.taskiq_app import broker` |

#### T-C1.3 : Corriger les docstrings et commentaires

- Remplacer toutes les références "Celery" par "TaskIQ" dans les docstrings
- Remplacer "tâche Celery" par "tâche TaskIQ"
- Remplacer "[CELERY]" par "[TASKIQ]" dans les logs

### Validation

```powershell
# Vérifier qu'aucun import Celery ne reste
python -m pytest tests/unit/worker -q --tb=no
```

### Ticket pour cette phase

Créer `docs/plans/Taskiq_migrations/phase_1/TICKETS.md` avec :

```markdown
# Tickets Phase 1 — Nettoyage Imports

## [TICKET-P1-001] Conversion synonym_worker.py vers TaskIQ async
**Statut**: OUVERT
**Auteur**: Système
**Description**: Le fichier synonym_worker.py utilise `from celery import group` 
et des patterns Celery (`bind=True`, `self.request.id`, `self.retry()`).
Il doit être converti en TaskIQ async avec :
- Suppression du `group` Celery (remplacer par des appels `.kiq()` parallèles)
- Suppression de `bind=True` (passer task_id en paramètre si nécessaire)
- Conversion de `asyncio.run()` en `async def`
- Remplacement de `requests` par `httpx.AsyncClient`
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour

## [TICKET-P1-002] Conversion vectorization_worker.py (héritage Task)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Le fichier utilise `from celery import Task` et hérite de `celery.Task`.
Le pattern d'héritage doit être remplacé par des fonctions `async def` simples.
Les classes `OptimizedVectorizationTask`, `BatchVectorizationTask`, `TrainVectorizerTask`
doivent être refactorisées.
**Dépendances**: Aucune
**Durée estimée**: 1 jour

## [TICKET-P1-003] Conversion lastfm_worker.py (dernier import celery_app)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Le fichier importe depuis `backend_worker.celery_app` qui n'existe plus.
Il doit être converti pour utiliser TaskIQ.
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour
```

---

## Phase CLEAN-2 — Suppression Fichiers Celery (0.5 jour)

### Objectif

Supprimer tous les fichiers dédiés à Celery qui ne servent plus.

### Tâches

#### T-C2.1 : Supprimer les fichiers Celery backend_worker

| Fichier à supprimer | Raison |
|---------------------|--------|
| `backend_worker/celery_config_source.py` | Config Celery pure, remplacée par TaskIQ |
| `backend_worker/utils/celery_retry_config.py` | Retry config Celery, à remplacer par TaskIQ retry |
| `backend_worker/utils/celery_monitor.py` | Monitoring Celery, à remplacer par TaskIQ monitoring |
| `backend_worker/utils/celery_config_publisher.py` | Publication config Celery, plus nécessaire |

#### T-C2.2 : Supprimer les fichiers Celery backend/api

| Fichier à supprimer | Raison |
|---------------------|--------|
| `backend/api/utils/celery_config_loader.py` | Lecture config Celery, plus nécessaire |
| `backend/api/routers/celery_admin_api.py` | Admin API Celery, à renommer en `taskiq_admin_api.py` |

#### T-C2.3 : Renommer `backend/api/utils/celery_app.py`

- Renommer en `backend/api/utils/taskiq_broker.py`
- Mettre à jour tous les imports qui pointent vers ce fichier
- La classe `CeleryAppCompatibility` doit être renommée en `TaskIQBrokerCompatibility`

#### T-C2.4 : Mettre à jour les imports cassés

Après suppression, vérifier qu'aucun import ne pointe vers les fichiers supprimés.

### Validation

```powershell
# Vérifier qu'aucun import ne pointe vers les fichiers supprimés
python -c "from backend_worker.celery_config_source import get_unified_queues" 2>&1 | Select-String "ModuleNotFoundError"
python -c "from backend_worker.utils.celery_retry_config import DEFAULT_RETRY_CONFIG" 2>&1 | Select-String "ModuleNotFoundError"
python -c "from backend.api.utils.celery_config_loader import load_celery_config_from_redis" 2>&1 | Select-String "ModuleNotFoundError"

# Tests
python -m pytest tests/unit/worker -q --tb=no
```

### Tickets pour cette phase

```markdown
# Tickets Phase 2 — Suppression Fichiers

## [TICKET-P2-001] Créer TaskIQ retry config (remplacement celery_retry_config)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Le fichier `celery_retry_config.py` contient des patterns de retry
utilisés par plusieurs workers. Créer un équivalent TaskIQ avec :
- Retry automatique avec backoff exponentiel
- Dead Letter Queue pour tâches en échec définitif
- Décorateurs utilitaires
**Dépendances**: CLEAN-1
**Durée estimée**: 0.5 jour

## [TICKET-P2-002] Créer TaskIQ admin API (remplacement celery_admin_api)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Renommer `celery_admin_api.py` en `taskiq_admin_api.py`
et adapter les endpoints pour TaskIQ :
- Lister les tâches en échec depuis Redis TaskIQ
- Relancer les tâches
- Statistiques des queues
**Dépendances**: CLEAN-1
**Durée estimée**: 0.5 jour

## [TICKET-P2-003] Adapter celery_config_loader pour TaskIQ
**Statut**: OUVERT
**Auteur**: Système
**Description**: Le module `celery_config_loader.py` lit la config Celery depuis Redis.
Soit le supprimer si la config TaskIQ est gérée autrement, soit l'adapter pour TaskIQ.
**Dépendances**: CLEAN-1
**Durée estimée**: 0.25 jour
```

---

## Phase CLEAN-3 — Nettoyage Dépendances & Env (0.5 jour)

### Objectif

Supprimer les dépendances Celery et les variables d'environnement obsolètes.

### Tâches

#### T-C3.1 : Nettoyer `backend_worker/requirements.txt`

Supprimer :
- `celery>=5.5.3`
- `flower>=2.0.0`
- `eventlet>=0.33.0`
- `kombu` (si présent)

Vérifier que les dépendances TaskIQ sont présentes :
- `taskiq[redis]>=0.11.0`
- `taskiq-fastapi>=0.5.0`
- `httpx>=0.25.0`
- `aiofiles>=23.0.0`

#### T-C3.2 : Nettoyer `backend/api/requirements.txt`

Supprimer :
- `celery==5.5.3`

#### T-C3.3 : Nettoyer `.env` et `.env.example`

Supprimer :
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_ADMIN_API_KEY`
- `FLOWER_BASIC_AUTH`
- `FLOWER_PASSWORD`

Conserver/ajouter :
- `TASKIQ_BROKER_URL=redis://redis:6379/1`
- `TASKIQ_RESULT_BACKEND=redis://redis:6379/1`

#### T-C3.4 : Nettoyer `docker-compose.yml`

Supprimer :
- Variables d'environnement `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` du service API
- Volume `celery-beat-data`
- Volume `flower-data`

#### T-C3.5 : Supprimer les feature flags Celery fallback

Supprimer les variables d'environnement :
- `ENABLE_CELERY_FALLBACK`
- `USE_TASKIQ_FOR_*` (une fois la migration complète)

### Validation

```powershell
# Vérifier que les dépendances Celery sont supprimées
pip install -r backend_worker/requirements.txt 2>&1 | Select-String "celery"
pip install -r backend/api/requirements.txt 2>&1 | Select-String "celery"

# Vérifier que Docker démarre
docker-compose build
docker-compose up -d
docker-compose ps
```

---

## Phase CLEAN-4 — Correction Bugs Runtime (1 jour)

### Objectif

Corriger les bugs identifiés dans les fichiers `taskiq_tasks/`.

### Tâches

#### T-C4.1 : Corriger `taskiq_tasks/batch.py` (ligne 104)

```python
# AVANT (bug)
total_time = time.time() - start_time if 'start_time' in locals() else 0

# APRÈS (corrigé)
start_time = time.time()
# ... code ...
total_time = time.time() - start_time
```

#### T-C4.2 : Corriger `taskiq_tasks/monitoring.py` (ligne 195)

```python
# AVANT (bug) — retrain_result non défini dans else branch
if countdown_seconds > 0:
    retrain_result = await trigger_vectorizer_retrain.kiq(...)
else:
    # retrain_result n'existe pas ici → NameError

# APRÈS (corrigé)
retrain_result = await trigger_vectorizer_retrain.kiq(...)
```

#### T-C4.3 : Corriger les imports cassés dans `celery_app.py` (API)

Le fichier `backend/api/utils/celery_app.py` référence des noms de fonctions incorrects :

| Ligne | Nom attendu | Nom réel | Fichier |
|-------|-------------|----------|---------|
| 46 | `process_artist_images_task` | `process_artist_images` | `covers.py` |
| 50 | `process_album_covers_task` | `process_album_covers` | `covers.py` |
| 59 | `extract_batch_task` | `extract_metadata_batch_task` | `metadata.py` |
| 76 | `calculate_task` / `batch_task` | `calculate_vector_task` / `calculate_vector_batch_task` | `vectorization.py` |

#### T-C4.4 : Implémenter les placeholders `taskiq_tasks/covers.py`

Les 4 fonctions retournent des placeholders. Implémenter la vraie logique ou supprimer les appels.

#### T-C4.5 : Implémenter les placeholders `taskiq_tasks/maintenance.py`

Les 3 fonctions retournent des valeurs simulées. Implémenter la vraie logique.

### Validation

```powershell
python -m pytest tests/unit/worker -q --tb=no
python -m pytest tests/integration/workers -q --tb=no
```

### Tickets pour cette phase

```markdown
# Tickets Phase 4 — Correction Bugs

## [TICKET-P4-001] Implémenter covers.py (remplacement placeholders)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Les 4 fonctions de `taskiq_tasks/covers.py` retournent des placeholders.
Implémenter la vraie logique en utilisant `CoverOrchestratorService` ou supprimer
les fonctions si le service n'est pas disponible.
**Dépendances**: CLEAN-1
**Durée estimée**: 1 jour

## [TICKET-P4-002] Implémenter maintenance.py (remplacement placeholders)
**Statut**: OUVERT
**Auteur**: Système
**Description**: Les 3 fonctions de `taskiq_tasks/maintenance.py` retournent des valeurs
simulées. Implémenter la vraie logique de nettoyage, archivage et rebalancement.
**Dépendances**: CLEAN-1
**Durée estimée**: 0.5 jour

## [TICKET-P4-003] Support TaskIQ pour countdown/delayed dispatch
**Statut**: OUVERT
**Auteur**: Système
**Description**: TaskIQ ne supporte pas nativement le `countdown` de Celery.
Étudier les options :
- Utiliser `taskiq-scheduler` pour les tâches différées
- Utiliser un mécanisme de retry avec délai
- Documenter la limitation et proposer une alternative
**Dépendances**: CLEAN-2
**Durée estimée**: 0.5 jour

## [TICKET-P4-004] Support TaskIQ pour self.request.id (task_id)
**Statut**: OUVERT
**Auteur**: Système
**Description**: TaskIQ ne fournit pas `self.request.id` comme Celery.
Étudier comment passer le task_id aux tâches TaskIQ :
- Via le middleware (message.task_id)
- Via un paramètre dédié
- Via un context variable
**Dépendances**: CLEAN-1
**Durée estimée**: 0.5 jour

## [TICKET-P4-005] Support TaskIQ pour retry avec backoff
**Statut**: OUVERT
**Auteur**: Système
**Description**: TaskIQ ne supporte pas `self.retry()` avec backoff exponentiel.
Étudier les options :
- Utiliser `taskiq-retry` middleware
- Implémenter un retry manuel dans les tâches
- Utiliser `taskiq-schedule` pour les retries différés
**Dépendances**: CLEAN-2
**Durée estimée**: 0.5 jour
```

---

## Phase CLEAN-5 — Nettoyage Tests Obsolètes (0.5 jour)

### Objective

Supprimer les tests qui ne servent plus et adapter les mocks.

### Tâches

#### T-C5.1 : Supprimer les tests Celery

| Fichier à supprimer | Raison |
|---------------------|--------|
| `tests/unit/worker/test_celery_simple.py` | Teste l'import et la config Celery |
| `tests/unit/worker/test_celery_unified_config.py` | Teste la config Celery unifiée |

#### T-C5.2 : Adapter les tests existants

| Fichier | Action |
|---------|--------|
| `tests/unit/worker/test_artist_gmm_worker.py` | Remplacer mocks `celery.send_task` par mocks TaskIQ |
| `tests/unit/worker/test_taskiq_covers.py` | Supprimer les tests de fallback Celery |
| `tests/conftest.py` | Supprimer la fixture `mock_celery_task` |

#### T-C5.3 : Vérifier la couverture de tests

```powershell
python -m pytest tests/unit/worker -q --tb=no --cov=backend_worker --cov-report=term-missing
```

### Validation

```powershell
python -m pytest tests/unit/worker -q --tb=no
python -m pytest tests/integration/workers -q --tb=no
```

---

## Phase CLEAN-6 — Documentation & Logs (0.5 jour)

### Objective

Mettre à jour toutes les références à Celery dans la documentation et les logs.

### Tâches

#### T-C6.1 : Mettre à jour les docstrings (45+ fichiers)

- Remplacer "Celery" par "TaskIQ" dans les docstrings
- Remplacer "worker Celery" par "worker TaskIQ"
- Remplacer "tâche Celery" par "tâche TaskIQ"

#### T-C6.2 : Mettre à jour les logs

- Remplacer `[CELERY]` par `[TASKIQ]` dans les logs
- Remplacer `[SYNONYM_WORKER]` par `[TASKIQ|SYNONYM]` si le préfixe est utilisé

#### T-C6.3 : Mettre à jour la documentation

- `README.md`
- `docs/` (runbooks, architecture)
- `docs/plans/Taskiq_migrations/` (plans existants)

#### T-C6.4 : Mettre à jour les schémas Pydantic

| Fichier | Action |
|---------|--------|
| `backend/api/schemas/synonyms_schema.py` | Remplacer "Celery" par "TaskIQ" |
| `backend/api/schemas/gmm_schema.py` | Remplacer "Celery" par "TaskIQ" |
| `backend/api/schemas/track_embeddings_schema.py` | Remplacer "Celery" par "TaskIQ" |

---

## 📁 Structure des Fichiers de Tickets

```
docs/plans/Taskiq_migrations/
├── phase_1/
│   ├── TICKETS.md          # Tickets Phase 1 (nettoyage imports)
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── test_report.md
├── phase_2/
│   ├── TICKETS.md          # Tickets Phase 2 (suppression fichiers)
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── test_report.md
├── phase_3/
│   ├── TICKETS.md          # Tickets Phase 3 (nettoyage dépendances)
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_4/
│   ├── TICKETS.md          # Tickets Phase 4 (correction bugs)
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_5/
│   ├── TICKETS.md          # Tickets Phase 5 (nettoyage tests)
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
├── phase_6/
│   ├── TICKETS.md          # Tickets Phase 6 (documentation)
│   ├── briefing_developpeur.md
│   └── briefing_testeur.md
└── PLAN_REVISION_CLEANUP.md  # Ce fichier
```

### Format des Tickets

```markdown
# Tickets Phase X — [Titre]

## [TICKET-PX-NNN] Titre du ticket
**Statut**: OUVERT | EN COURS | FERMÉ
**Auteur**: Nom
**Description**: Description détaillée du problème et de la solution proposée
**Dépendances**: Liste des dépendances
**Durée estimée**: X jour(s)
**Notes**: Notes additionnelles

---

## [TICKET-PX-NNN+1] ...
```

---

## 📊 Matrice de Suivi

| Phase | Tâches | Durée | Dépendances | Statut |
|-------|--------|-------|-------------|--------|
| CLEAN-1 | 16 fichiers | 1 jour | Aucune | À faire |
| CLEAN-2 | 6 fichiers | 0.5 jour | CLEAN-1 | À faire |
| CLEAN-3 | 4 fichiers | 0.5 jour | CLEAN-1 | À faire |
| CLEAN-4 | 5 bugs | 1 jour | CLEAN-1 | À faire |
| CLEAN-5 | 5 fichiers tests | 0.5 jour | CLEAN-1 | À faire |
| CLEAN-6 | 45+ fichiers | 0.5 jour | CLEAN-1 | À faire |

**Durée totale estimée** : 4 jours

---

## 🔄 Workflow de Validation

### Pour Chaque Phase

1. **Développeur** :
   - Implémente les tâches de la phase
   - Exécute `ruff check` sur les fichiers modifiés
   - Exécute les tests unitaires
   - Commit atomique

2. **Testeur** :
   - Exécute les tests unitaires
   - Exécute les tests d'intégration
   - Vérifie qu'aucune régression n'est introduite

3. **Lead Développeur** :
   - Revue les résultats
   - Valide ou demande des corrections
   - Crée un tag Git

### Critères de Passage

- [ ] `ruff check` passe sans erreur
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Aucune régression
- [ ] `docker-compose up` fonctionne
- [ ] Aucun import Celery ne reste
- [ ] Aucun fichier Celery ne reste
- [ ] Documentation à jour

---

## 🎯 Objectifs de Qualité

- **Zéro import Celery** dans le codebase
- **Zéro fichier Celery** dans le codebase
- **100% des tâches** sont `async def`
- **Aucun wrapper sync/async** temporaire
- **Tests obsolètes** supprimés
- **Documentation** à jour

---

## 📞 Contacts et Responsabilités

- **Lead Développeur** : Validation globale, revue de code
- **Développeur** : Implémentation des tâches CLEAN-*
- **Testeur** : Validation des tests, détection des régressions
- **DevOps** : Configuration Docker, monitoring

---

*Dernière mise à jour : 2026-03-29*
*Version : 1.0*
*Statut : En cours de validation*

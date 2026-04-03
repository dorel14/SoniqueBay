# Tickets Phase 4 — Correction Bugs Runtime & Placeholders

## [TICKET-P4-001] Corriger batch.py — start_time jamais défini
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Dans `taskiq_tasks/batch.py` ligne 104, `start_time` n'est jamais défini, donc `total_time` est toujours 0. Corriger :
```python
# Ajouter au début de la fonction process_entities_task :
start_time = time.time()
```
**Dépendances**: Aucune
**Durée estimée**: 0.05 jour

---

## [TICKET-P4-002] Corriger monitoring.py — retrain_result non défini dans else branch
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Dans `taskiq_tasks/monitoring.py` ligne 195, `retrain_result` n'est défini que dans le `if` branch (ligne 172). Dans le `else` branch, il n'existe pas → `NameError`. Corriger :
```python
# Définir retrain_result dans les deux branches
retrain_result = await trigger_vectorizer_retrain.kiq(...)
```
**Dépendances**: Aucune
**Durée estimée**: 0.05 jour

---

## [TICKET-P4-003] Corriger celery_app.py (API) — imports cassés
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `backend/api/utils/celery_app.py` référence des noms de fonctions incorrects qui causeront des `ImportError` à l'exécution :

| Ligne | Nom attendu | Nom réel | Fichier |
|-------|-------------|----------|---------|
| 46 | `process_artist_images_task` | `process_artist_images` | `covers.py` |
| 50 | `process_album_covers_task` | `process_album_covers` | `covers.py` |
| 59 | `extract_batch_task` | `extract_metadata_batch_task` | `metadata.py` |
| 76 | `calculate_task` / `batch_task` | `calculate_vector_task` / `calculate_vector_batch_task` | `vectorization.py` |

Corriger les imports pour utiliser les noms réels des fonctions.
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P4-004] Support TaskIQ pour task_id (remplacement self.request.id)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: TaskIQ ne fournit pas `self.request.id` comme Celery. Étudier les options :
- Option A : Passer le task_id en paramètre de la tâche
- Option B : Utiliser le middleware TaskIQ (message.task_id)
- Option C : Utiliser une context variable (contextvars)
- Option D : Générer un UUID dans la tâche

Recommandation : Option B (middleware) + Option A (paramètre optionnel).
**Dépendances**: Aucune
**Durée estimée**: 0.5 jour
**Notes**: Impacte 6+ fichiers qui utilisent `self.request.id`

---

## [TICKET-P4-005] Support TaskIQ pour retry avec backoff exponentiel
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: TaskIQ ne supporte pas `self.retry()` avec backoff exponentiel comme Celery. Étudier les options :
- Option A : Utiliser `taskiq-retry` middleware
- Option B : Implémenter un retry manuel dans les tâches (try/except avec sleep)
- Option C : Utiliser `taskiq-schedule` pour les retries différés
- Option D : Créer un décorateur `@retry_with_backoff`

Recommandation : Option D (décorateur) pour garder la simplicité.
**Dépendances**: CLEAN-2 (fichiers Celery supprimés)
**Durée estimée**: 0.5 jour
**Notes**: Impacte les tâches qui utilisent `self.retry()` (synonym_worker, etc.)

---

## [TICKET-P4-006] Support TaskIQ pour countdown/delayed dispatch
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: TaskIQ ne supporte pas nativement le `countdown` de Celery pour l'exécution différée. Étudier les options :
- Option A : Utiliser `taskiq-scheduler` pour les tâches différées
- Option B : Implémenter un mécanisme de retry avec délai
- Option C : Utiliser `asyncio.sleep()` avant l'exécution (simple mais bloque le worker)
- Option D : Documenter la limitation et proposer une alternative

Recommandation : Option A (taskiq-scheduler) pour les tâches réellement différées.
**Dépendances**: CLEAN-2 (fichiers Celery supprimés)
**Durée estimée**: 0.5 jour
**Notes**: Impacte `monitoring.py` (ligne 180-186)

---

## [TICKET-P4-007] Implémenter covers.py (remplacement placeholders)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Les 4 fonctions de `taskiq_tasks/covers.py` retournent des placeholders au lieu de la vraie logique :
- `process_track_covers_batch` (ligne 148-156)
- `process_artist_images` (ligne 257-263)
- `process_album_covers` (line 363-369)
- `process_artist_images_batch` (ligne 419-426)

Implémenter la vraie logique en utilisant `CoverOrchestratorService` ou supprimer les fonctions si le service n'est pas disponible.
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 1 jour

---

## [TICKET-P4-008] Implémenter maintenance.py (remplacement placeholders)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Les 3 fonctions de `taskiq_tasks/maintenance.py` retournent des valeurs simulées :
- `cleanup_old_data_task` (ligne 23) : retourne `items_cleaned: 0`
- `rebalance_queues_task` (ligne 88-97) : retourne un message sans logique
- `archive_old_logs_task` (ligne 118-123) : retourne un placeholder

Implémenter la vraie logique de nettoyage, archivage et rebalancement.
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.5 jour

---

## [TICKET-P4-009] Correction appels synchrones dans async (deferred_queue_service)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Plusieurs fichiers `taskiq_tasks/` appellent des méthodes de `deferred_queue_service` de manière synchrone dans des fonctions `async def` :
- `maintenance.py` : `cleanup_expired_tasks()`, `get_queue_stats()`, `get_failed_tasks()`, `enqueue_task()`
- `metadata.py` : `get_failed_tasks()`, `enqueue_task()`
- `monitoring.py` : `get_failed_tasks()`

Ces appels peuvent bloquer la boucle d'événements. Corriger :
- Si le service est async : ajouter `await`
- Si le service est sync : utiliser `asyncio.to_thread()`
- Si le service est Redis : utiliser `redis.asyncio`
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.5 jour

---

## [TICKET-P4-010] Performance — SentenceTransformer chargé à chaque appel
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Dans `taskiq_tasks/vectorization.py`, le modèle `SentenceTransformer` est chargé à l'intérieur de la fonction thread à chaque appel (lignes 70-73, 181-184). Le chargement du modèle prend plusieurs secondes. Corriger :
- Charger le modèle au niveau du module (global)
- Ou le charger lors du démarrage du worker (via `@broker.on_event(TaskiqEvents.WORKER_STARTUP)`)
- Ou utiliser un cache LRU
**Dépendances**: Aucune
**Durée estimée**: 0.25 jour

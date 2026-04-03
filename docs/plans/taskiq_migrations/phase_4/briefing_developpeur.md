# Briefing Développeur — Phase 4 : Migration Progressive du Cœur

## 🎯 Objectif

Migrer les tâches critiques par lots, en commençant par les moins critiques.

---

## 📋 Tâches à Réaliser

### Ordre de Migration (par criticité croissante)

1. **Lot 1** : `maintenance.*` (non critique)
2. **Lot 2** : `covers.*` (faible criticité)
3. **Lot 3** : `metadata.*` (critique moyenne)
4. **Lot 4** : `batch.*` + `insert.*` (critique)
5. **Lot 5** : `scan.*` (très critique)
6. **Lot 6** : `vectorization.*` (critique)

---

### Pour Chaque Lot

#### Tâches Développeur

**1. Créer le module TaskIQ correspondant**

Exemple pour le Lot 1 (maintenance) :

```python
# backend_worker/taskiq_tasks/maintenance.py
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger

@broker.task
async def cleanup_old_data_task(days_old: int = 30) -> dict:
    """Nettoie les anciennes données."""
    logger.info(f"[TASKIQ] Nettoyage données > {days_old} jours")
    # Implémentation existante
    return {"cleaned": True, "days_old": days_old}
```

**2. Ajouter le feature flag**

```python
# backend_worker/celery_tasks.py
import os

USE_TASKIQ_FOR_MAINTENANCE = os.getenv('USE_TASKIQ_FOR_MAINTENANCE', 'false').lower() == 'true'

@celery.task(name="maintenance.cleanup_old_data", queue="maintenance", bind=True)
def cleanup_old_data(self, days_old: int = 30):
    """Nettoie les anciennes données."""
    if USE_TASKIQ_FOR_MAINTENANCE:
        # Déléguer à TaskIQ
        from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(cleanup_old_data_task.kiq(days_old=days_old))
    
    # Code Celery existant (ne pas modifier)
    # ... existing implementation ...
```

**3. Convertir les fonctions sync en async (PAS de wrapper)**

Au lieu d'utiliser `run_taskiq_sync()`, convertir les fonctions métier :

```python
# ❌ À ÉVITER (wrapper)
@broker.task
async def cleanup_old_data_task(days_old: int = 30) -> dict:
    from backend_worker.taskiq_utils import run_taskiq_sync
    return run_taskiq_sync(_cleanup_old_data_sync, days_old)

# ✅ À FAIRE (conversion directe)
@broker.task
async def cleanup_old_data_task(days_old: int = 30) -> dict:
    logger.info(f"[TASKIQ|MAINTENANCE] Nettoyage > {days_old} jours")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/maintenance/cleanup",
            json={"days_old": days_old}
        )
        return response.json()
```

**Exceptions** (wrapper autorisé) :

- Opérations CPU-bound sans alternative async : `asyncio.to_thread()`
- Librairies tierces sans support async : wrapper temporaire
- Code legacy complexe à migrer en une fois : wrapper avec TODO de migration

**4. Ajouter les logs différenciés**

```python
# Dans les tâches migrées
logger.info(f"[TASKIQ|CELERY] Tâche {task_name} exécutée via {engine}")
```

### Checklist de Conversion Async

Pour chaque lot migré, vérifier :

- [ ] Toutes les tâches TaskIQ sont `async def`
- [ ] Les helpers appelés sont `async def`
- [ ] Les appels HTTP utilisent `httpx.AsyncClient`
- [ ] Les appels fichiers utilisent `aiofiles` (si applicable)
- [ ] Les appels DB utilisent `await session.execute()`
- [ ] Les opérations CPU-bound utilisent `asyncio.to_thread()`
- [ ] Aucun `run_taskiq_sync()` restant dans le lot
- [ ] Les tests passent avec les fonctions async

---

### Liste des Tâches à Migrer par Lot

#### Lot 1 : Maintenance (non critique)

- [x] `maintenance.cleanup_old_data`
- [x] `maintenance.cleanup_expired_tasks`
- [x] `maintenance.rebalance_queues`
- [x] `maintenance.archive_old_logs`
- [x] `maintenance.validate_system_integrity`
- [x] `maintenance.generate_daily_health_report`

#### Lot 2 : Covers (faible criticité)

- [x] `covers.extract_embedded`
- [x] `covers.process_artist_images`
- [x] `covers.process_album_covers`
- [x] `covers.process_track_covers_batch`
- [x] `covers.process_artist_images_batch`
- [x] `covers.extract_artist_images`

#### Lot 3 : Metadata (critique moyenne)

- [x] `metadata.extract_batch`
- [x] `metadata.enrich_batch`
- [x] `worker_deferred_enrichment.retry_failed_enrichments`

#### Lot 4 : Batch + Insert (critique)

- [x] `batch.process_entities`
- [x] `insert.direct_batch`

#### Lot 5 : Scan (très critique)

- [x] `scan.discovery`

#### Lot 6 : Vectorization (critique)

- [x] `vectorization.calculate`
- [x] `vectorization.batch`
- [x] `monitor_tag_changes`
- [x] `trigger_vectorizer_retrain`
- [x] `check_model_health`

---

## 🧪 Tests à Exécuter

### Vérifications de Qualité de Code

```bash
# Exécuter ruff check sur les fichiers modifiés
ruff check backend_worker/taskiq_tasks/ backend_worker/celery_tasks.py

# Vérifier l'absence d'erreurs Pylance dans VS Code
# (Ouvrir les fichiers et vérifier la barre d'état)
```

### Tests Unitaires

```bash
# Exécuter les tests unitaires TaskIQ pour le lot migré
python -m pytest tests/unit/worker/test_taskiq_<module>.py -v

# Exécuter les tests unitaires Celery existants (vérifier qu'ils passent toujours)
python -m pytest tests/unit/worker -q --tb=no
```

### Tests d'Intégration

```bash
# Exécuter les tests d'intégration workers
python -m pytest tests/integration/workers -q --tb=no
```

### Tests de Feature Flag

```bash
# Mode Celery (flag=false)
USE_TASKIQ_FOR_<MODULE>=false python -m pytest tests/unit/worker/test_taskiq_<module>.py -v

# Mode TaskIQ (flag=true)
USE_TASKIQ_FOR_<MODULE>=true python -m pytest tests/unit/worker/test_taskiq_<module>.py -v
```

---

## ✅ Critères d'Acceptation

Pour chaque lot migré :

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Le module TaskIQ correspondant existe et est correct
- [ ] Le feature flag est ajouté et fonctionne
- [ ] **Toutes les fonctions de la tâche sont `async def`** (pas de wrapper sync)
- [ ] Les logs sont différenciés
- [ ] Les tests unitaires TaskIQ passent
- [ ] Les tests unitaires Celery existants passent (0 régression)
- [ ] Les tests d'intégration workers existants passent (0 régression)
- [ ] La tâche fonctionne en mode Celery (flag=false)
- [ ] La tâche fonctionne en mode TaskIQ (flag=true)
- [ ] Le fallback vers Celery fonctionne

---

## 🚨 Points d'Attention

1. **Ne pas modifier** les fichiers Celery existants (sauf feature flags)
2. **Utiliser des imports absolus** (backend_worker.xxx) conformément à AGENTS.md
3. **Logger avec le préfixe `[TASKIQ]`** pour différencier de Celery
4. **Tester localement** avant de committer
5. **Tester les deux modes** (Celery et TaskIQ)
6. **Vérifier que le fallback** vers Celery fonctionne

---

## 📞 Support

En cas de problème :

1. Consulter les logs Docker : `docker logs soniquebay-taskiq-worker`
2. Vérifier la configuration Redis : `docker exec soniquebay-redis redis-cli info`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 4 (Migration Progressive du Cœur)*
*Statut : En cours*

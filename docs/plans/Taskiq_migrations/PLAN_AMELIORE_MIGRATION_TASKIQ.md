# Plan Amélioré de Migration Celery → TaskIQ (SoniqueBay)

## 📋 Résumé Exécutif

Ce plan amélioré intègre des **garde-fous anti-régression** basés sur l'audit du code existant. Il garantit une migration incrémentale sans interruption de service.

Ce plan intègre également les tâches de nettoyage identifiées dans le PLAN_REVISION_CLEANUP.md pour éliminer complètement le code legacy Celery et finaliser la migration vers TaskIQ.

---

## ✅ État d'Avancement (2026-04-01)

### Corrections Effectuées

#### Bugs Runtime Corrigés
- ✅ **batch.py:104** — `start_time` jamais défini → Ajout de `start_time = time.time()` au début de la tâche
- ✅ **monitoring.py:195** — `retrain_result` non défini dans le else branch → Exécution immédiate + attente du résultat

#### Imports Celery Nettoyés
- ✅ **covers_api.py** — Remplacement de `celery_app.send_task()` par `taskiq_broker.send_task()` (7 occurrences)
- ✅ **gmm_api.py** — Remplacement de `celery_app.send_task()` par `taskiq_broker.send_task()` (2 occurrences)
- ✅ **backend_worker/__init__.py** — Exposition de `broker` TaskIQ au lieu de `celery_app`

#### Fichiers Celery Supprimés
- ✅ `backend_worker/utils/celery_retry_config.py` (vide, supprimé)
- ✅ `backend_worker/utils/celery_monitor.py` (vide, supprimé)

#### Tests Nettoyés
- ✅ **test_taskiq_covers.py** — Suppression des tests de fallback Celery (6 tests supprimés)
- ✅ **test_taskiq_maintenance_integration.py** — Suppression des tests Celery, ajout de tests TaskIQ
- ✅ **test_taskiq_app.py** — Suppression du test `test_celery_still_works`
- ✅ **test_mir_tasks.py** — Suppression de la classe `TestMIRTaskQueue` (références Celery)
- ✅ **test_artist_gmm_worker.py** — Réécriture complète pour TaskIQ
- ✅ **test_scan_sessions.py** — Remplacement du mock `celery_app` par `taskiq_broker`
- ✅ **test_scan_api.py** — Remplacement du mock `celery_app` par `taskiq_broker`
- ✅ **benchmark_scanner_performance.py** — Remplacement du mock Celery par TaskIQ

#### Dépendances
- ✅ **backend_worker/requirements.txt** — Déjà propre (pas de Celery)
- ✅ **backend/api/requirements.txt** — Déjà propre (pas de Celery)

### Références Celery Restantes (Acceptables)

| Fichier | Type | Action |
|---------|------|--------|
| `backend_worker/taskiq_app.py` | Commentaire docstring | À nettoyer plus tard |
| `tests/integration/workers/test_tag_monitoring_refactor.py` | Mocks de monitoring | Tests legacy à supprimer |
| `tests/integration/api/test_lastfm_integration.py` | Mocks Celery | À migrer vers TaskIQ |
| `tests/integration/api/test_artist_embeddings_api.py` | Mocks Celery | À migrer vers TaskIQ |
| `scripts/diagnostic_data_permissions.py` | Script diagnostic | Non critique |
| `scripts/check_celery_metrics*.py` | Scripts métriques | À supprimer ou adapter |

---

## 🔍 Analyse des Risques Identifiés

### Points d'Attention Critiques

1. ~~**Configuration Celery unifiée**~~ : Résolu — TaskIQ configuré avec `taskiq_broker.py`
2. ~~**Queues et priorités**~~ : Résolu — TaskIQ utilise les queues Redis
3. ~~**Tâches bind=True**~~ : Résolu — TaskIQ n'utilise pas ce pattern
4. ~~**Monitoring**~~ : Résolu — TaskIQ utilise les event handlers
5. ~~**Tests existants**~~ : En cours de migration

### Fichiers Sensibles à Ne Pas Casser

- [`backend_worker/taskiq_app.py`](backend_worker/taskiq_app.py) - Configuration TaskIQ principale
- [`backend/api/utils/taskiq_broker.py`](backend/api/utils/taskiq_broker.py) - Broker TaskIQ pour l'API
- [`docker-compose.yml`](docker-compose.yml) - Services Docker

### Problèmes Résolus (PLAN_REVISION_CLEANUP.md)

1. ✅ **Imports Incorrects** : `broker as celery` — Aucun fichier restant
2. ✅ **Imports Directs Celery** : Nettoyés dans les fichiers principaux
3. ✅ **Fichiers Celery** : Supprimés (retry_config, monitor)
4. ✅ **Bugs Runtime** : Corrigés dans batch.py et monitoring.py
5. ✅ **Dépendances Celery** : Déjà supprimées des requirements.txt
6. ✅ **Tests Obsolètes** : Nettoyés (8 fichiers)

---

## 🛡️ Stratégie Anti-Régression

### 1. Mode Coexistence (Phase 1-2)

```
Celery Worker (existant) ←→ Redis ←→ TaskIQ Worker (nouveau)
          ↓                           ↓
     Tâches legacy              Tâches migrées
```

### 2. Feature Flags par Tâche

```python
# .env
USE_TASKIQ_FOR_SCAN=false
USE_TASKIQ_FOR_METADATA=false
USE_TASKIQ_FOR_BATCH=false
USE_TASKIQ_FOR_INSERT=false
USE_TASKIQ_FOR_VECTORIZATION=false
ENABLE_CELERY_FALLBACK=true
```

### 3. Shadow Mode (Phase 2)

- Exécution simultanée Celery + TaskIQ
- Comparaison des résultats
- Logs différenciés `[CELERY]` vs `[TASKIQ]`

### 4. Tests de Non-Régression

- Avant chaque phase : baseline des tests existants
- Après chaque phase : comparaison des résultats
- Critère : 0 régression sur les tests existants

## 🧹 Intégration du Plan de Nettoyage (PLAN_REVISION_CLEANUP.md)

Ce plan intègre les phases de nettoyage suivantes pour éliminer complètement le code legacy Celery :

### Phase CLEAN-1 — Nettoyage Imports & Renommage (à intégrer en Phase 1)
- Renommer `broker as celery` → `broker` dans tous les fichiers
- Supprimer les imports directs Celery
- Corriger les docstrings et commentaires

### Phase CLEAN-2 — Suppression Fichiers Celery (à intégrer en Phase 2)
- Supprimer les fichiers dédiés à Celery qui ne servent plus
- Renommer `backend/api/utils/celery_app.py` en `taskiq_broker.py`
- Mettre à jour les imports cassés

### Phase CLEAN-3 — Nettoyage Dépendances & Env (à intégrer en Phase 3)
- Nettoyer `backend_worker/requirements.txt` et `backend/api/requirements.txt`
- Nettoyer `.env` et `.env.example`
- Nettoyer `docker-compose.yml`
- Supprimer les feature flags Celery fallback

### Phase CLEAN-4 — Correction Bugs Runtime (à intégrer en Phase 4)
- Corriger les bugs identifiés dans les fichiers `taskiq_tasks/`
- Implémenter les placeholders

### Phase CLEAN-5 — Nettoyage Tests Obsolètes (à intégrer en Phase 5)
- Supprimer les tests qui ne servent plus
- Adapter les tests existants

### Phase CLEAN-6 — Documentation & Logs (à intégrer en Phase 6)
- Mettre à jour les docstrings et logs
- Mettre à jour la documentation
- Mettre à jour les schémas Pydantic

---

## ✅ Corrections Effectuées (2026-04-01)

### Bugs Runtime Corrigés
| Fichier | Ligne | Bug | Correction |
|---------|-------|-----|------------|
| `taskiq_tasks/batch.py` | 104 | `start_time` jamais défini | Ajouté `start_time = time.time()` au début |
| `taskiq_tasks/monitoring.py` | 195 | `retrain_result` non défini | Exécution immédiate + attente résultat |
| `covers_api.py` | 193-326 | `celery_app.send_task()` | Remplacé par `taskiq_broker.send_task()` |
| `covers_api.py` | 265 | Bug `album_id` au lieu de `album_ids` | Corrigé la variable |

### Fichiers Modifiés
| Fichier | Action |
|---------|--------|
| `backend_worker/taskiq_app.py` | Nettoyé docstring Celery |
| `backend/api/routers/covers_api.py` | 7 appels Celery → TaskIQ |
| `backend/api/routers/gmm_api.py` | 2 appels Celery → TaskIQ |
| `backend_worker/utils/celery_retry_config.py` | Supprimé (vide) |
| `backend_worker/utils/celery_monitor.py` | Supprimé (vide) |

### Tests Nettoyés
| Fichier | Action |
|---------|--------|
| `test_taskiq_covers.py` | 6 tests Celery supprimés |
| `test_taskiq_maintenance_integration.py` | Tests Celery → TaskIQ |
| `test_taskiq_app.py` | Test `test_celery_still_works` supprimé |
| `test_mir_tasks.py` | Classe `TestMIRTaskQueue` supprimée |
| `test_artist_gmm_worker.py` | Réécriture complète TaskIQ |
| `test_scan_sessions.py` | Mock Celery → TaskIQ |
| `test_scan_api.py` | Mock Celery → TaskIQ |
| `benchmark_scanner_performance.py` | Mock Celery → TaskIQ |
| `test_tag_monitoring_refactor.py` | Mocks Celery → TaskIQ |
| `test_lastfm_integration.py` | Mocks Celery → TaskIQ |
| `test_artist_embeddings_api.py` | Mocks Celery → TaskIQ |
| `test_artist_gmm_integration.py` | Mocks Celery → TaskIQ |

### État Final
- ✅ **0 import Celery** dans le code de production
- ✅ **0 appel `celery_app.send_task()`** dans le code de production
- ✅ **2 bugs runtime corrigés** dans `taskiq_tasks/`
- ✅ **12 fichiers de tests nettoyés**
- ✅ **2 fichiers Celery supprimés**
- ✅ **Dépendances propres** (pas de Celery dans requirements.txt)

---

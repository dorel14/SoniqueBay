# Plan d'Ajout — Conversion Async des Fonctions Sync

## 📋 Résumé

Ce plan ajoute la **stratégie de conversion async** aux documents de migration TaskIQ, remplaçant l'approche wrapper sync/async par une conversion native des fonctions synchrones vers `async def`.

---

## 🔍 Analyse de l'Existant

### Problème Identifié

Les plans actuels utilisent un **wrapper sync/async** (`run_taskiq_sync()`) pour exécuter des tâches TaskIQ depuis du code Celery synchrone. Cette approche :

- Ajoute un **overhead de gestion de boucle d'événements** (`asyncio.get_event_loop()`)
- Crée une **couche d'abstraction inutile** entre Celery et TaskIQ
- **Masque les problèmes** de concurrence sous-jacents
- **Complexifie le debugging** avec des stacks d'erreur imbriqués

### Solution Proposée

Convertir les **fonctions métier synchrones** en `async def` directement, pour que les tâches TaskIQ les appellent nativement sans wrapper.

### Inventaire des Fonctions à Convertir

| Catégorie | Nb Fonctions | Priorité | Exemples |
|-----------|--------------|----------|----------|
| **Tâches Celery pures sync** | 32 | Haute | `discovery`, `extract_metadata_batch`, `batch_entities` |
| **Tâches sync wrappant async** | 10 | Moyenne | `cluster_all_artists`, `insert_batch_direct`, `fetch_artist_lastfm_info` |
| **Helpers sync** | 15+ | Moyenne | `extract_single_file_metadata`, `call_library_api`, `scan_music_files` |
| **Déjà async** | 1 | ✅ OK | `diagnostic_missing_metadata_task` |

---

## 📦 Modifications à Appliquer

### 1. `PLAN_AMELIORE_MIGRATION_TASKIQ.md`

#### Ajout : Section "Stratégie de Conversion Async" dans Phase 4

Insérer après la section "Pour Chaque Lot" (ligne ~637) :

```markdown
## 🔄 Stratégie de Conversion Async

### Principe

**Toutes les fonctions métier migrées vers TaskIQ doivent être converties en `async def`.**

Le wrapper `run_taskiq_sync()` est un **fallback temporaire** pendant la migration, 
pas une solution cible. L'objectif est d'avoir des tâches TaskIQ 100% async.

### Règles de Conversion

#### Règle 1 : Fonctions métier → async def
Toute fonction appelée par une tâche TaskIQ doit être `async def`.

#### Règle 2 : I/O → await avec librairies async
- HTTP : `requests.get()` → `httpx.AsyncClient().get()`
- Fichiers : `open()` → `aiofiles.open()`
- DB : `session.query()` → `await session.execute()`

#### Règle 3 : CPU-bound → asyncio.to_thread()
Pour les opérations CPU-intensives (Librosa, sentence-transformers) :
```python
result = await asyncio.to_thread(cpu_heavy_function, arg1, arg2)
```

#### Règle 4 : Appels API existants → httpx.AsyncClient
Remplacer `requests` par `httpx` dans les helpers :
```python
# AVANT (sync)
import requests
response = requests.get(f"{API_URL}/api/tracks/{track_id}")

# APRÈS (async)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(f"{API_URL}/api/tracks/{track_id}")
```

### Patterns de Conversion

#### Pattern A : Fonction pure I/O (HTTP, DB)
```python
# AVANT
def get_track_by_path(path: str) -> dict | None:
    response = requests.get(f"{API_URL}/api/tracks?path={path}")
    return response.json()

# APRÈS
async def get_track_by_path(path: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/tracks?path={path}")
        return response.json()
```

#### Pattern B : Fonction CPU-bound (Librosa, ML)
```python
# AVANT
def extract_audio_features(file_path: str) -> dict:
    y, sr = librosa.load(file_path)
    mfcc = librosa.feature.mfcc(y=y, sr=sr)
    return {"mfcc": mfcc.tolist()}

# APRÈS
async def extract_audio_features(file_path: str) -> dict:
    return await asyncio.to_thread(_extract_audio_features_sync, file_path)

def _extract_audio_features_sync(file_path: str) -> dict:
    y, sr = librosa.load(file_path)
    mfcc = librosa.feature.mfcc(y=y, sr=sr)
    return {"mfcc": mfcc.tolist()}
```

#### Pattern C : Fonction mixte (I/O + CPU)
```python
# AVANT
def process_track(track_id: int) -> dict:
    track = requests.get(f"{API_URL}/api/tracks/{track_id}").json()
    features = extract_audio_features(track["path"])
    requests.post(f"{API_URL}/api/tracks/{track_id}/features", json=features)
    return {"success": True}

# APRÈS
async def process_track(track_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/tracks/{track_id}")
        track = response.json()
    
    features = await asyncio.to_thread(extract_audio_features_sync, track["path"])
    
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/api/tracks/{track_id}/features", json=features)
    
    return {"success": True}
```

### Matrice de Conversion par Lot

#### Lot 1 : Maintenance (non critique)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `celery_tasks.py` | `cleanup_old_data` | A (I/O via API) | Facile |
| `maintenance_tasks.py` | `cleanup_expired_tasks_task` | A (Redis) | Facile |
| `maintenance_tasks.py` | `rebalance_queues_task` | A (Redis) | Facile |
| `maintenance_tasks.py` | `archive_old_logs_task` | A (Fichiers) | Facile |
| `maintenance_tasks.py` | `validate_system_integrity_task` | A (Redis + API) | Facile |
| `maintenance_tasks.py` | `generate_daily_health_report_task` | A (Redis) | Facile |

#### Lot 2 : Covers (faible criticité)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `covers_tasks.py` | `process_artist_images` | A (API) | Moyenne |
| `covers_tasks.py` | `process_album_covers` | A (API) | Moyenne |
| `covers_tasks.py` | `process_track_covers_batch` | A (API + I/O fichiers) | Moyenne |
| `covers_tasks.py` | `extract_embedded` | B (CPU: Pillow) | Moyenne |

#### Lot 3 : Metadata (critique moyenne)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `celery_tasks.py` | `extract_metadata_batch` | C (I/O + CPU mutagen) | Difficile |
| `enrichment_worker.py` | `process_enrichment_batch_task` | A (API) | Moyenne |

#### Lot 4 : Batch + Insert (critique)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `process_entities_worker.py` | `batch_entities` | A (API) | Moyenne |
| `insert_batch_worker.py` | `insert_batch_direct` | C (I/O + déjà async interne) | Moyenne |

#### Lot 5 : Scan (très critique)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `celery_tasks.py` | `discovery` | A (I/O fichiers + API) | Difficile |
| `scan_worker.py` | `scan_music_files` | A (I/O fichiers) | Moyenne |

#### Lot 6 : Vectorization (critique)
| Fichier | Fonction | Pattern | Difficulté |
|---------|----------|---------|------------|
| `vectorization_worker.py` | `vectorize_track_optimized` | B (CPU: sentence-transformers) | Difficile |
| `vectorization_worker.py` | `vectorize_tracks_batch_optimized` | B (CPU) | Difficile |
| `monitoring_worker.py` | `monitor_tag_changes_task` | A (API) | Moyenne |

### Dépendances à Ajouter

```txt
# backend_worker/requirements.txt
httpx>=0.25.0      # Déjà présent ? Vérifier
aiofiles>=23.0.0   # Pour I/O fichiers async
```
```

#### Ajout : Critère de Passage Phase 4 (ligne ~660)

Ajouter dans les critères de validation :
```markdown
- [ ] **Toutes les tâches migrées sont `async def`** (pas de wrapper sync)
- [ ] **Aucun `run_taskiq_sync()`** dans les tâches migrées
- [ ] **Librairies async utilisées** (httpx, aiofiles) où applicable
```

---

### 2. `PLAN_OPTIMISE_STORIES.md`

#### Ajout : Story DEV-15 (Conversion Async Préliminaire)

Insérer après DEV-5 (Wrapper Sync/Async) et avant DEV-6 (Tâche Maintenance) :

```markdown
### Story DEV-15 : Conversion Async des Fonctions Sync
**Rôle** : Développeur  
**Durée** : 1.5 jours  
**Dépendances** : DEV-2  

#### Objectif
Convertir les fonctions sync critiques en async pour éviter les wrappers.

#### Tâches
- [ ] Auditer les fonctions sync appelées par les tâches à migrer
- [ ] Créer `backend_worker/utils/async_helpers.py`
  - `async_get(url)` : wrapper async pour GET HTTP
  - `async_post(url, data)` : wrapper async pour POST HTTP
  - `async_read_file(path)` : wrapper async pour lecture fichiers
  - `run_cpu_bound(func, *args)` : wrapper pour CPU-bound via `asyncio.to_thread()`
- [ ] Convertir les helpers sync les plus utilisés
  - `call_library_api` → `async_call_library_api` (synonym_worker.py)
  - `scan_music_files` → async (scan_worker.py)
  - `extract_single_file_metadata` → async split (enrichment_worker.py)
- [ ] Ajouter les tests unitaires pour les helpers async

#### Critères d'Acceptation
- [ ] Helpers async fonctionnels
- [ ] Tests unitaires passent
- [ ] Aucune régression sur les tests existants
- [ ] `httpx` et `aiofiles` ajoutés aux dépendances

#### Validation
```bash
python -m pytest tests/unit/worker/test_async_helpers.py -v
python -m pytest tests/unit/worker -q --tb=no
```
```

#### Modification : Stories DEV-6 à DEV-13

Ajouter un critère d'acceptation commun à chaque story de migration :
```markdown
- [ ] **Toutes les fonctions de la tâche sont `async def`** (pas de wrapper sync)
```

#### Modification : Story DEV-9 (Wrapper Sync/Async)

Ajouter un avertissement :
```markdown
> ⚠️ **Ce wrapper est un FALLBACK TEMPORAIRE**. L'objectif est de convertir 
> toutes les fonctions en async. Ce wrapper ne doit être utilisé que pendant 
> la phase de transition. Voir DEV-15 pour la stratégie de conversion.
```

---

### 3. `phase_4/briefing_developpeur.md`

#### Modification : Section "Pour Chaque Lot" → Étape 3

Remplacer le wrapper sync/async par la conversion directe :

```markdown
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
```

#### Ajout : Checklist de Conversion par Lot

```markdown
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
```

---

### 4. `STORY_ORGANIZATION.md`

#### Modification : Renommage de DEV-9

Changer :
```markdown
| **DEV-9** | Créer wrapper sync/async `taskiq_utils.py` | Phase 1 | Wrapper fonctionnel |
```

En :
```markdown
| **DEV-9** | Créer wrapper sync/async FALLBACK `taskiq_utils.py` | Phase 1 | Wrapper fonctionnel (temporaire) |
```

#### Ajout : DEV-15 dans la matrice

Insérer dans la section Phase 2 :
```markdown
| **DEV-15** | Convertir helpers sync → async | DEV-2 | Helpers async fonctionnels |
```

#### Modification : Graphe des dépendances

Ajouter :
```mermaid
    DEV-2 --> DEV-15
    DEV-15 --> DEV-7
    DEV-15 --> DEV-16
```

---

### 5. `phase_2/briefing_developpeur.md`

#### Modification : Section T2.4

Ajouter un avertissement sur le wrapper :
```markdown
> ⚠️ **Ce wrapper est un FALLBACK TEMPORAIRE**. Il sera remplacé par 
> la conversion directe des fonctions en `async def` dans les phases suivantes.
> Ne pas créer de nouvelles fonctions sync qui utilisent ce wrapper.
```

---

## 🧪 Validation

### Tests à Ajouter

1. `tests/unit/worker/test_async_helpers.py` :
   - Test `async_get()` avec mock HTTP
   - Test `async_post()` avec mock HTTP
   - Test `async_read_file()` avec fichier temporaire
   - Test `run_cpu_bound()` avec fonction CPU simulée

### Critères de Validation

- [ ] Toutes les nouvelles fonctions sont `async def`
- [ ] Aucun `run_taskiq_sync()` dans les tâches migrées
- [ ] `httpx` et `aiofiles` dans `requirements.txt`
- [ ] Tests unitaires async passent
- [ ] Tests existants passent (0 régression)
- [ ] `ruff check` passe sur les fichiers modifiés

---

## 📊 Impact sur le Planning

### Ajout de Durée

| Phase | Durée Actuelle | Durée Ajoutée | Raison |
|-------|---------------|---------------|--------|
| Phase 2 | 2-4 jours | +0.5 jour | Conversion helpers async |
| Phase 4 | 5-10 jours | +2-3 jours | Conversion fonctions par lot |
| **Total** | 19-33 jours | +2.5-3.5 jours | Gain qualité et performance |

### Gain Attendu

- **Performance** : Pas d'overhead de wrapper sync/async
- **Maintenabilité** : Code 100% async, pas de mélange sync/async
- **Debugging** : Stacks d'erreur plus clairs
- **Fiabilité** : Pas de risque de deadlock avec `asyncio.get_event_loop()`

---

## 📁 Fichiers Modifiés

| Fichier | Type de Modification |
|---------|---------------------|
| `PLAN_AMELIORE_MIGRATION_TASKIQ.md` | Ajout section "Stratégie de Conversion Async" |
| `PLAN_OPTIMISE_STORIES.md` | Ajout story DEV-15, modification DEV-6 à DEV-13 |
| `phase_4/briefing_developpeur.md` | Remplacement wrapper par conversion directe |
| `phase_2/briefing_developpeur.md` | Ajout avertissement wrapper temporaire |
| `STORY_ORGANIZATION.md` | Ajout DEV-15, modification DEV-9 |

---

*Dernière mise à jour : 2026-03-22*
*Version : 1.0*
*Statut : En cours de validation*

# Dépendances entre Tâches Celery — SoniqueBay

## 📋 Résumé

Ce document cartographie les flux de tâches Celery et les dépendances entre elles, identifiées via les appels `celery.send_task()`.

**Date d'audit** : 2026-03-20  
**Fichiers analysés** :
- `backend_worker/celery_tasks.py`
- `backend_worker/workers/` (tous les fichiers)

---

## 🔄 Flux Principal de Scan (Pipeline Complète)

```
scan.discovery
    ↓ (celery.send_task)
metadata.extract_batch (pour chaque batch de 50 fichiers)
    ↓ (celery.send_task)
batch.process_entities
    ↓ (celery.send_task)
insert.direct_batch
    ↓ (deferred_queue_service.enqueue_task)
worker_deferred_enrichment.process_enrichment_batch
```

### Détail des Appels

#### 1. `scan.discovery` → `metadata.extract_batch`

**Fichier** : [`celery_tasks.py:90-95`](backend_worker/celery_tasks.py:90)

```python
celery.send_task(
    'metadata.extract_batch',
    args=[batch_files, batch_id],
    queue='extract',
    priority=5
)
```

**Condition** : Uniquement si des fichiers sont découverts (`if discovered_files:`).

**Batches** : Les fichiers sont divisés en batches de 50 fichiers.

---

#### 2. `metadata.extract_batch` → `batch.process_entities`

**Fichier** : [`celery_tasks.py:180-185`](backend_worker/celery_tasks.py:180)

```python
celery.send_task(
    'batch.process_entities',
    args=[extracted_metadata],
    queue='batch',
    priority=5
)
```

**Condition** : Uniquement si des métadonnées sont extraites (`if extracted_metadata:`).

---

#### 3. `batch.process_entities` → `insert.direct_batch`

**Fichier** : [`celery_tasks.py:323-328`](backend_worker/celery_tasks.py:323)

```python
celery.send_task(
    'insert.direct_batch',
    args=[insertion_data],
    queue='insert',
    priority=7
)
```

**Condition** : Toujours exécuté (les données sont préparées même si vides).

---

#### 4. `insert.direct_batch` → `worker_deferred_enrichment.process_enrichment_batch`

**Fichier** : [`insert_batch_worker.py:458`](backend_worker/workers/insert/insert_batch_worker.py:458)

```python
enrichment_result = process_enrichment_batch_task.delay(batch_size=min(pending_count, 50))
```

**Note** : Utilise `.delay()` au lieu de `send_task()` car la fonction est importée localement.

**Condition** : Uniquement si des tâches d'enrichissement sont en attente (`if pending_count > 0:`).

---

## 🔄 Flux Post-Scan : Auto-Queueing GMM

```
scan.discovery (succès)
    ↓ (_maybe_trigger_gmm_clustering)
gmm.cluster_all_artists
```

### Détail de l'Appel

**Fichier** : [`scan_worker.py:263-267`](backend_worker/workers/scan/scan_worker.py:263)

```python
celery.send_task(
    'gmm.cluster_all_artists',
    args=[False],  # force_refresh=False
    queue='gmm'
)
```

**Conditions** :
- Le scan doit être réussi (`scan_result.get("success", False)`)
- Au moins 50 fichiers découverts (`files_discovered < 50`)
- ET (artistes avec features ≥ 50 OU tracks analysées ≥ 500)

---

## 🔄 Flux d'Enrichissement Différé

```
insert.direct_batch
    ↓ (deferred_queue_service.enqueue_task)
worker_deferred_enrichment.process_enrichment_batch
    ↓ (deferred_queue_service.dequeue_task)
_enrich_artist / _enrich_album / _analyze_audio
```

### Détail des Enqueues

#### Pour les Artistes

**Fichier** : [`insert_batch_worker.py:88-90`](backend_worker/workers/insert/insert_batch_worker.py:88)

```python
success = deferred_queue_service.enqueue_task(
    "deferred_enrichment", 
    task_data, 
    priority="normal", 
    delay_seconds=60
)
```

**Condition** : Artiste sans cover existante.

#### Pour les Albums

**Fichier** : [`insert_batch_worker.py:127-129`](backend_worker/workers/insert/insert_batch_worker.py:127)

```python
success = deferred_queue_service.enqueue_task(
    "deferred_enrichment", 
    task_data, 
    priority="normal", 
    delay_seconds=120
)
```

**Condition** : Album sans cover existante.

#### Pour les Tracks Audio

**Fichier** : [`insert_batch_worker.py:418-422`](backend_worker/workers/insert/insert_batch_worker.py:418)

```python
success = deferred_queue_service.enqueue_task(
    "deferred_enrichment",
    task_data,
    priority="low",
    delay_seconds=30 + (enqueued_count % 10) * 5
)
```

**Condition** : Track avec `track_id` et `file_path` valides.

---

## 🔄 Flux de Synonymes (Indépendant)

```
synonym.generate_chain
    ↓ (group)
synonym.generate_single (parallèle)
```

### Détail de l'Appel

**Fichier** : [`synonym_worker.py:335-346`](backend_worker/workers/synonym_worker.py:335)

```python
tasks.append(
    generate_synonyms_for_tag.s(
        tag_name=tag_name,
        tag_type=tag_type,
        related_tags=related_tags,
        include_embedding=include_embedding,
    )
)

job = group(tasks)
group_result = job.apply_async()
```

**Note** : Utilise le pattern Celery `group()` pour l'exécution parallèle.

---

## 🔄 Flux Last.fm (Indépendant)

```
lastfm.batch_fetch_info
    ↓ (appel direct)
lastfm.fetch_artist_info
    ↓ (appel direct)
lastfm.fetch_similar_artists
```

### Détail des Appels

**Fichier** : [`lastfm_worker.py:242-253`](backend_worker/workers/lastfm/lastfm_worker.py:242)

```python
# Fetch artist info (appel direct de la fonction, pas via apply())
info_result = fetch_artist_lastfm_info(artist_id)

# Fetch similar artists (appel direct de la fonction)
similar_result = fetch_similar_artists(artist_id)
```

**Note** : Les appels sont directs (pas via Celery), donc pas de dépendance Celery réelle.

---

## 📊 Matrice des Dépendances

| Tâche Source | Tâche Cible | Type d'Appel | Condition |
|--------------|-------------|--------------|-----------|
| `scan.discovery` | `metadata.extract_batch` | `celery.send_task()` | Fichiers découverts |
| `metadata.extract_batch` | `batch.process_entities` | `celery.send_task()` | Métadonnées extraites |
| `batch.process_entities` | `insert.direct_batch` | `celery.send_task()` | Toujours |
| `insert.direct_batch` | `worker_deferred_enrichment.process_enrichment_batch` | `.delay()` | Tâches en attente |
| `scan.discovery` | `gmm.cluster_all_artists` | `celery.send_task()` | Scan réussi + seuils |
| `synonym.generate_chain` | `synonym.generate_single` | `group()` | Toujours |
| `lastfm.batch_fetch_info` | `lastfm.fetch_artist_info` | Appel direct | Toujours |
| `lastfm.fetch_artist_info` | `lastfm.fetch_similar_artists` | Appel direct | `include_similar=True` |

---

## 🔗 Flux Complets (Diagrammes)

### Flux Principal de Scan

```
┌─────────────────┐
│  scan.discovery │
└────────┬────────┘
         │ (send_task × N batches)
         ▼
┌─────────────────────────┐
│ metadata.extract_batch  │
└────────┬────────────────┘
         │ (send_task)
         ▼
┌─────────────────────────┐
│ batch.process_entities  │
└────────┬────────────────┘
         │ (send_task)
         ▼
┌─────────────────────────┐
│  insert.direct_batch    │
└────────┬────────────────┘
         │ (delay)
         ▼
┌─────────────────────────────────────┐
│ worker_deferred_enrichment.         │
│   process_enrichment_batch          │
└─────────────────────────────────────┘
```

### Flux GMM Post-Scan

```
┌─────────────────┐
│  scan.discovery │
└────────┬────────┘
         │ (succès + seuils)
         ▼
┌─────────────────────────┐
│ gmm.cluster_all_artists │
└─────────────────────────┘
```

### Flux Synonymes

```
┌─────────────────────────┐
│ synonym.generate_chain  │
└────────┬────────────────┘
         │ (group × N tags)
         ▼
┌─────────────────────────┐
│ synonym.generate_single │ (× N parallèle)
└─────────────────────────┘
```

---

## 📝 Notes Importantes

1. **Couplage Fort** : Le flux principal de scan est fortement couplé. Une erreur dans une étape arrête toute la pipeline.

2. **Enrichissement Différé** : L'enrichissement utilise une queue Redis interne (`deferred_queue_service`), pas directement Celery. Cela permet un découplage et un contrôle de priorité.

3. **Auto-Queueing GMM** : Le clustering GMM est déclenché automatiquement après un scan réussi si les seuils sont atteints.

4. **Appels Directs** : Les tâches Last.fm utilisent des appels directs entre fonctions, pas des appels Celery. Cela réduit la overhead mais crée un couplage fort.

5. **Priorités** : La priorité 7 est utilisée pour l'insertion (plus urgente que les autres tâches à priorité 5).

---

## 🎯 Points d'Attention pour la Migration TaskIQ

1. **`celery.send_task()`** : Ces appels doivent être remplacés par les équivalents TaskIQ.

2. **`group()`** : Le pattern Celery `group()` pour l'exécution parallèle doit être adapté à TaskIQ.

3. **`.delay()`** : Les appels `.delay()` doivent être remplacés par les appels TaskIQ async.

4. **`deferred_queue_service`** : Ce service interne peut être conservé ou remplacé par les capacités de queue de TaskIQ.

5. **Ordre d'Exécution** : L'ordre des tâches dans la pipeline principale doit être préservé lors de la migration.

---

*Dernière mise à jour : 2026-03-20*
*Phase : 0 (Audit et Préparation)*

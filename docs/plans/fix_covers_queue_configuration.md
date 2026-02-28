# Plan de correction - Configuration des queues pour les covers

## Problème identifié

Les covers n'étaient pas insérées dans la base de données après un scan complet car les tâches Celery de traitement des covers étaient envoyées à une queue `deferred` qui n'était pas consommée par les workers.

## Analyse

Dans `celery_app.py`, les workers étaient configurés pour écouter les queues suivantes :
```python
worker_queues=[
    'scan', 'extract', 'batch', 'insert', 'covers',
    'deferred_vectors', 'deferred_covers', 'deferred_enrichment',
    'deferred', 'celery', 'maintenance', 'audio_analysis'
]
```

Mais les tâches de covers dans `covers_tasks.py` utilisaient la queue `deferred` :
```python
@celery.task(name="covers.process_artist_images", queue="deferred")
```

Cette queue `deferred` générique n'était pas dans la liste des queues écoutées par les workers. Les tâches étaient donc envoyées mais jamais traitées.

## Corrections effectuées

### 1. `backend_worker/tasks/covers_tasks.py`

Changement de la queue pour toutes les tâches de covers de `deferred` vers `deferred_covers` :

- `covers.process_artist_images` → queue `deferred_covers`
- `covers.process_album_covers` → queue `deferred_covers`
- `covers.process_track_covers_batch` → queue `deferred_covers`
- `covers.process_artist_images_batch` → queue `deferred_covers`
- `covers.extract_artist_images` → queue `deferred_covers`
- `covers.extract_embedded` → queue `deferred_covers`

### 2. `backend_worker/celery_tasks.py`

Changement de la queue pour les tâches locales :
- `covers.extract_embedded` → queue `deferred_covers`
- `metadata.enrich_batch` → queue `deferred_enrichment` (correction cohérence)

## Architecture des queues

Les queues sont maintenant correctement configurées :

| Queue | Usage | Tâches |
|-------|-------|--------|
| `scan` | Découverte fichiers | `scan.discovery` |
| `extract` | Extraction métadonnées | `metadata.extract_batch` |
| `batch` | Regroupement entités | `batch.process_entities` |
| `insert` | Insertion BDD | `insert.direct_batch` |
| `deferred_covers` | Traitement covers | `covers.*` |
| `deferred_enrichment` | Enrichissement données | `metadata.enrich_batch`, `worker_deferred_enrichment.*` |
| `deferred_vectors` | Vectorisation | `vectorization.*` |
| `vectorization_monitoring` | Monitoring vectorisation | `monitor_tag_changes`, `check_model_health` |
| `maintenance` | Tâches maintenance | `cleanup_expired_tasks`, etc. |
| `gmm` | Clustering GMM | `gmm.*` |
| `audio_analysis` | Analyse audio Librosa | `audio_analysis.*` |

## Étapes suivantes

1. **Redémarrer les workers Celery** pour prendre en compte les changements :
   ```bash
   docker-compose restart celery-worker
   ```

2. **Vérifier les logs** pour s'assurer que les tâches de covers sont bien reçues :
   ```bash
   docker-compose logs -f celery-worker | grep -i "covers"
   ```

3. **Effectuer un scan complet** et vérifier que les covers sont bien traitées :
   - Les callbacks dans `entity_manager.py` déclenchent les tâches après insertion
   - Les tâches `process_artist_images` et `process_album_covers` sont maintenant exécutées

4. **Vérifier la base de données** pour confirmer l'insertion des covers :
   ```sql
   SELECT COUNT(*) FROM covers;
   SELECT entity_type, COUNT(*) FROM covers GROUP BY entity_type;
   ```

## Tests recommandés

1. Lancer un scan sur un petit répertoire de test
2. Vérifier dans les logs que les tâches `covers.process_artist_images` et `covers.process_album_covers` sont bien exécutées
3. Vérifier que les covers sont présentes dans la table `covers` de la base de données
4. Vérifier que les images sont visibles dans l'interface frontend

## Notes

- Les tâches de covers sont maintenant isolées dans leur propre queue `deferred_covers`
- Cela permet un meilleur contrôle de la concurrence et de la priorité
- Les workers peuvent être configurés pour consommer plus ou moins de tâches de covers selon les besoins

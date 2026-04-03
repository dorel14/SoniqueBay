# Matrice des Tâches Celery — SoniqueBay

## 📋 Résumé

Ce document liste toutes les tâches Celery identifiées dans le projet SoniqueBay, avec leurs signatures complètes, queues, priorités et caractéristiques.

**Date d'audit** : 2026-03-20  
**Fichiers analysés** :
- `backend_worker/celery_tasks.py`
- `backend_worker/workers/` (tous les fichiers)

---

## Tâches de Scan

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `scan.discovery` | `scan` | 5 | `directory: str`, `progress_callback=None` | `dict` | Oui | Haute | [`celery_tasks.py:10`](backend_worker/celery_tasks.py:10) |

**Description** : Découverte de fichiers musicaux et lancement de la pipeline complète (discovery → extract_metadata → batch_entities → insert_batch).

---

## Tâches de Métadonnées

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `metadata.extract_batch` | `extract` | 5 | `file_paths: list[str]`, `batch_id: str = None` | `dict` | Oui | Haute | [`celery_tasks.py:123`](backend_worker/celery_tasks.py:123) |
| `metadata.enrich_batch` | `deferred_enrichment` | 8 | `track_ids: list[int]` | `dict` | Oui | Basse | [`celery_tasks.py:590`](backend_worker/celery_tasks.py:590) |

**Description** :
- `metadata.extract_batch` : Extrait les métadonnées de fichiers en parallèle avec ThreadPoolExecutor (max 2 workers pour RPi).
- `metadata.enrich_batch` : Enrichissement par lot des tracks (placeholder).

---

## Tâches de Batch

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `batch.process_entities` | `batch` | 5 | `metadata_list: list[dict]`, `batch_id: str = None` | `dict` | Oui | Haute | [`celery_tasks.py:205`](backend_worker/celery_tasks.py:205) |

**Description** : Regroupe les métadonnées par artistes et albums pour insertion optimisée.

---

## Tâches d'Insertion

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `insert.direct_batch` | `insert` | 7 | `insertion_data: Dict[str, Any]` | `dict` | Non | Haute | [`insert_batch_worker.py:54`](backend_worker/workers/insert/insert_batch_worker.py:54) |

**Description** : Insère en base de données via l'API HTTP uniquement (pas d'accès direct DB). Utilise l'entity_manager pour résolution automatique des références.

---

## Tâches de Vectorisation

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `vectorization.calculate` | `vectorization` | 5 | `track_id: int`, `metadata: dict = None` | `dict` | Oui | Moyenne | [`celery_tasks.py:345`](backend_worker/celery_tasks.py:345) |
| `vectorization.batch` | `vectorization` | 5 | `track_ids: list[int]` | `dict` | Oui | Moyenne | [`celery_tasks.py:450`](backend_worker/celery_tasks.py:450) |

**Description** :
- `vectorization.calculate` : Calcule le vecteur d'une track via sentence-transformers (modèle `all-MiniLM-L6-v2`).
- `vectorization.batch` : Calcule les vecteurs d'un batch de tracks.

---

## Tâches de Covers

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `covers.extract_embedded` | `deferred_covers` | 7 | `file_paths: list[str]` | `dict` | Oui | Basse | [`celery_tasks.py:557`](backend_worker/celery_tasks.py:557) |

**Description** : Extrait les covers intégrées pour un lot de fichiers (placeholder).

---

## Tâches GMM Clustering

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `gmm.cluster_all_artists` | `celery` (défaut) | 5 | `force_refresh: bool = False` | `dict` | Oui | Basse | [`celery_tasks.py:620`](backend_worker/celery_tasks.py:620) |
| `gmm.cluster_artist` | `celery` (défaut) | 5 | `artist_id: int` | `dict` | Oui | Basse | [`celery_tasks.py:643`](backend_worker/celery_tasks.py:643) |
| `gmm.refresh_stale_clusters` | `celery` (défaut) | 5 | `max_age_hours: int = 24` | `dict` | Oui | Basse | [`celery_tasks.py:666`](backend_worker/celery_tasks.py:666) |
| `gmm.cleanup_old_clusters` | `celery` (défaut) | 5 | `-` | `dict` | Oui | Basse | [`celery_tasks.py:690`](backend_worker/celery_tasks.py:690) |

**Description** : Clustering GMM des artistes via le service `ArtistClusteringService`.

---

## Tâches de Synonymes

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `synonym.generate_single` | `celery` (défaut) | 5 | `tag_name: str`, `tag_type: str = "genre"`, `related_tags: Optional[List[str]] = None`, `include_embedding: bool = True` | `dict` | Oui | Moyenne | [`synonym_worker.py:92`](backend_worker/workers/synonym_worker.py:92) |
| `synonym.generate_batch` | `celery` (défaut) | 5 | `tags: List[Dict[str, str]]`, `fail_silently: bool = True`, `include_embedding: bool = True` | `dict` | Oui | Moyenne | [`synonym_worker.py:216`](backend_worker/workers/synonym_worker.py:216) |
| `synonym.generate_chain` | `celery` (défaut) | 5 | `tags: List[Dict[str, str]]`, `include_embedding: bool = True` | `dict` | Oui | Moyenne | [`synonym_worker.py:299`](backend_worker/workers/synonym_worker.py:299) |
| `synonym.regenerate_all` | `celery` (défaut) | 5 | `tag_type: Optional[str] = None`, `batch_size: int = 10` | `dict` | Oui | Basse | [`synonym_worker.py:373`](backend_worker/workers/synonym_worker.py:373) |
| `synonym.check_status` | `celery` (défaut) | 5 | `tag_name: str`, `tag_type: str = "genre"` | `dict` | Oui | Basse | [`synonym_worker.py:452`](backend_worker/workers/synonym_worker.py:452) |

**Description** : Génération de synonyms pour les tags musicaux via le service LLM local (Ollama).

---

## Tâches Deferred Enrichment

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `worker_deferred_enrichment.process_enrichment_batch` | `deferred_enrichment` | 5 | `batch_size: int = 10` | `dict` | Oui | Basse | [`deferred_enrichment_worker.py:15`](backend_worker/workers/deferred/deferred_enrichment_worker.py:15) |
| `worker_deferred_enrichment.get_enrichment_stats` | `deferred_enrichment` | 5 | `-` | `dict` | Oui | Basse | [`deferred_enrichment_worker.py:197`](backend_worker/workers/deferred/deferred_enrichment_worker.py:197) |
| `worker_deferred_enrichment.retry_failed_enrichments` | `deferred_enrichment` | 5 | `max_retries: int = 5` | `dict` | Oui | Basse | [`deferred_enrichment_worker.py:221`](backend_worker/workers/deferred/deferred_enrichment_worker.py:221) |

**Description** : Traitement différé de l'enrichissement (artistes, albums, tracks audio).

---

## Tâches Last.fm

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `lastfm.fetch_artist_info` | `deferred` | 5 | `artist_id: int` | `dict` | Oui | Basse | [`lastfm_worker.py:16`](backend_worker/workers/lastfm/lastfm_worker.py:16) |
| `lastfm.fetch_similar_artists` | `deferred` | 5 | `artist_id: int`, `limit: int = 10` | `dict` | Oui | Basse | [`lastfm_worker.py:116`](backend_worker/workers/lastfm/lastfm_worker.py:116) |
| `lastfm.batch_fetch_info` | `deferred` | 5 | `artist_ids: List[int]`, `include_similar: bool = True` | `dict` | Oui | Basse | [`lastfm_worker.py:218`](backend_worker/workers/lastfm/lastfm_worker.py:218) |

**Description** : Récupération d'informations artistes depuis l'API Last.fm.

---

## Tâches Artist GMM

| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité | Fichier Source |
|-----|-------|----------|------------|--------|------------|-----------|----------------|
| `artist_gmm.train_model` | `deferred` | 5 | `n_components: int = 10`, `max_iterations: int = 100` | `dict` | Oui | Basse | [`artist_gmm_worker.py:16`](backend_worker/workers/artist_gmm/artist_gmm_worker.py:16) |
| `artist_gmm.generate_embeddings` | `deferred` | 5 | `artist_names: Optional[List[str]] = None` | `dict` | Oui | Basse | [`artist_gmm_worker.py:74`](backend_worker/workers/artist_gmm/artist_gmm_worker.py:74) |
| `artist_gmm.update_clusters` | `deferred` | 5 | `-` | `dict` | Oui | Basse | [`artist_gmm_worker.py:131`](backend_worker/workers/artist_gmm/artist_gmm_worker.py:131) |

**Description** : Entraînement de modèles GMM sur les embeddings d'artistes et gestion des similarités.

---

## 📊 Statistiques

| Catégorie | Nombre de Tâches | Criticité Haute | Criticité Moyenne | Criticité Basse |
|-----------|------------------|-----------------|-------------------|-----------------|
| Scan | 1 | 1 | 0 | 0 |
| Métadonnées | 2 | 1 | 0 | 1 |
| Batch | 1 | 1 | 0 | 0 |
| Insertion | 1 | 1 | 0 | 0 |
| Vectorisation | 2 | 0 | 2 | 0 |
| Covers | 1 | 0 | 0 | 1 |
| GMM Clustering | 4 | 0 | 0 | 4 |
| Synonymes | 5 | 0 | 5 | 0 |
| Deferred Enrichment | 3 | 0 | 0 | 3 |
| Last.fm | 3 | 0 | 0 | 3 |
| Artist GMM | 3 | 0 | 0 | 3 |
| **TOTAL** | **26** | **4** | **7** | **15** |

---

## 🔄 Queues Utilisées

| Queue | Priorité | Tâches |
|-------|----------|--------|
| `scan` | 5 | `scan.discovery` |
| `extract` | 5 | `metadata.extract_batch` |
| `batch` | 5 | `batch.process_entities` |
| `insert` | 7 | `insert.direct_batch` |
| `vectorization` | 5 | `vectorization.calculate`, `vectorization.batch` |
| `deferred_covers` | 7 | `covers.extract_embedded` |
| `deferred_enrichment` | 5, 8 | `metadata.enrich_batch`, `worker_deferred_enrichment.*` |
| `deferred` | 5 | `lastfm.*`, `artist_gmm.*` |
| `celery` (défaut) | 5 | `gmm.*`, `synonym.*` |

---

## 📝 Notes

1. **Idempotence** : La majorité des tâches sont idempotentes, sauf `insert.direct_batch` qui peut créer des doublons si exécutée plusieurs fois.

2. **Accès DB** : Seule la tâche `insert.direct_batch` accède à la DB via l'API HTTP. Toutes les autres tâches utilisent l'API REST.

3. **Modèle de vectorisation** : Le modèle `all-MiniLM-L6-v2` est utilisé pour la vectorisation (léger, adapté au RPi4).

4. **Pipeline principale** : `scan.discovery` → `metadata.extract_batch` → `batch.process_entities` → `insert.direct_batch`

5. **Enrichissement différé** : Les tâches d'enrichissement sont gérées via une queue Redis interne (`deferred_queue_service`), pas directement via Celery.

---

*Dernière mise à jour : 2026-03-20*
*Phase : 0 (Audit et Préparation)*

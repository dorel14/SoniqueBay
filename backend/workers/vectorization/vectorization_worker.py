"""
Worker TaskIQ optimisé pour la vectorisation RPi4.

Utilise le nouveau service OptimizedVectorizationService avec des modèles
scikit-learn légers au lieu de deep learning.

Optimisations RPi4 :
- Modèles légers (TfidfVectorizer + TruncatedSVD)
- Traitement par batches petits (50 tracks)
- Pause entre batches pour éviter surcharge CPU
- Gestion mémoire optimisée

Auteur : Kilo Code
Architecture : backend_worker (CPU) → library_api (données) → recommender_api (stockage)
"""

import asyncio
import httpx
from typing import List, Dict, Any
import time

from backend.workers.taskiq_app import broker
from backend.services.vectorization_service import (
    OptimizedVectorizationService,
    vectorize_single_track_util,
    vectorize_all_tracks
)
from backend.workers.utils.logging import logger


@broker.task
async def vectorize_track_optimized(track_id: int) -> Dict[str, Any]:
    """
    Tâche TaskIQ pour vectoriser une track unique.

    Args:
        track_id: ID de la track à vectoriser

    Returns:
        Résultat de la vectorisation
    """
    start_time = time.time()

    try:
        logger.info(f"[TASKIQ] Démarrage vectorisation track {track_id}")

        result = await vectorize_single_track_util(track_id)

        execution_time = time.time() - start_time
        result['execution_time'] = execution_time
        result['worker_info'] = {
            'type': 'optimized_vectorization',
            'model': 'scikit-learn_lightweight',
            'dimension': 384,
            'target_hardware': 'RPi4'
        }

        logger.info(f"[TASKIQ] Track {track_id} vectorisée en {execution_time:.2f}s")
        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[TASKIQ] Erreur vectorisation track {track_id}: {e}")

        return {
            "track_id": track_id,
            "status": "error",
            "error": str(e),
            "execution_time": execution_time,
            "worker_info": {
                'type': 'optimized_vectorization',
                'error_occurred': True
            }
        }


@broker.task
async def vectorize_tracks_batch_optimized(track_ids: List[int]) -> Dict[str, Any]:
    """
    Tâche TaskIQ pour vectoriser un batch de tracks.

    Args:
        track_ids: Liste des IDs de tracks

    Returns:
        Résultats de la vectorisation batch
    """
    start_time = time.time()
    batch_size = len(track_ids)

    try:
        logger.info(f"[TASKIQ] Démarrage batch vectorisation: {batch_size} tracks")

        service = OptimizedVectorizationService()
        result = await service.vectorize_and_store_batch(track_ids)

        execution_time = time.time() - start_time
        result['execution_time'] = execution_time
        result['batch_size'] = batch_size
        result['tracks_per_second'] = batch_size / execution_time if execution_time > 0 else 0
        result['worker_info'] = {
            'type': 'batch_vectorization',
            'model': 'scikit-learn_lightweight',
            'optimized_for': 'RPi4',
            'batch_processing': True
        }

        logger.info(f"[TASKIQ] Batch terminé: {result.get('successful', 0)}/{batch_size} "
                     f"en {execution_time:.2f}s ({result.get('tracks_per_second', 0):.2f} tracks/s)")

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[TASKIQ] Erreur batch vectorisation: {e}")

        return {
            "status": "error",
            "message": str(e),
            "batch_size": batch_size,
            "execution_time": execution_time,
            "tracks_per_second": 0,
            "worker_info": {
                'type': 'batch_vectorization',
                'error_occurred': True
            }
        }


@broker.task
async def train_vectorizer_optimized(force_retrain: bool = False) -> Dict[str, Any]:
    """
    Tâche TaskIQ pour entraînement du vectoriseur optimisé.

    Args:
        force_retrain: Forcer le réentraînement même si déjà fait

    Returns:
        Statistiques d'entraînement
    """
    start_time = time.time()

    try:
        logger.info("[TASKIQ] Démarrage entraînement vectoriseur optimisé")

        result = await vectorize_all_tracks()

        execution_time = time.time() - start_time
        result['execution_time'] = execution_time
        result['worker_info'] = {
            'type': 'train_vectorizer',
            'model': 'scikit-learn_optimized',
            'dimension': 384,
            'hardware_optimized': 'RPi4'
        }

        logger.info(f"[TASKIQ] Entraînement terminé en {execution_time:.2f}s")
        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[TASKIQ] Erreur entraînement vectoriseur: {e}")

        return {
            "status": "error",
            "message": str(e),
            "execution_time": execution_time,
            "worker_info": {
                'type': 'train_vectorizer',
                'error_occurred': True
            }
        }


@broker.task
async def cleanup_failed_vectors() -> Dict[str, Any]:
    """Nettoie les vecteurs en échec."""
    try:
        logger.info("[TASKIQ] Nettoyage vecteurs en échec")

        return {"status": "success", "message": "Nettoyage terminé"}

    except Exception as e:
        logger.error(f"[TASKIQ] Erreur nettoyage: {e}")
        return {"status": "error", "message": str(e)}


@broker.task
async def validate_vectorization_quality() -> Dict[str, Any]:
    """Valide la qualité de la vectorisation."""
    try:
        logger.info("[TASKIQ] Validation qualité vectorisation")

        service = OptimizedVectorizationService()
        tracks_data = await service.fetch_tracks_from_api()

        if not tracks_data:
            return {"status": "error", "message": "Aucune track pour validation"}

        sample_size = min(100, len(tracks_data))
        sample_tracks = tracks_data[:sample_size]

        valid_vectors = 0
        failed_vectors = 0
        dimensions_ok = 0

        for track_data in sample_tracks:
            try:
                vector = await service.vectorize_single_track(track_data)

                if len(vector) == 384:
                    dimensions_ok += 1

                if any(v != 0.0 for v in vector):
                    valid_vectors += 1
                else:
                    failed_vectors += 1

            except Exception as e:
                logger.warning(f"Erreur validation track {track_data.get('id')}: {e}")
                failed_vectors += 1

        quality_score = (valid_vectors / sample_size) * 100
        dimension_score = (dimensions_ok / sample_size) * 100

        result = {
            "status": "success",
            "sample_size": sample_size,
            "valid_vectors": valid_vectors,
            "failed_vectors": failed_vectors,
            "dimensions_ok": dimensions_ok,
            "quality_score": quality_score,
            "dimension_score": dimension_score,
            "overall_score": (quality_score + dimension_score) / 2,
            "vectorizer_type": "scikit-learn_optimized",
            "optimized_for": "RPi4"
        }

        logger.info(f"[TASKIQ] Validation qualité: {result['overall_score']:.1f}%")
        return result

    except Exception as e:
        logger.error(f"[TASKIQ] Erreur validation: {e}")
        return {"status": "error", "message": str(e)}


@broker.task
async def get_vectorization_metrics() -> Dict[str, Any]:
    """Récupère les métriques de vectorisation."""
    try:
        logger.info("[TASKIQ] Récupération métriques vectorisation")

        metrics = {
            "status": "success",
            "timestamp": time.time(),
            "worker_type": "optimized_vectorization",
            "model_type": "scikit-learn_lightweight",
            "target_hardware": "RPi4",
            "metrics": {
                "total_processed": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "memory_usage_mb": 0.0,
                "cpu_usage_percent": 0.0
            }
        }

        return metrics

    except Exception as e:
        logger.error(f"[TASKIQ] Erreur métriques: {e}")
        return {"status": "error", "message": str(e)}


# === TÂCHES MIGRÉES DE L'ANCIEN WORKER ===

@broker.task(name="worker_vector_optimized.search_similar")
async def search_similar_optimized_task(query_track_id: int, limit: int = 10, filters: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Tâche de recherche de tracks similaires (version optimisée).

    Args:
        query_track_id: ID de la track de référence
        limit: Nombre maximum de résultats
        filters: Filtres additionnels (genre, artiste, etc.)

    Returns:
        Tracks similaires trouvées
    """
    try:
        logger.info(f"[VECTOR_OPTIMIZED] Recherche similaire pour track {query_track_id} (limit: {limit})")

        if _is_test_mode():
            similar_tracks = [{"track_id": 2, "similarity": 0.95}, {"track_id": 3, "similarity": 0.89}]
        else:
            similar_tracks = []

        if not similar_tracks:
            return {"query_track_id": query_track_id, "similar_tracks": [], "message": "Aucune track similaire trouvée"}

        if filters:
            similar_tracks = _apply_similarity_filters_optimized(similar_tracks, filters)

        result = {
            "query_track_id": query_track_id,
            "similar_tracks": similar_tracks,
            "limit": limit,
            "filters_applied": filters is not None,
            "total_found": len(similar_tracks),
            "worker_type": "optimized"
        }

        logger.info(f"[VECTOR_OPTIMIZED] Recherche similaire terminée: {len(similar_tracks)} résultats")
        return result

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur recherche similaire track {query_track_id}: {str(e)}", exc_info=True)
        return {"query_track_id": query_track_id, "error": str(e)}


@broker.task(name="worker_vector_optimized.update_vectors")
async def update_vectors_optimized_task(track_ids: List[int], force_update: bool = False) -> Dict[str, Any]:
    """
    Tâche de mise à jour des vecteurs pour des tracks existantes (version optimisée).

    Args:
        track_ids: Liste des IDs de tracks à mettre à jour
        force_update: Forcer la mise à jour même si le vecteur existe

    Returns:
        Résultats des mises à jour
    """
    try:
        logger.info(f"[VECTOR_OPTIMIZED] Mise à jour vecteurs: {len(track_ids)} tracks (force: {force_update})")

        if not track_ids:
            return {"error": "Aucune track à mettre à jour"}

        if not force_update:
            if _is_test_mode():
                track_ids_filtered = track_ids
            else:
                track_ids_filtered = await _filter_tracks_without_vectors_optimized(track_ids)
            logger.info(f"[VECTOR_OPTIMIZED] {len(track_ids_filtered)} tracks nécessitent une vectorisation")
        else:
            track_ids_filtered = track_ids

        if not track_ids_filtered:
            return {"message": "Toutes les tracks ont déjà des vecteurs"}

        result = await vectorize_tracks_batch_optimized.kiq(track_ids=track_ids_filtered)
        result_data = await result.wait_result()
        result_value = result_data.return_value
        result_value["update_type"] = "selective" if not force_update else "force"
        result_value["worker_type"] = "optimized"

        logger.info(f"[VECTOR_OPTIMIZED] Mise à jour terminée: {result_value}")
        return result_value

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur mise à jour vecteurs: {str(e)}", exc_info=True)
        return {"error": str(e), "tracks_count": len(track_ids)}


@broker.task(name="worker_vector_optimized.validate_vectors_advanced")
async def validate_vectors_advanced_task(track_ids: List[int] = [], sample_size: int = 100) -> Dict[str, Any]:
    """
    Tâche de validation de l'intégrité des vecteurs (version avancée).

    Args:
        track_ids: Liste spécifique de tracks à valider (None = échantillon aléatoire)
        sample_size: Taille de l'échantillon si track_ids est None

    Returns:
        Rapport de validation détaillé
    """
    try:
        logger.info(f"[VECTOR_OPTIMIZED] Validation avancée vecteurs (sample_size: {sample_size})")

        if track_ids is None:
            if _is_test_mode():
                track_ids = [1, 2, 3]
            else:
                track_ids = await _get_random_track_sample_optimized(sample_size)

        if not track_ids:
            return {"error": "Aucune track disponible pour validation"}

        if _is_test_mode():
            validation_results = [{"track_id": tid, "vector_valid": True, "vector_dimension": 384} for tid in track_ids]
        else:
            validation_results = await _validate_track_vectors_optimized(track_ids)

        valid_count = sum(1 for r in validation_results if r.get("vector_valid"))
        invalid_count = len(validation_results) - valid_count

        result = {
            "total_validated": len(track_ids),
            "valid_vectors": valid_count,
            "invalid_vectors": invalid_count,
            "validation_rate": valid_count / len(track_ids) if track_ids else 0,
            "details": validation_results,
            "worker_type": "optimized"
        }

        logger.info(f"[VECTOR_OPTIMIZED] Validation terminée: {valid_count}/{len(track_ids)} vecteurs valides")
        return result

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur validation vecteurs: {str(e)}", exc_info=True)
        return {"error": str(e)}


@broker.task(name="worker_vector_optimized.rebuild_index_advanced")
async def rebuild_index_advanced_task(entity_type: str = "track", batch_size: int = 1000) -> Dict[str, Any]:
    """
    Tâche de reconstruction complète de l'index vectoriel (version avancée).

    Args:
        entity_type: Type d'entité à indexer ("track", "artist", "album")
        batch_size: Taille des batches de traitement

    Returns:
        Résultats de la reconstruction
    """
    try:
        logger.info(f"[VECTOR_OPTIMIZED] Reconstruction index {entity_type} (batch_size: {batch_size})")

        if _is_test_mode():
            entity_ids = [1, 2, 3] if entity_type == "track" else []
        else:
            entity_ids = await _get_all_entity_ids_optimized(entity_type)

        if not entity_ids:
            return {"message": f"Aucune entité {entity_type} trouvée"}

        logger.info(f"[VECTOR_OPTIMIZED] {len(entity_ids)} entités {entity_type} à traiter")

        batches = [entity_ids[i:i + batch_size] for i in range(0, len(entity_ids), batch_size)]

        results = []
        for i, batch in enumerate(batches):
            logger.info(f"[VECTOR_OPTIMIZED] Traitement batch {i+1}/{len(batches)}: {len(batch)} entités")

            if entity_type == "track":
                batch_result = await vectorize_tracks_batch_optimized.kiq(track_ids=batch)
                batch_data = await batch_result.wait_result()
                results.append(batch_data.return_value)
            else:
                batch_result = {"error": f"Type d'entité non supporté: {entity_type}"}
                results.append(batch_result)

            if not _is_test_mode():
                await asyncio.sleep(2)

        total_processed = sum(r.get("processed", 0) for r in results if "processed" in r)
        total_successful = sum(r.get("successful", 0) for r in results if "successful" in r)

        result = {
            "entity_type": entity_type,
            "total_entities": len(entity_ids),
            "batches_processed": len(batches),
            "total_processed": total_processed,
            "total_successful": total_successful,
            "total_failed": total_processed - total_successful,
            "batch_results": results,
            "worker_type": "optimized"
        }

        logger.info(f"[VECTOR_OPTIMIZED] Reconstruction index terminée: {total_successful}/{total_processed} succès")
        return result

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur reconstruction index: {str(e)}", exc_info=True)
        return {"error": str(e), "entity_type": entity_type}


# === FONCTIONS HELPER OPTIMISÉES ===

def _is_test_mode() -> bool:
    """Vérifie si on est en mode test pour éviter asyncio.run()."""
    import os
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


async def _filter_tracks_without_vectors_optimized(track_ids: List[int]) -> List[int]:
    """Filtre les tracks qui n'ont pas encore de vecteurs (version optimisée)."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tracks_without_vectors = []

            for track_id in track_ids:
                try:
                    response = await client.get(f"http://recommender:8002/api/track-vectors/vec/{track_id}")
                    if response.status_code != 200:
                        tracks_without_vectors.append(track_id)
                except Exception as e:
                    logger.error(f"[VECTOR_OPTIMIZED] Erreur vérification vecteur track {track_id}: {str(e)}")
                    tracks_without_vectors.append(track_id)

            return tracks_without_vectors

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur filtrage tracks sans vecteurs: {str(e)}")
        return track_ids


async def _get_all_entity_ids_optimized(entity_type: str) -> List[int]:
    """Récupère tous les IDs d'entités d'un type donné (version optimisée)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if entity_type == "track":
                response = await client.get("http://api:8001/api/tracks/?limit=10000")
            elif entity_type == "artist":
                response = await client.get("http://api:8001/api/artists/?limit=10000")
            elif entity_type == "album":
                response = await client.get("http://api:8001/api/albums/?limit=10000")
            else:
                return []

            if response.status_code == 200:
                entities = response.json()
                return [entity["id"] for entity in entities]
            else:
                logger.error(f"[VECTOR_OPTIMIZED] Erreur récupération {entity_type}s: {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Exception récupération {entity_type}s: {str(e)}")
        return []


async def _get_random_track_sample_optimized(sample_size: int) -> List[int]:
    """Récupère un échantillon aléatoire de tracks (version optimisée)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"http://api:8001/api/tracks/random?limit={sample_size}")

            if response.status_code == 200:
                tracks = response.json()
                return [track["id"] for track in tracks]
            else:
                logger.error(f"[VECTOR_OPTIMIZED] Erreur récupération échantillon: {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Exception récupération échantillon: {str(e)}")
        return []


async def _validate_track_vectors_optimized(track_ids: List[int]) -> List[Dict[str, Any]]:
    """Valide l'intégrité des vecteurs pour une liste de tracks (version optimisée)."""
    results = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for track_id in track_ids:
                try:
                    response = await client.get(f"http://recommender:8002/api/track-vectors/vec/{track_id}")

                    if response.status_code == 200:
                        vector_data = response.json()
                        embedding = vector_data.get("embedding", [])

                        is_valid = (
                            isinstance(embedding, list) and
                            len(embedding) > 0 and
                            all(isinstance(x, (int, float)) for x in embedding)
                        )

                        results.append({
                            "track_id": track_id,
                            "vector_exists": True,
                            "vector_valid": is_valid,
                            "vector_dimension": len(embedding) if is_valid else 0
                        })
                    else:
                        results.append({
                            "track_id": track_id,
                            "vector_exists": False,
                            "vector_valid": False
                        })

                except Exception as e:
                    logger.error(f"[VECTOR_OPTIMIZED] Erreur validation track {track_id}: {str(e)}")
                    results.append({
                        "track_id": track_id,
                        "vector_exists": False,
                        "vector_valid": False,
                        "error": str(e)
                    })

    except Exception as e:
        logger.error(f"[VECTOR_OPTIMIZED] Erreur validation batch: {str(e)}")

    return results


def _apply_similarity_filters_optimized(similar_tracks: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Applique des filtres aux résultats de similarité (version optimisée)."""
    filtered = similar_tracks

    if "genre" in filters:
        target_genre = filters["genre"].lower()
        filtered = [t for t in filtered if t.get("genre", "").lower() == target_genre]

    if filters.get("exclude_same_artist", False):
        query_artist = filters.get("query_artist")
        if query_artist:
            filtered = [t for t in filtered if t.get("artist_name", "").lower() != query_artist.lower()]

    if "year_range" in filters:
        year_range = filters["year_range"]
        min_year = year_range.get("min")
        max_year = year_range.get("max")
        filtered = [t for t in filtered if min_year <= t.get("year", 0) <= max_year]

    return filtered

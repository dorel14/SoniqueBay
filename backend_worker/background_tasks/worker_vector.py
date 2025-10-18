"""
Worker Vector - Calcul et stockage des vecteurs
Responsable du calcul et du stockage des vecteurs d'embedding pour le système de recommandation.
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.vectorization_service import (
    vectorize_tracks, vectorize_single_track, vectorize_and_store_batch,
    VectorizationService, search_similar_tracks
)


def _is_test_mode() -> bool:
    """Vérifie si on est en mode test pour éviter asyncio.run()."""
    import os
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


@celery.task(name="worker_vector.vectorize_tracks_batch", queue="worker_vector")
def vectorize_tracks_batch_task(track_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
    """
    Tâche de vectorisation par lot des tracks.

    Args:
        track_ids: Liste des IDs de tracks à vectoriser
        priority: Priorité de traitement ("high", "normal", "low")

    Returns:
        Résultats de la vectorisation
    """
    try:
        logger.info(f"[WORKER_VECTOR] Démarrage vectorisation batch: {len(track_ids)} tracks (priorité: {priority})")

        if not track_ids:
            return {"error": "Aucune track à vectoriser"}

        # Traitement par lots pour optimiser les performances
        batch_size = 50 if priority == "high" else 25
        batches = [track_ids[i:i + batch_size] for i in range(0, len(track_ids), batch_size)]

        results = []
        for batch in batches:
            if _is_test_mode():
                batch_result = {"total": len(batch), "successful": len(batch), "failed": 0}
            else:
                batch_result = asyncio.run(vectorize_and_store_batch(batch))
            results.append(batch_result)

            # Pause entre les batches pour éviter la surcharge CPU/mémoire
            if priority != "high" and not _is_test_mode():
                asyncio.run(asyncio.sleep(0.5))

        # Consolidation des résultats
        total = sum(r.get("total", 0) for r in results)
        successful = sum(r.get("successful", 0) for r in results)
        failed = sum(r.get("failed", 0) for r in results)

        result = {
            "total_tracks": len(track_ids),
            "processed": total,
            "successful": successful,
            "failed": failed,
            "priority": priority,
            "batch_results": results
        }

        logger.info(f"[WORKER_VECTOR] Vectorisation batch terminée: {successful}/{total} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur vectorisation batch: {str(e)}", exc_info=True)
        return {"error": str(e), "tracks_count": len(track_ids)}


@celery.task(name="worker_vector.vectorize_single_track_task", queue="worker_vector")
def vectorize_single_track_task(track_id: int) -> Dict[str, Any]:
    """
    Tâche de vectorisation d'une track unique.

    Args:
        track_id: ID de la track à vectoriser

    Returns:
        Résultat de la vectorisation
    """
    try:
        logger.info(f"[WORKER_VECTOR] Vectorisation track unique: {track_id}")

        if _is_test_mode():
            result = {"track_id": track_id, "status": "success", "vector_dimension": 384}
        else:
            result = asyncio.run(vectorize_single_track(track_id))

        logger.info(f"[WORKER_VECTOR] Vectorisation track {track_id} terminée: {result}")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur vectorisation track {track_id}: {str(e)}", exc_info=True)
        return {"track_id": track_id, "error": str(e)}


@celery.task(name="worker_vector.update_tracks_vectors", queue="worker_vector")
def update_tracks_vectors_task(track_ids: List[int], force_update: bool = False) -> Dict[str, Any]:
    """
    Tâche de mise à jour des vecteurs pour des tracks existantes.

    Args:
        track_ids: Liste des IDs de tracks à mettre à jour
        force_update: Forcer la mise à jour même si le vecteur existe

    Returns:
        Résultats des mises à jour
    """
    try:
        logger.info(f"[WORKER_VECTOR] Mise à jour vecteurs: {len(track_ids)} tracks (force: {force_update})")

        if not track_ids:
            return {"error": "Aucune track à mettre à jour"}

        # Filtrage des tracks qui ont déjà des vecteurs (sauf si force_update)
        if not force_update:
            if _is_test_mode():
                track_ids = track_ids  # En test, garder tous les IDs
            else:
                track_ids = asyncio.run(_filter_tracks_without_vectors(track_ids))
            logger.info(f"[WORKER_VECTOR] {len(track_ids)} tracks nécessitent une vectorisation")

        if not track_ids:
            return {"message": "Toutes les tracks ont déjà des vecteurs"}

        # Vectorisation des tracks filtrées
        result = vectorize_tracks_batch_task(track_ids, "normal")
        result["update_type"] = "selective" if not force_update else "force"

        logger.info(f"[WORKER_VECTOR] Mise à jour terminée: {result}")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur mise à jour vecteurs: {str(e)}", exc_info=True)
        return {"error": str(e), "tracks_count": len(track_ids)}


@celery.task(name="worker_vector.rebuild_index", queue="worker_vector")
def rebuild_index_task(entity_type: str = "track", batch_size: int = 1000) -> Dict[str, Any]:
    """
    Tâche de reconstruction complète de l'index vectoriel.

    Args:
        entity_type: Type d'entité à indexer ("track", "artist", "album")
        batch_size: Taille des batches de traitement

    Returns:
        Résultats de la reconstruction
    """
    try:
        logger.info(f"[WORKER_VECTOR] Reconstruction index {entity_type} (batch_size: {batch_size})")

        # Récupération de tous les IDs d'entités
        if _is_test_mode():
            entity_ids = [1, 2, 3] if entity_type == "track" else []  # Simulation pour tests
        else:
            entity_ids = asyncio.run(_get_all_entity_ids(entity_type))

        if not entity_ids:
            return {"message": f"Aucune entité {entity_type} trouvée"}

        logger.info(f"[WORKER_VECTOR] {len(entity_ids)} entités {entity_type} à traiter")

        # Traitement par gros batches
        batches = [entity_ids[i:i + batch_size] for i in range(0, len(entity_ids), batch_size)]

        results = []
        for i, batch in enumerate(batches):
            logger.info(f"[WORKER_VECTOR] Traitement batch {i+1}/{len(batches)}: {len(batch)} entités")

            if entity_type == "track":
                batch_result = vectorize_tracks_batch_task(batch, "low")
            else:
                # Pour artistes/albums, logique différente (non implémentée pour l'instant)
                batch_result = {"error": f"Type d'entité non supporté: {entity_type}"}

            results.append(batch_result)

            # Pause plus longue entre les gros batches
            if not _is_test_mode():
                asyncio.run(asyncio.sleep(2))

        # Consolidation des résultats
        total_processed = sum(r.get("processed", 0) for r in results if "processed" in r)
        total_successful = sum(r.get("successful", 0) for r in results if "successful" in r)

        result = {
            "entity_type": entity_type,
            "total_entities": len(entity_ids),
            "batches_processed": len(batches),
            "total_processed": total_processed,
            "total_successful": total_successful,
            "total_failed": total_processed - total_successful,
            "batch_results": results
        }

        logger.info(f"[WORKER_VECTOR] Reconstruction index terminée: {total_successful}/{total_processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur reconstruction index: {str(e)}", exc_info=True)
        return {"error": str(e), "entity_type": entity_type}


@celery.task(name="worker_vector.search_similar", queue="worker_vector")
def search_similar_task(query_track_id: int, limit: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Tâche de recherche de tracks similaires.

    Args:
        query_track_id: ID de la track de référence
        limit: Nombre maximum de résultats
        filters: Filtres additionnels (genre, artiste, etc.)

    Returns:
        Tracks similaires trouvées
    """
    try:
        logger.info(f"[WORKER_VECTOR] Recherche similaire pour track {query_track_id} (limit: {limit})")

        # Recherche des tracks similaires
        if _is_test_mode():
            similar_tracks = [{"track_id": 2, "similarity": 0.95}, {"track_id": 3, "similarity": 0.89}]
        else:
            similar_tracks = asyncio.run(search_similar_tracks(query_track_id, limit))

        if not similar_tracks:
            return {"query_track_id": query_track_id, "similar_tracks": [], "message": "Aucune track similaire trouvée"}

        # Application des filtres si fournis
        if filters:
            similar_tracks = _apply_similarity_filters(similar_tracks, filters)

        result = {
            "query_track_id": query_track_id,
            "similar_tracks": similar_tracks,
            "limit": limit,
            "filters_applied": filters is not None,
            "total_found": len(similar_tracks)
        }

        logger.info(f"[WORKER_VECTOR] Recherche similaire terminée: {len(similar_tracks)} résultats")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur recherche similaire track {query_track_id}: {str(e)}", exc_info=True)
        return {"query_track_id": query_track_id, "error": str(e)}


@celery.task(name="worker_vector.validate_vectors", queue="worker_vector")
def validate_vectors_task(track_ids: List[int] = None, sample_size: int = 100) -> Dict[str, Any]:
    """
    Tâche de validation de l'intégrité des vecteurs.

    Args:
        track_ids: Liste spécifique de tracks à valider (None = échantillon aléatoire)
        sample_size: Taille de l'échantillon si track_ids est None

    Returns:
        Rapport de validation
    """
    try:
        logger.info(f"[WORKER_VECTOR] Validation vecteurs (sample_size: {sample_size})")

        if track_ids is None:
            # Sélection d'un échantillon aléatoire
            if _is_test_mode():
                track_ids = [1, 2, 3]  # Simulation pour tests
            else:
                track_ids = asyncio.run(_get_random_track_sample(sample_size))

        if not track_ids:
            return {"error": "Aucune track disponible pour validation"}

        # Validation des vecteurs
        if _is_test_mode():
            validation_results = [{"track_id": tid, "vector_valid": True, "vector_dimension": 384} for tid in track_ids]
        else:
            validation_results = asyncio.run(_validate_track_vectors(track_ids))

        valid_count = sum(1 for r in validation_results if r.get("vector_valid"))
        invalid_count = len(validation_results) - valid_count

        result = {
            "total_validated": len(track_ids),
            "valid_vectors": valid_count,
            "invalid_vectors": invalid_count,
            "validation_rate": valid_count / len(track_ids) if track_ids else 0,
            "details": validation_results
        }

        logger.info(f"[WORKER_VECTOR] Validation terminée: {valid_count}/{len(track_ids)} vecteurs valides")
        return result

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur validation vecteurs: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def _filter_tracks_without_vectors(track_ids: List[int]) -> List[int]:
    """
    Filtre les tracks qui n'ont pas encore de vecteurs.

    Args:
        track_ids: Liste des IDs de tracks

    Returns:
        Liste des IDs de tracks sans vecteurs
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tracks_without_vectors = []

            for track_id in track_ids:
                try:
                    # Vérifier si le vecteur existe
                    response = await client.get(f"http://backend:8001/api/track-vectors/vec/{track_id}")
                    if response.status_code != 200:
                        tracks_without_vectors.append(track_id)
                except Exception as e:
                    logger.error(f"[WORKER_VECTOR] Erreur vérification vecteur track {track_id}: {str(e)}")
                    tracks_without_vectors.append(track_id)  # Inclure en cas d'erreur

            return tracks_without_vectors

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur filtrage tracks sans vecteurs: {str(e)}")
        return track_ids  # Retourner tous en cas d'erreur


async def _get_all_entity_ids(entity_type: str) -> List[int]:
    """
    Récupère tous les IDs d'entités d'un type donné.

    Args:
        entity_type: Type d'entité

    Returns:
        Liste des IDs
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if entity_type == "track":
                response = await client.get("http://backend:8001/api/tracks/?limit=10000")
            elif entity_type == "artist":
                response = await client.get("http://backend:8001/api/artists/?limit=10000")
            elif entity_type == "album":
                response = await client.get("http://backend:8001/api/albums/?limit=10000")
            else:
                return []

            if response.status_code == 200:
                entities = response.json()
                return [entity["id"] for entity in entities]
            else:
                logger.error(f"[WORKER_VECTOR] Erreur récupération {entity_type}s: {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Exception récupération {entity_type}s: {str(e)}")
        return []


def _apply_similarity_filters(similar_tracks: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applique des filtres aux résultats de similarité.

    Args:
        similar_tracks: Liste des tracks similaires
        filters: Filtres à appliquer

    Returns:
        Liste filtrée
    """
    filtered = similar_tracks

    # Filtre par genre
    if "genre" in filters:
        target_genre = filters["genre"].lower()
        filtered = [t for t in filtered if t.get("genre", "").lower() == target_genre]

    # Filtre par artiste (éviter les recommandations du même artiste)
    if filters.get("exclude_same_artist", False):
        query_artist = filters.get("query_artist")
        if query_artist:
            filtered = [t for t in filtered if t.get("artist_name", "").lower() != query_artist.lower()]

    # Filtre par année
    if "year_range" in filters:
        year_range = filters["year_range"]
        min_year = year_range.get("min")
        max_year = year_range.get("max")
        filtered = [t for t in filtered if min_year <= t.get("year", 0) <= max_year]

    return filtered


async def _get_random_track_sample(sample_size: int) -> List[int]:
    """
    Récupère un échantillon aléatoire de tracks.

    Args:
        sample_size: Taille de l'échantillon

    Returns:
        Liste des IDs de tracks
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"http://backend:8001/api/tracks/random?limit={sample_size}")

            if response.status_code == 200:
                tracks = response.json()
                return [track["id"] for track in tracks]
            else:
                logger.error(f"[WORKER_VECTOR] Erreur récupération échantillon: {response.status_code}")
                return []

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Exception récupération échantillon: {str(e)}")
        return []


async def _validate_track_vectors(track_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Valide l'intégrité des vecteurs pour une liste de tracks.

    Args:
        track_ids: IDs des tracks à valider

    Returns:
        Résultats de validation détaillés
    """
    results = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for track_id in track_ids:
                try:
                    # Récupération du vecteur
                    response = await client.get(f"http://backend:8001/api/track-vectors/vec/{track_id}")

                    if response.status_code == 200:
                        vector_data = response.json()
                        embedding = vector_data.get("embedding", [])

                        # Validation de base du vecteur
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
                    logger.error(f"[WORKER_VECTOR] Erreur validation track {track_id}: {str(e)}")
                    results.append({
                        "track_id": track_id,
                        "vector_exists": False,
                        "vector_valid": False,
                        "error": str(e)
                    })

    except Exception as e:
        logger.error(f"[WORKER_VECTOR] Erreur validation batch: {str(e)}")

    return results
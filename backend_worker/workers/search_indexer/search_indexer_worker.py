"""
Worker Celery pour l'indexation Whoosh des tracks musicales.

Ce worker récupère les données des tracks via l'API Library et les indexe
dans Whoosh pour permettre la recherche full-text as you type.

Optimisé pour Raspberry Pi 4 : traitement par batches, gestion mémoire.
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event
from backend.api.utils.search import get_or_create_index, add_to_index, delete_index
import os
from pathlib import Path


@celery.task(name="search_indexer.build_index", queue="scan", bind=True)
def build_search_index_task(self, index_dir: str = "search_index", batch_size: int = 500) -> Dict[str, Any]:
    """
    Tâche principale pour construire l'index Whoosh complet.

    Récupère toutes les tracks via l'API et les indexe par batches.

    Args:
        index_dir: Répertoire de l'index Whoosh
        batch_size: Taille des batches de traitement

    Returns:
        Résultats de l'indexation
    """
    try:
        task_id = self.request.id
        logger.info(f"[SEARCH_INDEXER] Démarrage indexation complète: index_dir={index_dir}, batch_size={batch_size}")

        # Publier progression SSE
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Initialisation de l'indexation",
            "current": 0,
            "total": 100,
            "percent": 0
        }, channel="progress")

        # Récupérer le nombre total de tracks
        total_tracks = _get_total_tracks_count()
        if total_tracks == 0:
            logger.warning("[SEARCH_INDEXER] Aucune track trouvée dans la bibliothèque")
            return {
                "success": True,
                "tracks_processed": 0,
                "total_tracks": 0,
                "batches_processed": 0,
                "index_dir": index_dir
            }

        logger.info(f"[SEARCH_INDEXER] {total_tracks} tracks à indexer")

        # Nettoyer l'index existant si nécessaire
        _cleanup_existing_index(index_dir)

        # Calculer le nombre de batches
        num_batches = (total_tracks + batch_size - 1) // batch_size
        logger.info(f"[SEARCH_INDEXER] Traitement en {num_batches} batches de {batch_size} tracks")

        tracks_processed = 0
        batches_processed = 0

        # Traiter par batches
        for batch_num in range(num_batches):
            offset = batch_num * batch_size

            # Récupérer un batch de tracks
            tracks_batch = _get_tracks_batch(offset, batch_size)
            if not tracks_batch:
                logger.info(f"[SEARCH_INDEXER] Batch {batch_num + 1} vide, arrêt")
                break

            # Indexer le batch
            batch_result = _index_tracks_batch(tracks_batch, index_dir)
            tracks_processed += batch_result["tracks_indexed"]
            batches_processed += 1

            # Publier progression
            progress_percent = min(100, int((tracks_processed / total_tracks) * 100))
            publish_event("progress", {
                "type": "progress",
                "task_id": task_id,
                "step": f"Indexation batch {batches_processed}/{num_batches}",
                "current": tracks_processed,
                "total": total_tracks,
                "percent": progress_percent,
                "tracks_indexed": tracks_processed
            }, channel="progress")

            logger.info(f"[SEARCH_INDEXER] Batch {batches_processed}/{num_batches} traité: {len(tracks_batch)} tracks")

        # Finalisation
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Indexation terminée",
            "current": tracks_processed,
            "total": total_tracks,
            "percent": 100,
            "tracks_indexed": tracks_processed
        }, channel="progress")

        result = {
            "success": True,
            "tracks_processed": tracks_processed,
            "total_tracks": total_tracks,
            "batches_processed": batches_processed,
            "index_dir": index_dir,
            "task_id": task_id
        }

        logger.info(f"[SEARCH_INDEXER] Indexation terminée: {result}")
        return result

    except Exception as e:
        error_msg = f"Erreur lors de l'indexation: {str(e)}"
        logger.error(f"[SEARCH_INDEXER] {error_msg}")

        # Publier erreur SSE
        publish_event("progress", {
            "type": "error",
            "task_id": self.request.id,
            "step": "Erreur d'indexation",
            "error": error_msg
        }, channel="progress")

        return {
            "success": False,
            "error": error_msg,
            "tracks_processed": 0,
            "task_id": self.request.id
        }


@celery.task(name="search_indexer.update_index", queue="scan", bind=True)
def update_search_index_task(self, track_ids: List[int], index_dir: str = "search_index") -> Dict[str, Any]:
    """
    Met à jour l'index Whoosh pour des tracks spécifiques.

    Args:
        track_ids: Liste des IDs des tracks à mettre à jour
        index_dir: Répertoire de l'index Whoosh

    Returns:
        Résultats de la mise à jour
    """
    try:
        task_id = self.request.id
        logger.info(f"[SEARCH_INDEXER] Mise à jour index pour {len(track_ids)} tracks")

        tracks_updated = 0

        # Traiter chaque track
        for track_id in track_ids:
            # Récupérer les données de la track
            track_data = _get_track_data(track_id)
            if track_data:
                # Indexer la track
                _index_single_track(track_data, index_dir)
                tracks_updated += 1

        result = {
            "success": True,
            "tracks_updated": tracks_updated,
            "total_requested": len(track_ids),
            "index_dir": index_dir,
            "task_id": task_id
        }

        logger.info(f"[SEARCH_INDEXER] Mise à jour terminée: {result}")
        return result

    except Exception as e:
        error_msg = f"Erreur lors de la mise à jour: {str(e)}"
        logger.error(f"[SEARCH_INDEXER] {error_msg}")

        return {
            "success": False,
            "error": error_msg,
            "tracks_updated": 0,
            "task_id": self.request.id
        }


@celery.task(name="search_indexer.clear_index", queue="maintenance")
def clear_search_index_task(index_dir: str = "search_index") -> Dict[str, Any]:
    """
    Vide complètement l'index Whoosh.

    Args:
        index_dir: Répertoire de l'index Whoosh

    Returns:
        Résultats du nettoyage
    """
    try:
        logger.info(f"[SEARCH_INDEXER] Nettoyage index: {index_dir}")

        # Supprimer l'index
        _cleanup_existing_index(index_dir)

        result = {
            "success": True,
            "index_dir": index_dir,
            "action": "cleared"
        }

        logger.info(f"[SEARCH_INDEXER] Index nettoyé: {result}")
        return result

    except Exception as e:
        error_msg = f"Erreur lors du nettoyage: {str(e)}"
        logger.error(f"[SEARCH_INDEXER] {error_msg}")

        return {
            "success": False,
            "error": error_msg,
            "index_dir": index_dir
        }


async def _get_total_tracks_count_async() -> int:
    """Récupère le nombre total de tracks via l'API de manière asynchrone."""
    try:
        # URL de l'API Library
        library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")

        async with httpx.AsyncClient(
            base_url=library_api_url,
            timeout=httpx.Timeout(30.0)
        ) as client:
            # Utiliser l'endpoint GraphQL pour compter les tracks
            query = """
            query GetTracksCount {
                tracksConnection {
                    aggregate {
                        count
                    }
                }
            }
            """

            from backend_worker.services.entity_manager import execute_graphql_query
            result = await execute_graphql_query(client, query)

            count = result.get("tracksConnection", {}).get("aggregate", {}).get("count", 0)
            logger.info(f"[SEARCH_INDEXER] Nombre total de tracks: {count}")
            return count

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur comptage tracks: {e}")
        return 0


def _get_total_tracks_count() -> int:
    """Wrapper synchrone pour _get_total_tracks_count_async."""
    import asyncio
    return asyncio.run(_get_total_tracks_count_async())


async def _get_tracks_batch_async(offset: int, limit: int) -> List[Dict[str, Any]]:
    """Récupère un batch de tracks via l'API de manière asynchrone."""
    try:
        # URL de l'API Library
        library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")

        async with httpx.AsyncClient(
            base_url=library_api_url,
            timeout=httpx.Timeout(60.0)  # Plus long pour les gros batches
        ) as client:
            # Utiliser GraphQL pour récupérer les tracks avec pagination
            query = """
            query GetTracksBatch($first: Int!, $skip: Int!) {
                tracks(first: $first, skip: $skip) {
                    id
                    path
                    title
                    artist {
                        name
                    }
                    album {
                        title
                    }
                    genre
                    year
                    duration
                    track_number
                    disc_number
                    musicbrainz_id
                    musicbrainz_albumid
                    musicbrainz_artistid
                    musicbrainz_genre
                }
            }
            """

            variables = {
                "first": limit,
                "skip": offset
            }

            from backend_worker.services.entity_manager import execute_graphql_query
            result = await execute_graphql_query(client, query, variables)

            tracks_data = result.get("tracks", [])

            # Transformer les données pour correspondre au format attendu
            formatted_tracks = []
            for track in tracks_data:
                formatted_track = {
                    "id": track.get("id"),
                    "path": track.get("path"),
                    "title": track.get("title"),
                    "artist": track.get("artist", {}).get("name") if track.get("artist") else None,
                    "album": track.get("album", {}).get("title") if track.get("album") else None,
                    "genre": track.get("genre"),
                    "year": track.get("year"),
                    "duration": track.get("duration"),
                    "track_number": track.get("track_number"),
                    "disc_number": track.get("disc_number"),
                    "musicbrainz_id": track.get("musicbrainz_id"),
                    "musicbrainz_albumid": track.get("musicbrainz_albumid"),
                    "musicbrainz_artistid": track.get("musicbrainz_artistid"),
                    "musicbrainz_genre": track.get("musicbrainz_genre")
                }
                formatted_tracks.append(formatted_track)

            logger.info(f"[SEARCH_INDEXER] Récupéré {len(formatted_tracks)} tracks (offset: {offset}, limit: {limit})")
            return formatted_tracks

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur récupération batch tracks: {e}")
        return []


def _get_tracks_batch(offset: int, limit: int) -> List[Dict[str, Any]]:
    """Wrapper synchrone pour _get_tracks_batch_async."""
    import asyncio
    return asyncio.run(_get_tracks_batch_async(offset, limit))


async def _get_track_data_async(track_id: int) -> Optional[Dict[str, Any]]:
    """Récupère les données d'une track spécifique via l'API de manière asynchrone."""
    try:
        # URL de l'API Library
        library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")

        async with httpx.AsyncClient(
            base_url=library_api_url,
            timeout=httpx.Timeout(30.0)
        ) as client:
            # Utiliser GraphQL pour récupérer une track spécifique
            query = """
            query GetTrack($id: ID!) {
                track(where: {id: $id}) {
                    id
                    path
                    title
                    artist {
                        name
                    }
                    album {
                        title
                    }
                    genre
                    year
                    duration
                    track_number
                    disc_number
                    musicbrainz_id
                    musicbrainz_albumid
                    musicbrainz_artistid
                    musicbrainz_genre
                }
            }
            """

            variables = {"id": str(track_id)}

            from backend_worker.services.entity_manager import execute_graphql_query
            result = await execute_graphql_query(client, query, variables)

            track_data = result.get("track")
            if not track_data:
                logger.warning(f"[SEARCH_INDEXER] Track {track_id} non trouvée")
                return None

            # Transformer les données pour correspondre au format attendu
            formatted_track = {
                "id": track_data.get("id"),
                "path": track_data.get("path"),
                "title": track_data.get("title"),
                "artist": track_data.get("artist", {}).get("name") if track_data.get("artist") else None,
                "album": track_data.get("album", {}).get("title") if track_data.get("album") else None,
                "genre": track_data.get("genre"),
                "year": track_data.get("year"),
                "duration": track_data.get("duration"),
                "track_number": track_data.get("track_number"),
                "disc_number": track_data.get("disc_number"),
                "musicbrainz_id": track_data.get("musicbrainz_id"),
                "musicbrainz_albumid": track_data.get("musicbrainz_albumid"),
                "musicbrainz_artistid": track_data.get("musicbrainz_artistid"),
                "musicbrainz_genre": track_data.get("musicbrainz_genre")
            }

            logger.debug(f"[SEARCH_INDEXER] Track {track_id} récupérée: {formatted_track.get('title')}")
            return formatted_track

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur récupération track {track_id}: {e}")
        return None


def _get_track_data(track_id: int) -> Optional[Dict[str, Any]]:
    """Wrapper synchrone pour _get_track_data_async."""
    import asyncio
    return asyncio.run(_get_track_data_async(track_id))


def _index_tracks_batch(tracks: List[Dict[str, Any]], index_dir: str) -> Dict[str, Any]:
    """Indexe un batch de tracks dans Whoosh."""
    try:
        tracks_indexed = 0

        for track in tracks:
            try:
                _index_single_track(track, index_dir)
                tracks_indexed += 1
            except Exception as e:
                logger.error(f"[SEARCH_INDEXER] Erreur indexation track {track.get('id')}: {e}")
                continue

        return {
            "tracks_indexed": tracks_indexed,
            "batch_size": len(tracks)
        }

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur indexation batch: {e}")
        return {
            "tracks_indexed": 0,
            "batch_size": len(tracks),
            "error": str(e)
        }


def _index_single_track(track: Dict[str, Any], index_dir: str) -> None:
    """Indexe une seule track dans Whoosh."""
    try:
        # Récupérer/créer l'index
        index = get_or_create_index(index_dir)

        # Ajouter à l'index
        add_to_index(index, track)

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur indexation track {track.get('id')}: {e}")
        raise


def _cleanup_existing_index(index_dir: str) -> None:
    """Nettoie l'index existant."""
    try:
        # Utiliser la validation sécurisée
        from backend.api.utils.search import validate_index_directory
        safe_index_dir = validate_index_directory(index_dir)

        index_path = Path("./data/search_indexes") / safe_index_dir

        if index_path.exists():
            import shutil
            shutil.rmtree(index_path, ignore_errors=True)
            logger.info(f"[SEARCH_INDEXER] Index nettoyé: {index_path}")

    except Exception as e:
        logger.error(f"[SEARCH_INDEXER] Erreur nettoyage index: {e}")
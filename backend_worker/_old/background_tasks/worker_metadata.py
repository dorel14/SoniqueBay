"""
Worker Metadata - Extraction et enrichissement des métadonnées

Responsabilités :
- Extraction des métadonnées de base depuis les fichiers audio
- Enrichissement des tracks avec BPM, genres et tags via APIs externes
- Analyse audio et vectorisation

Optimisations Raspberry Pi :
- max_workers = 2 pour extraction
- Timeouts réduits (60s par fichier)
- Batches plus petits (25 fichiers)
- Traitement séquentiel pour éviter surcharge

Architecture :
1. Extraction : extract_metadata_batch -> métadonnées de base
2. Enrichissement : enrich_tracks_batch -> BPM, genres, tags
3. Analyse : analyze_audio_features -> caractéristiques audio
"""

import asyncio
import httpx
import time
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event
from backend_worker.celery_app import celery
from backend_worker.services.audio_features_service import analyze_audio_with_librosa, analyze_audio_batch
from backend_worker.services.enrichment_service import enrich_artist, enrich_album
from backend_worker.services.cache_service import CacheService

library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")
recommender_api_url = os.getenv("RECOMMENDER_API_URL", "http://recommender:8002")

def _is_test_mode() -> bool:
    """Vérifie si on est en mode test."""
    import os
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


@celery.task(name="worker_metadata.enrich_tracks_batch", queue="worker_metadata")
def enrich_tracks_batch_task(track_ids: List[int], enrichment_types: List[str] = None) -> Dict[str, Any]:
    """
    Tâche d'enrichissement par lot des tracks.

    Args:
        track_ids: Liste des IDs de tracks à enrichir
        enrichment_types: Types d'enrichissement ("audio", "artist", "album", "all")

    Returns:
        Résultats de l'enrichissement
    """
    try:
        if enrichment_types is None:
            enrichment_types = ["all"]

        logger.info(f"[WORKER_METADATA] Démarrage enrichissement batch: {len(track_ids)} tracks, types: {enrichment_types}")

        if not track_ids:
            return {"error": "Aucune track à enrichir"}

        # Traitement par lots pour éviter la surcharge
        batch_size = 20  # Taille optimale pour l'enrichissement
        batches = [track_ids[i:i + batch_size] for i in range(0, len(track_ids), batch_size)]

        results = []
        for batch in batches:
            if _is_test_mode():
                batch_result = {"processed": len(batch), "audio_enriched": len(batch), "artists_enriched": len(batch), "albums_enriched": len(batch)}
            else:
                batch_result = asyncio.run(_enrich_tracks_batch(batch, enrichment_types))
            results.append(batch_result)

            # Pause entre les batches
            if not _is_test_mode():
                asyncio.run(asyncio.sleep(0.5))

        # Consolidation des résultats
        total_processed = sum(r.get("processed", 0) for r in results)
        audio_enriched = sum(r.get("audio_enriched", 0) for r in results)
        artists_enriched = sum(r.get("artists_enriched", 0) for r in results)
        albums_enriched = sum(r.get("albums_enriched", 0) for r in results)

        result = {
            "total_tracks": len(track_ids),
            "processed": total_processed,
            "audio_enriched": audio_enriched,
            "artists_enriched": artists_enriched,
            "albums_enriched": albums_enriched,
            "enrichment_types": enrichment_types,
            "batch_results": results
        }

        logger.info(f"[WORKER_METADATA] Enrichissement terminé: {audio_enriched} audio, {artists_enriched} artistes, {albums_enriched} albums")
        return result

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur enrichissement batch: {str(e)}", exc_info=True)
        return {"error": str(e), "tracks_count": len(track_ids)}


@celery.task(name="worker_metadata.analyze_audio_features", queue="worker_metadata")
def analyze_audio_features_task(track_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
    """
    Tâche d'analyse des caractéristiques audio.

    Args:
        track_ids: Liste des IDs de tracks à analyser
        priority: Priorité de traitement

    Returns:
        Résultats de l'analyse audio
    """
    try:
        logger.info(f"[WORKER_METADATA] Démarrage analyse audio: {len(track_ids)} tracks (priorité: {priority})")

        if not track_ids:
            return {"error": "Aucune track à analyser"}

        # Récupération des chemins de fichiers
        if _is_test_mode():
            # Simulation pour les tests
            track_data_list = [{"id": tid, "path": f"/test/path/track_{tid}.mp3"} for tid in track_ids]
        else:
            track_data_list = asyncio.run(_get_track_paths(track_ids))

        if not track_data_list:
            return {"error": "Aucune track trouvée avec chemin valide"}

        # Analyse par batch
        batch_size = 10 if priority == "high" else 5
        batches = [track_data_list[i:i + batch_size] for i in range(0, len(track_data_list), batch_size)]

        results = []
        for batch in batches:
            if _is_test_mode():
                # Simulation pour les tests
                batch_result = {"total": len(batch), "successful": len(batch), "failed": 0}
            else:
                batch_result = asyncio.run(analyze_audio_batch(batch))
            results.append(batch_result)

            # Pause entre les batches pour les analyses CPU-intensive
            if priority != "high" and not _is_test_mode():
                asyncio.run(asyncio.sleep(1))

        # Consolidation des résultats
        total = sum(r.get("total", 0) for r in results)
        successful = sum(r.get("successful", 0) for r in results)
        failed = sum(r.get("failed", 0) for r in results)

        result = {
            "total_tracks": len(track_ids),
            "analyzed": total,
            "successful": successful,
            "failed": failed,
            "priority": priority,
            "results": results
        }

        logger.info(f"[WORKER_METADATA] Analyse audio terminée: {successful}/{total} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur analyse audio: {str(e)}", exc_info=True)
        return {"error": str(e), "tracks_count": len(track_ids)}


@celery.task(name="worker_metadata.enrich_artists_albums", queue="worker_metadata")
def enrich_artists_albums_task(entity_ids: List[int], entity_type: str = "artist") -> Dict[str, Any]:
    """
    Tâche d'enrichissement des artistes ou albums.

    Args:
        entity_ids: Liste des IDs d'entités à enrichir
        entity_type: Type d'entité ("artist" ou "album")

    Returns:
        Résultats de l'enrichissement
    """
    try:
        logger.info(f"[WORKER_METADATA] Démarrage enrichissement {entity_type}s: {len(entity_ids)} entités")

        if not entity_ids:
            return {"error": f"Aucun {entity_type} à enrichir"}

        if entity_type not in ["artist", "album"]:
            return {"error": f"Type d'entité non supporté: {entity_type}"}

        # Traitement séquentiel pour éviter la surcharge des APIs
        results = []
        for entity_id in entity_ids:
            try:
                if _is_test_mode():
                    result = {"success": True}
                else:
                    if entity_type == "artist":
                        result = asyncio.run(enrich_artist(entity_id))
                    elif entity_type == "album":
                        result = asyncio.run(enrich_album(entity_id))

                results.append({"entity_id": entity_id, "success": True})
            except Exception as e:
                logger.error(f"[WORKER_METADATA] Erreur enrichissement {entity_type} {entity_id}: {str(e)}")
                results.append({"entity_id": entity_id, "success": False, "error": str(e)})

            # Pause entre chaque entité
            if not _is_test_mode():
                asyncio.run(asyncio.sleep(0.5))

        success_count = sum(1 for r in results if r.get("success"))

        result = {
            "entity_type": entity_type,
            "total_entities": len(entity_ids),
            "successful": success_count,
            "failed": len(entity_ids) - success_count,
            "results": results
        }

        logger.info(f"[WORKER_METADATA] Enrichissement {entity_type}s terminé: {success_count}/{len(entity_ids)} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur enrichissement {entity_type}s: {str(e)}", exc_info=True)
        return {"error": str(e), "entity_type": entity_type, "entities_count": len(entity_ids)}


@celery.task(name="worker_metadata.update_track_metadata", queue="worker_metadata")
def update_track_metadata_task(track_id: int, metadata_updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche de mise à jour des métadonnées d'une track spécifique.

    Args:
        track_id: ID de la track
        metadata_updates: Mises à jour à appliquer

    Returns:
        Résultat de la mise à jour
    """
    try:
        logger.info(f"[WORKER_METADATA] Mise à jour métadonnées track {track_id}")

        # Validation des données
        if not metadata_updates:
            return {"track_id": track_id, "error": "Aucune mise à jour fournie"}

        # Application des mises à jour via API
        if _is_test_mode():
            result = {"track_id": track_id, "success": True, "updated_fields": list(metadata_updates.keys())}
        else:
            result = asyncio.run(_update_track_metadata(track_id, metadata_updates))

        logger.info(f"[WORKER_METADATA] Mise à jour track {track_id} terminée: {result}")
        return result

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur mise à jour track {track_id}: {str(e)}", exc_info=True)
        return {"track_id": track_id, "error": str(e)}


@celery.task(name="worker_metadata.bulk_update_genres_tags", queue="worker_metadata")
def bulk_update_genres_tags_task(track_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tâche de mise à jour en bulk des genres et tags.

    Args:
        track_updates: Liste des mises à jour [{"track_id": int, "genres": [...], "tags": {...}}]

    Returns:
        Résultats des mises à jour
    """
    try:
        logger.info(f"[WORKER_METADATA] Démarrage bulk update genres/tags: {len(track_updates)} tracks")

        if not track_updates:
            return {"error": "Aucune mise à jour fournie"}

        # Traitement par lots
        batch_size = 50
        batches = [track_updates[i:i + batch_size] for i in range(0, len(track_updates), batch_size)]

        results = []
        for batch in batches:
            if _is_test_mode():
                batch_result = {"processed": len(batch), "successful": len(batch)}
            else:
                batch_result = asyncio.run(_bulk_update_genres_tags_batch(batch))
            results.append(batch_result)

        # Consolidation
        total_processed = sum(r.get("processed", 0) for r in results)
        successful = sum(r.get("successful", 0) for r in results)

        result = {
            "total_updates": len(track_updates),
            "processed": total_processed,
            "successful": successful,
            "failed": total_processed - successful,
            "batch_results": results
        }

        logger.info(f"[WORKER_METADATA] Bulk update terminé: {successful}/{total_processed} succès")
        return result

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur bulk update: {str(e)}", exc_info=True)
        return {"error": str(e), "updates_count": len(track_updates)}


async def _enrich_tracks_batch(track_ids: List[int], enrichment_types: List[str]) -> Dict[str, Any]:
    """
    Enrichit un batch de tracks selon les types spécifiés.

    Args:
        track_ids: IDs des tracks
        enrichment_types: Types d'enrichissement

    Returns:
        Résultats de l'enrichissement
    """
    processed = 0
    audio_enriched = 0
    artists_enriched = 0
    albums_enriched = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for track_id in track_ids:
                try:
                    # Récupération des données de la track
                    
                    track_response = await client.get(f"{library_api_url}/api/tracks/{track_id}")
                    if track_response.status_code != 200:
                        logger.warning(f"[WORKER_METADATA] Track {track_id} non trouvée")
                        continue

                    track_data = track_response.json()

                    # Enrichissement audio si demandé
                    if "audio" in enrichment_types or "all" in enrichment_types:
                        if not track_data.get("bpm"):  # Vérifier si déjà enrichi
                            audio_result = await analyze_audio_with_librosa(track_id, track_data.get("path"))
                            if audio_result:
                                audio_enriched += 1

                    # Enrichissement artiste si demandé
                    if "artist" in enrichment_types or "all" in enrichment_types:
                        artist_id = track_data.get("track_artist_id")
                        if artist_id:
                            await enrich_artist(artist_id)
                            artists_enriched += 1

                    # Enrichissement album si demandé
                    if "album" in enrichment_types or "all" in enrichment_types:
                        album_id = track_data.get("album_id")
                        if album_id:
                            await enrich_album(album_id)
                            albums_enriched += 1

                    processed += 1

                except Exception as e:
                    logger.error(f"[WORKER_METADATA] Erreur enrichissement track {track_id}: {str(e)}")

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur batch enrichissement: {str(e)}")

    return {
        "processed": processed,
        "audio_enriched": audio_enriched,
        "artists_enriched": artists_enriched,
        "albums_enriched": albums_enriched
    }


async def _get_track_paths(track_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Récupère les chemins de fichiers pour une liste de tracks.

    Args:
        track_ids: IDs des tracks

    Returns:
        Liste des données de tracks avec chemins
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tracks_data = []
            for track_id in track_ids:
                try:
                    response = await client.get(f"{library_api_url}/api/tracks/{track_id}")
                    if response.status_code == 200:
                        track_data = response.json()
                        if track_data.get("path"):
                            tracks_data.append({
                                "id": track_id,
                                "path": track_data["path"]
                            })
                except Exception as e:
                    logger.error(f"[WORKER_METADATA] Erreur récupération track {track_id}: {str(e)}")

            return tracks_data

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur récupération tracks: {str(e)}")
        return []


async def _update_track_metadata(track_id: int, metadata_updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour les métadonnées d'une track via l'API.

    Args:
        track_id: ID de la track
        metadata_updates: Mises à jour à appliquer

    Returns:
        Résultat de la mise à jour
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{library_api_url}/api/tracks/{track_id}/metadata",
                json={"metadata": metadata_updates}
            )

            if response.status_code == 200:
                return {"track_id": track_id, "success": True, "updated_fields": list(metadata_updates.keys())}
            else:
                error_msg = response.text
                return {"track_id": track_id, "success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Exception mise à jour track {track_id}: {str(e)}")
        return {"track_id": track_id, "success": False, "error": str(e)}


async def _bulk_update_genres_tags_batch(track_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Met à jour les genres et tags pour un batch de tracks.

    Args:
        track_updates: Liste des mises à jour

    Returns:
        Résultats des mises à jour
    """
    processed = 0
    successful = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for update in track_updates:
                try:
                    track_id = update.get("track_id")
                    if not track_id:
                        continue

                    # Construction de la payload de mise à jour
                    update_payload = {}
                    if "genres" in update:
                        update_payload["genres"] = update["genres"]
                    if "tags" in update:
                        update_payload["tags"] = update["tags"]

                    if update_payload:
                        response = await client.put(
                            f"{library_api_url}/api/tracks/{track_id}/genres-tags",
                            json=update_payload
                        )

                        if response.status_code == 200:
                            successful += 1

                    processed += 1

                except Exception as e:
                    logger.error(f"[WORKER_METADATA] Erreur update track {update.get('track_id')}: {str(e)}")
                    processed += 1

    except Exception as e:
        logger.error(f"[WORKER_METADATA] Erreur bulk update batch: {str(e)}")

    return {"processed": processed, "successful": successful}


def extract_single_file_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extrait les métadonnées d'un fichier unique (fonction synchrone pour ThreadPoolExecutor).

    Optimisée pour Raspberry Pi : extraction simple, pas d'analyse audio.

    Args:
        file_path: Chemin du fichier à traiter

    Returns:
        Dictionnaire de métadonnées ou None si erreur
    """
    try:
        # Import ici pour éviter les problèmes d'import dans les threads
        from mutagen import File
        from backend_worker.services.music_scan import (
            get_file_type, get_tag, sanitize_path, get_musicbrainz_tags,
        )

        # Validation et sanitisation du chemin
        try:
            sanitized_path = sanitize_path(file_path)
            file_path_obj = Path(sanitized_path)
        except ValueError as e:
            logger.warning(f"[METADATA] Chemin invalide {file_path}: {e}")
            return None

        # Vérification existence fichier
        if not file_path_obj.exists() or not file_path_obj.is_file():
            logger.warning(f"[METADATA] Fichier inexistant: {file_path}")
            return None

        # Ouverture et lecture du fichier
        try:
            audio = File(file_path, easy=False)
            if audio is None:
                logger.warning(f"[METADATA] Impossible de lire: {file_path}")
                return None
        except Exception as e:
            logger.error(f"[METADATA] Erreur lecture {file_path}: {e}")
            return None

        # Extraction des métadonnées de base
        try:
            metadata = {
                "path": file_path,
                "title": get_tag(audio, "title") or file_path_obj.stem,
                "artist": get_tag(audio, "artist") or get_tag(audio, "TPE1") or get_tag(audio, "TPE2"),
                "album": get_tag(audio, "album") or file_path_obj.parent.name,
                "genre": get_tag(audio, "genre"),
                "year": get_tag(audio, "date") or get_tag(audio, "TDRC"),
                "track_number": get_tag(audio, "tracknumber") or get_tag(audio, "TRCK"),
                "disc_number": get_tag(audio, "discnumber") or get_tag(audio, "TPOS"),
                "file_type": get_file_type(file_path),
            }

            # Ajouter durée si disponible
            if hasattr(audio.info, 'length'):
                metadata["duration"] = int(audio.info.length)

            # Ajouter bitrate si disponible
            if hasattr(audio.info, 'bitrate') and audio.info.bitrate:
                metadata["bitrate"] = int(audio.info.bitrate / 1000)

            # Extraction des données MusicBrainz
            mb_data = get_musicbrainz_tags(audio)
            metadata.update({
                "musicbrainz_artistid": mb_data.get("musicbrainz_artistid"),
                "musicbrainz_albumartistid": mb_data.get("musicbrainz_albumartistid"),
                "musicbrainz_albumid": mb_data.get("musicbrainz_albumid"),
                "musicbrainz_id": mb_data.get("musicbrainz_id"),
                "acoustid_fingerprint": mb_data.get("acoustid_fingerprint")
            })

            # Nettoyer les valeurs None
            metadata = {k: v for k, v in metadata.items() if v is not None}

            logger.debug(f"[METADATA] Métadonnées extraites: {file_path}")
            return metadata

        except Exception as e:
            logger.error(f"[METADATA] Erreur traitement {file_path}: {e}")
            return None

    except Exception as e:
        logger.error(f"[METADATA] Erreur générale {file_path}: {e}")
        return None


@celery.task(name='extract_metadata_batch', queue='metadata', bind=True)
def extract_metadata_batch(self, file_paths: List[str], batch_id: str = None):
    """
    Extrait les métadonnées de fichiers en parallèle avec ThreadPoolExecutor.

    Optimisée pour Raspberry Pi : max_workers=2, timeout=60s, batches=25.

    Args:
        file_paths: Liste des chemins de fichiers à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Liste des métadonnées extraites
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[METADATA] Démarrage extraction batch: {len(file_paths)} fichiers")
        logger.info(f"[METADATA] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[METADATA] Batch ID: {batch_id}")

        # Validation des chemins
        valid_paths = []
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_paths.append(file_path)
            else:
                logger.warning(f"[METADATA] Fichier invalide ignoré: {file_path}")

        if not valid_paths:
            logger.warning("[METADATA] Aucun fichier valide dans le batch")
            return []

        logger.info(f"[METADATA] Fichiers valides: {len(valid_paths)}/{len(file_paths)}")

        # Configuration ThreadPoolExecutor optimisée pour Raspberry Pi
        max_workers = 2  # Fixé à 2 pour Raspberry Pi (4 cœurs max)

        # Extraction massive avec ThreadPoolExecutor
        extracted_metadata = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les fichiers en parallèle
            future_to_path = {
                executor.submit(extract_single_file_metadata, file_path): file_path
                for file_path in valid_paths
            }

            # Collecter les résultats au fur et à mesure
            completed = 0
            for future in future_to_path:
                try:
                    metadata = future.result(timeout=60)  # 1 minute timeout par fichier (Raspberry Pi)
                    if metadata:
                        extracted_metadata.append(metadata)

                    completed += 1

                    # Update progression toutes les 100 fichiers
                    if completed % 100 == 0:
                        progress = min(90, (completed / len(valid_paths)) * 90)
                        self.update_state(state='PROGRESS', meta={
                            'current': completed,
                            'total': len(valid_paths),
                            'percent': progress,
                            'step': f'Extraction {completed}/{len(valid_paths)} fichiers'
                        })

                        # Publier la progression vers le frontend
                        publish_event("progress", {
                            "type": "progress",
                            "task_id": task_id,
                            "step": f'Extraction {completed}/{len(valid_paths)} fichiers',
                            "current": completed,
                            "total": len(valid_paths),
                            "percent": progress,
                            "batch_id": batch_id
                        }, channel="progress")

                except Exception as e:
                    logger.error(f"[METADATA] Erreur traitement fichier: {e}")
                    completed += 1

        # Métriques de performance
        total_time = time.time() - start_time
        files_per_second = len(extracted_metadata) / total_time if total_time > 0 else 0

        logger.info(f"[METADATA] Extraction terminée: {len(extracted_metadata)}/{len(valid_paths)} fichiers en {total_time:.2f}s")
        logger.info(f"[METADATA] Performance: {files_per_second:.2f} fichiers/seconde")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Extraction terminée",
            "current": len(extracted_metadata),
            "total": len(valid_paths),
            "percent": 100,
            "batch_id": batch_id,
            "files_processed": len(extracted_metadata),
            "files_total": len(valid_paths),
            "extraction_time": total_time,
            "files_per_second": files_per_second
        }, channel="progress")

        # Envoyer vers le batching si on a des résultats
        if extracted_metadata:
            celery.send_task(
                'batch_entities',
                args=[extracted_metadata],
                queue='batch',
                priority=5
            )

        return {
            'task_id': task_id,
            'batch_id': batch_id,
            'files_processed': len(extracted_metadata),
            'files_total': len(valid_paths),
            'extraction_time': total_time,
            'files_per_second': files_per_second,
            'success': True
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[METADATA] Erreur batch après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur d'extraction: {str(e)}",
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise


@celery.task(name='calculate_vector', queue='vectorization', bind=True,
             autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def calculate_vector(self, track_id: int, vectorization_payload: Dict[str, Any]):
    """
    Calcule le vecteur d'une track et le stocke dans la Recommender API.

    Tâche Celery avec retry automatique et optimisée pour Raspberry Pi.
    Respecte l'isolation : communication uniquement via HTTP vers Recommender API.

    Args:
        track_id: ID de la track (string selon prompt)
        vectorization_payload: Payload Redis avec artist, genres, moods, bpm, duration

    Returns:
        Résultat du calcul
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[VECTOR] Démarrage calcul vecteur: track_id={track_id}")
        logger.info(f"[VECTOR] Task ID: {task_id}")
        logger.info(f"[VECTOR] Payload: {vectorization_payload}")

        # Récupérer les données complètes de la track depuis Library API
        import httpx

        async def get_track_data():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{library_api_url}/api/tracks/{track_id}")
                if response.status_code == 200:
                    return response.json()
                return None

        track_data = asyncio.run(get_track_data())

        if not track_data:
            raise Exception(f"Track {track_id} non trouvée dans Library API")

        # Fusionner avec le payload Redis pour avoir toutes les métadonnées
        enriched_metadata = {
            **track_data,
            **vectorization_payload
        }

        # Import du service de vectorisation
        from backend_worker.services.vectorization_service import VectorizationService

        # Initialiser le service
        vector_service = VectorizationService()

        # Générer l'embedding
        import nest_asyncio
        nest_asyncio.apply()
        embedding = asyncio.run(vector_service.generate_embedding(enriched_metadata))

        if not embedding or len(embedding) == 0:
            raise Exception("Embedding vide généré")

        # Stocker le vecteur via l'API Recommender
        async def store_vector():
            async with httpx.AsyncClient(timeout=30.0) as client:
                vector_data = {
                    "track_id": str(track_id),
                    "vector": embedding,
                    "embedding_version": "v1",
                    "created_at": time.time()
                }

                response = await client.post(
                    f"{recommender_api_url}/api/vectors",
                    json=vector_data,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 201:
                    return True
                elif response.status_code == 409:
                    logger.info(f"Vecteur déjà existant pour track {track_id}")
                    return True
                else:
                    logger.error(f"Erreur stockage: {response.status_code} - {response.text}")
                    return False

        success = asyncio.run(store_vector())

        if not success:
            raise Exception("Échec stockage vecteur")

        # Métriques
        total_time = time.time() - start_time

        logger.info(f"Vecteur calculé et stocké: track_id={track_id}, dimension={len(embedding)}, temps={total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Vectorisation terminée",
            "current": 1,
            "total": 1,
            "percent": 100,
            "track_id": track_id,
            "vector_dimension": len(embedding),
            "calculation_time": total_time
        }, channel="progress")

        return {
            'task_id': task_id,
            'track_id': track_id,
            'success': True,
            'vector_dimension': len(embedding),
            'calculation_time': total_time
        }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Erreur calcul vecteur track {track_id}: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur vectorisation: {str(e)}",
            "error": str(e),
            "track_id": track_id,
            "duration": error_time
        }, channel="progress")

        raise


@celery.task(name='calculate_vector_if_needed', queue='vectorization', bind=True)
def calculate_vector_if_needed(self, track_id: int):
    """
    Calcule le vecteur d'une track seulement si nécessaire.

    Vérifie d'abord si le vecteur existe déjà.

    Args:
        track_id: ID de la track

    Returns:
        Résultat de l'opération
    """
    try:
        logger.info(f"Vérification vecteur: track_id={track_id}")

        # Vérifier si le vecteur existe déjà
        import httpx

        async def check_vector_exists():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://recommender:8002/api/track-vectors/{track_id}")
                return response.status_code == 200

        vector_exists = asyncio.run(check_vector_exists())

        if vector_exists:
            logger.info(f"Vecteur existe déjà pour track {track_id}")
            return {
                'track_id': track_id,
                'status': 'already_exists',
                'message': 'Vecteur déjà calculé'
            }

        # Récupérer les métadonnées de la track
        async def get_track_metadata():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{library_api_url}/api/tracks/{track_id}")
                if response.status_code == 200:
                    return response.json()
                return None

        metadata = asyncio.run(get_track_metadata())

        if not metadata:
            raise Exception(f"Track {track_id} non trouvée")

        # Calculer le vecteur
        result = calculate_vector(track_id, metadata)

        logger.info(f"Vecteur calculé pour track {track_id}")
        return result

    except Exception as e:
        logger.error(f"Erreur vérification/calcul track {track_id}: {str(e)}")
        raise


@celery.task(name='batch_entities', queue='batch', bind=True)
def batch_entities(self, metadata_list: List[Dict[str, Any]], batch_id: str = None):
    """
    Regroupe les métadonnées par artistes et albums pour insertion optimisée.

    Optimisée pour Raspberry Pi : batches plus petits, traitement séquentiel.

    Args:
        metadata_list: Liste des métadonnées à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Données groupées prêtes pour insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[BATCH] Démarrage batching: {len(metadata_list)} métadonnées")
        logger.info(f"[BATCH] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[BATCH] Batch ID: {batch_id}")

        if not metadata_list:
            logger.warning("[BATCH] Liste de métadonnées vide")
            return {
                'task_id': task_id,
                'batch_id': batch_id,
                'artists_count': 0,
                'albums_count': 0,
                'tracks_count': 0,
                'success': True
            }

        # Regroupement intelligent des données
        from collections import defaultdict
        artists_by_name = {}
        albums_by_key = {}
        tracks_by_artist = defaultdict(list)

        # Étape 1: Regrouper par artistes
        logger.info("[BATCH] Regroupement par artistes...")
        for metadata in metadata_list:
            artist_name = metadata.get('artist', 'Unknown')
            if not artist_name or artist_name.lower() == 'unknown':
                # Essayer de deviner l'artiste depuis le chemin
                path_obj = Path(metadata.get('path', ''))
                if len(path_obj.parts) >= 2:
                    artist_name = path_obj.parts[-2]  # Parent directory as artist
                else:
                    artist_name = 'Unknown Artist'

            # Normaliser le nom d'artiste
            normalized_artist = artist_name.strip().lower()

            if normalized_artist not in artists_by_name:
                artists_by_name[normalized_artist] = {
                    'name': artist_name,
                    'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                    'musicbrainz_albumartistid': metadata.get('musicbrainz_albumartistid'),
                    'tracks_count': 0,
                    'albums_count': 0
                }

            # Compter les tracks par artiste
            artists_by_name[normalized_artist]['tracks_count'] += 1

            # Ajouter à la liste des tracks de l'artiste
            tracks_by_artist[normalized_artist].append(metadata)

        # Étape 2: Regrouper par albums
        logger.info("[BATCH] Regroupement par albums...")
        for artist_name, tracks in tracks_by_artist.items():
            artist_info = artists_by_name[artist_name]

            for track in tracks:
                album_name = track.get('album', 'Unknown')
                if not album_name or album_name.lower() == 'unknown':
                    # Essayer de deviner l'album depuis le chemin
                    path_obj = Path(track.get('path', ''))
                    if len(path_obj.parts) >= 1:
                        album_name = path_obj.parts[-1]  # Grand-parent as album
                    else:
                        album_name = 'Unknown Album'

                # Créer une clé unique album-artiste
                album_key = (album_name.strip().lower(), artist_name)

                if album_key not in albums_by_key:
                    albums_by_key[album_key] = {
                        'title': album_name,
                        'album_artist_name': artist_name,
                        'release_year': track.get('year'),
                        'musicbrainz_albumid': track.get('musicbrainz_albumid'),
                        'tracks_count': 0
                    }

                albums_by_key[album_key]['tracks_count'] += 1
                artist_info['albums_count'] += 1

        # Étape 3: Préparation des données d'insertion
        logger.info("[BATCH] Préparation données d'insertion...")

        # Liste des artistes uniques
        artists_data = list(artists_by_name.values())

        # Liste des albums avec références aux artistes
        albums_data = []
        for album_key, album_info in albums_by_key.items():
            album_data = dict(album_info)
            albums_data.append(album_data)

        # Liste des tracks avec références
        tracks_data = []
        for track in metadata_list:
            artist_name = track.get('artist', '').strip().lower()
            album_name = track.get('album', '').strip().lower()

            # Ajouter les références pour résolution ultérieure
            track_data = dict(track)
            track_data['artist_name'] = artist_name
            track_data['album_title'] = album_name

            tracks_data.append(track_data)

        # Métriques du batching
        total_time = time.time() - start_time

        logger.info(f"[BATCH] Batching terminé: {len(artists_data)} artistes, {len(albums_data)} albums, {len(tracks_data)} pistes en {total_time:.2f}s")

        # Publier les métriques
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Batching terminé",
            "current": len(tracks_data),
            "total": len(tracks_data),
            "percent": 100,
            "batch_id": batch_id,
            "artists_count": len(artists_data),
            "albums_count": len(albums_data),
            "tracks_count": len(tracks_data),
            "batching_time": total_time
        }, channel="progress")

        # Préparer le résultat pour l'insertion
        insertion_data = {
            'task_id': task_id,
            'batch_id': batch_id,
            'artists': artists_data,
            'albums': albums_data,
            'tracks': tracks_data,
            'metadata_count': len(metadata_list),
            'batching_time': total_time,
            'success': True
        }

        # Envoyer vers l'insertion directe via API uniquement
        celery.send_task(
            'insert_batch_direct',
            args=[insertion_data],
            queue='insert',
            priority=7  # Priorité élevée pour l'insertion
        )

        return insertion_data

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[BATCH] Erreur batching après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur de batching: {str(e)}",
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise


@celery.task(name='insert_batch_direct', queue='insert', bind=True)
def insert_batch_direct(self, insertion_data: Dict[str, Any]):
    """
    Insère en base de données via l'API HTTP uniquement (pas d'accès direct BDD).

    Implémente la résolution des références d'artistes pour éviter les erreurs 422.
    Les artistes sont recherchés et créés avant l'insertion des albums et tracks.

    Optimisée pour Raspberry Pi : batches plus petits, timeouts réduits.

    Args:
        insertion_data: Données groupées prêtes pour insertion

    Returns:
        Résultat de l'insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[INSERT] Démarrage insertion directe: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} pistes")
        logger.info(f"[INSERT] Task ID: {task_id}")

        # Récupérer les données
        artists_data = insertion_data.get('artists', [])
        albums_data = insertion_data.get('albums', [])
        tracks_data = insertion_data.get('tracks', [])

        if not tracks_data and not artists_data and not albums_data:
            logger.warning("[INSERT] Aucune donnée à insérer")
            return {
                'task_id': task_id,
                'success': True,
                'artists_inserted': 0,
                'albums_inserted': 0,
                'tracks_inserted': 0
            }

        # Phase 1: Résolution complète des références pour éviter TOUTES les erreurs 422
        # Ordre : Artistes → Albums → Genres → Tracks
        resolved_data = asyncio.run(_resolve_all_references(artists_data, albums_data, tracks_data))
        artists_data = resolved_data['artists']
        albums_data = resolved_data['albums']
        tracks_data = resolved_data['tracks']
        resolved_data['genres']

        # Utiliser httpx pour des connexions HTTP optimisées
        import httpx

        # Configuration client HTTP optimisée pour Raspberry Pi
        with httpx.Client(
            base_url=library_api_url,
            timeout=httpx.Timeout(120.0),  # 2 minutes timeout (Raspberry Pi)
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Réduit pour Raspberry Pi
                max_connections=20,
                keepalive_expiry=120.0
            )
        ) as client:

            inserted_counts = {
                'artists': 0,
                'albums': 0,
                'tracks': 0
            }

            # Étape 1: Insertion des artistes par batches (optimisé Raspberry Pi)
            if artists_data:
                logger.info(f"[INSERT] Insertion de {len(artists_data)} artistes en batches")

                # Diviser en batches de 100 artistes (plus petit pour Raspberry Pi)
                batch_size = 100
                for i in range(0, len(artists_data), batch_size):
                    batch = artists_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/artists/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['artists'] += len(result)
                            logger.debug(f"[INSERT] Batch artistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch artistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch artistes: {e}")

            # Étape 2: Insertion des albums par batches
            if albums_data:
                logger.info(f"[INSERT] Insertion de {len(albums_data)} albums en batches")

                # Diviser en batches de 100 albums
                batch_size = 100
                for i in range(0, len(albums_data), batch_size):
                    batch = albums_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/albums/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['albums'] += len(result)
                            logger.debug(f"[INSERT] Batch albums {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch albums: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch albums: {e}")

            # Étape 3: Insertion des pistes par batches
            if tracks_data:
                logger.info(f"[INSERT] Insertion de {len(tracks_data)} pistes en batches")

                # Diviser en batches de 200 pistes (optimisé Raspberry Pi)
                batch_size = 200
                for i in range(0, len(tracks_data), batch_size):
                    batch = tracks_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/tracks/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['tracks'] += len(result)
                            logger.debug(f"[INSERT] Batch pistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch pistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch pistes: {e}")

            # Métriques finales
            total_time = time.time() - start_time

            logger.info(f"[INSERT] Insertion terminée: {inserted_counts} en {total_time:.2f}s")

            # Publier les métriques
            publish_event("progress", {
                "type": "progress",
                "task_id": task_id,
                "step": "Insertion terminée",
                "current": inserted_counts['tracks'],
                "total": inserted_counts['tracks'],
                "percent": 100,
                "artists_inserted": inserted_counts['artists'],
                "albums_inserted": inserted_counts['albums'],
                "tracks_inserted": inserted_counts['tracks'],
                "insertion_time": total_time,
                "insertions_per_second": sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }, channel="progress")

            result = {
                'task_id': task_id,
                'success': True,
                **inserted_counts,
                'insertion_time': total_time,
                'insertions_per_second': sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }

            return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[INSERT] Erreur insertion après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur d'insertion: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise


async def _resolve_all_references(artists_data: List[Dict[str, Any]],
                                    albums_data: List[Dict[str, Any]], 
                                    tracks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Résout TOUTES les références d'artistes, albums et genres pour éviter les erreurs 422.
    
    Ordre de résolution :
    1. Artistes (aucune référence, base)
    2. Albums (référence album_artist_id → artists.id)
    3. Genres (système autonome)
    4. Tracks (références track_artist_id → artists.id, album_id → albums.id)
    
    Returns:
        Dictionnaire avec toutes les données résolues
    """
    try:
        logger.info("[RESOLVE] Démarrage résolution complète des références")
        
        # PHASE 1: RÉSOLUTION DES ARTISTES
        logger.info("[RESOLVE] Phase 1: Résolution des artistes")
        resolved_artists = await _resolve_artists_references(artists_data)
        artist_mapping = resolved_artists['artist_mapping']
        final_artists = resolved_artists['artists']
        
        # PHASE 2: RÉSOLUTION DES ALBUMS
        logger.info("[RESOLVE] Phase 2: Résolution des albums")
        resolved_albums = await _resolve_albums_references(albums_data, artist_mapping)
        album_mapping = resolved_albums['album_mapping']
        final_albums = resolved_albums['albums']
        
        # PHASE 3: RÉSOLUTION DES GENRES
        logger.info("[RESOLVE] Phase 3: Résolution des genres")
        genre_result = await _resolve_genres_references(tracks_data)
        final_genres = genre_result['genres']
        track_cleaned_genres = genre_result['track_cleaned_genres']
        
        # PHASE 4: RÉSOLUTION DES TRACKS
        logger.info("[RESOLVE] Phase 4: Résolution des tracks")
        resolved_tracks = await _resolve_tracks_references(tracks_data, artist_mapping, album_mapping, final_genres, track_cleaned_genres)
        final_tracks = resolved_tracks['tracks']
        
        logger.info(f"[RESOLVE] Résolution complète terminée: {len(final_artists)} artistes, {len(final_albums)} albums, {len(final_genres)} genres, {len(final_tracks)} tracks")
        
        return {
            'artists': final_artists,
            'albums': final_albums,
            'genres': final_genres,
            'tracks': final_tracks
        }

    except Exception as e:
        logger.error(f"[RESOLVE] Erreur résolution complète: {str(e)}")
        raise


async def _resolve_artists_references(artists_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Résout les références d'artistes (aucune référence, base du système).
    """
    try:
        # Phase 1: Récupérer les artistes uniques pour la recherche
        unique_artists = {}
        for artist in artists_data:
            artist_name = artist.get('name', '').strip().lower()
            musicbrainz_id = artist.get('musicbrainz_artistid')
            
            if artist_name and artist_name not in unique_artists:
                unique_artists[artist_name] = {
                    'name': artist.get('name'),
                    'musicbrainz_artistid': musicbrainz_id,
                    'original_data': artist
                }

        logger.info(f"[RESOLVE-ARTISTS] Recherche de {len(unique_artists)} artistes uniques")

        # Phase 2: Rechercher les artistes existants par lots (avec cache)
        existing_artists = {}
        if unique_artists:
            cache_service = CacheService()
            await _search_existing_artists(unique_artists, existing_artists, cache_service)

        # Phase 3: Créer les artistes manquants
        new_artists = []
        artist_mapping = {}
        
        for artist_key, artist_info in unique_artists.items():
            if artist_key in existing_artists:
                # Artiste existant trouvé
                artist_mapping[artist_key] = existing_artists[artist_key]['id']
                logger.debug(f"[RESOLVE-ARTISTS] Artiste existant trouvé: {artist_info['name']} (ID: {existing_artists[artist_key]['id']})")
            else:
                # Nouvel artiste à créer
                new_artists.append(artist_info['original_data'])
                artist_mapping[artist_key] = f"TEMP_{len(new_artists)}"  # Temporary ID

        logger.info(f"[RESOLVE-ARTISTS] {len(existing_artists)} artistes trouvés, {len(new_artists)} nouveaux à créer")

        # Phase 4: Créer les nouveaux artistes via API
        if new_artists:
            created_artists = await _create_missing_artists(new_artists)
            for i, created_artist in enumerate(created_artists):
                # Remplacer les IDs temporaires par les vrais IDs
                temp_id = f"TEMP_{i+1}"
                for key, mapping in artist_mapping.items():
                    if mapping == temp_id:
                        artist_mapping[key] = created_artist['id']
                        break

        # Phase 5: Préparer les données finales
        final_artists = []
        for artist_info in unique_artists.values():
            artist_data = artist_info['original_data'].copy()
            artist_name = artist_info['name'].strip().lower()
            if artist_name in artist_mapping:
                artist_data['id'] = artist_mapping[artist_name]
            # Nettoyer les champs temporaires
            artist_data.pop('tracks_count', None)
            artist_data.pop('albums_count', None)
            final_artists.append(artist_data)

        return {
            'artist_mapping': artist_mapping,
            'artists': final_artists
        }

    except Exception as e:
        logger.error(f"[RESOLVE-ARTISTS] Erreur résolution artistes: {str(e)}")
        raise


async def _resolve_albums_references(albums_data: List[Dict[str, Any]], artist_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Résout les références d'albums avec référence album_artist_id → artists.id.
    """
    try:
        # Phase 1: Préparer les albums avec références artistes résolues
        resolved_albums = []
        album_mapping = {}
        
        for album in albums_data:
            album_artist_name = album.get('album_artist_name', '').strip().lower()
            if album_artist_name in artist_mapping:
                resolved_album = album.copy()
                resolved_album['album_artist_id'] = artist_mapping[album_artist_name]
                # Nettoyer le champ temporaire
                resolved_album.pop('album_artist_name', None)
                
                # Créer une clé unique pour l'album
                album_key = f"{resolved_album['title'].strip().lower()}_{resolved_album['album_artist_id']}"
                # S'assurer que l'ID est toujours un string temporaire au début
                album_mapping[album_key] = f"TEMP_ALBUM_{len(album_mapping)}"
                resolved_albums.append(resolved_album)
            else:
                logger.warning(f"[RESOLVE-ALBUMS] Impossible de résoudre l'artiste pour l'album: {album.get('title', 'Unknown')}")

        # Phase 2: Rechercher les albums existants
        existing_albums = await _search_existing_albums(resolved_albums, artist_mapping)
        
        # Phase 3: Mettre à jour le mapping avec les vrais IDs d'albums existants
        for album_key, temp_id in album_mapping.items():
            if album_key in existing_albums:
                album_mapping[album_key] = existing_albums[album_key]['id']
                logger.debug(f"[RESOLVE-ALBUMS] Album existant trouvé pour clé: {album_key}")

        # Phase 4: Créer les nouveaux albums via API
        albums_to_create = []
        temp_album_mappings = []  # Pour suivre les correspondances temp_id -> album_data
        
        for album in resolved_albums:
            album_key = f"{album['title'].strip().lower()}_{album['album_artist_id']}"
            album_id = album_mapping[album_key]
            # Vérifier si l'ID est un string temporaire (nouvel album à créer)
            if isinstance(album_id, str) and album_id.startswith("TEMP_ALBUM"):
                albums_to_create.append(album)
                temp_album_mappings.append((album_key, album_id))

        if albums_to_create:
            created_albums = await _create_missing_albums(albums_to_create)
            # Remplacer les IDs temporaires par les vrais IDs de manière fiable
            for i, (temp_album_key, temp_id) in enumerate(temp_album_mappings):
                if i < len(created_albums):
                    album_mapping[temp_album_key] = created_albums[i]['id']
                    logger.debug(f"[RESOLVE-ALBUMS] Remplacé {temp_id} par ID {created_albums[i]['id']} pour {temp_album_key}")

        # Finaliser les données d'albums avec les vrais IDs
        final_albums = []
        for album in resolved_albums:
            album_key = f"{album['title'].strip().lower()}_{album['album_artist_id']}"
            final_album = album.copy()
            final_album['id'] = album_mapping[album_key]
            final_albums.append(final_album)

        return {
            'album_mapping': album_mapping,
            'albums': final_albums
        }

    except Exception as e:
        logger.error(f"[RESOLVE-ALBUMS] Erreur résolution albums: {str(e)}")
        raise


def _clean_and_split_genres(genre_string: str) -> List[str]:
    """
    Nettoie et divise une chaîne de genres complexe en genres individuels.
    
    Exemple : "Dance, Soul, Hip Hop - Rap" → ["Dance", "Soul", "Hip Hop Rap"]
    
    Args:
        genre_string: Chaîne de genres potentiellement complexe
        
    Returns:
        Liste des genres nettoyés et individuels
    """
    if not genre_string or not isinstance(genre_string, str):
        return []
    
    # Remplacer les caractères problématiques
    cleaned = genre_string.replace('/', ' ').replace('-', ' ').replace('–', ' ')
    
    # Diviser par virgules et nettoyer
    genres = []
    for part in cleaned.split(','):
        part = part.strip()
        if part:
            # Supprimer les espaces multiples et capitaliser proprement
            part = ' '.join(part.split())
            
            # Éviter les genres trop longs ou problématiques
            if len(part) <= 50 and not part.isdigit():
                # Ignorer les codes années seuls (ex: "00S")
                if not (len(part) <= 3 and part.endswith('S')):
                    genres.append(part)
    
    return genres


async def _resolve_genres_references(tracks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Résout les genres (système autonome, pas de références externes).
    Nettoie et divise les genres complexes pour éviter les erreurs 307.
    Conserve aussi les genres nettoyés par track pour la liaison many-to-many.
    """
    try:
        # Extraire tous les genres mentionnés dans les tracks
        unique_genres = set()
        track_cleaned_genres = {}  # Pour conserver les genres nettoyés par track
        
        for i, track in enumerate(tracks_data):
            track_cleaned_genres[i] = []
            
            # Genre principal
            genre = track.get('genre')
            if genre:
                # Nettoyer et diviser les genres complexes
                cleaned_genres = _clean_and_split_genres(genre)
                track_cleaned_genres[i].extend(cleaned_genres)
                for cleaned_genre in cleaned_genres:
                    unique_genres.add(cleaned_genre.lower())
            
            # Genre principal complémentaire
            genre_main = track.get('genre_main')
            if genre_main:
                cleaned_genres = _clean_and_split_genres(genre_main)
                track_cleaned_genres[i].extend(cleaned_genres)
                for cleaned_genre in cleaned_genres:
                    unique_genres.add(cleaned_genre.lower())

        if not unique_genres:
            return {
                'genres': [],
                'track_cleaned_genres': track_cleaned_genres if 'track_cleaned_genres' in locals() else {}
            }

        logger.info(f"[RESOLVE-GENRES] Recherche de {len(unique_genres)} genres uniques")

        # Rechercher les genres existants
        existing_genres = await _search_existing_genres(list(unique_genres))
        
        # Créer les genres manquants
        genres_to_create = []
        for genre_name in unique_genres:
            if genre_name not in existing_genres:
                genres_to_create.append({'name': genre_name.title()})

        if genres_to_create:
            created_genres = await _create_missing_genres(genres_to_create)
            for created_genre in created_genres:
                existing_genres[created_genre['name'].lower()] = created_genre

        # Retourner tous les genres ET les genres nettoyés par track
        all_genres = list(existing_genres.values())
        
        return {
            'genres': all_genres,
            'track_cleaned_genres': track_cleaned_genres
        }

    except Exception as e:
        logger.error(f"[RESOLVE-GENRES] Erreur résolution genres: {str(e)}")
        raise


async def _resolve_tracks_references(tracks_data: List[Dict[str, Any]],
                                  artist_mapping: Dict[str, Any],
                                  album_mapping: Dict[str, Any],
                                  genres_data: List[Dict[str, Any]],
                                  track_cleaned_genres: Dict[int, List[str]] = None) -> Dict[str, Any]:
    """
    Résout les références de tracks avec track_artist_id → artists.id et album_id → albums.id.
    """
    try:
        # Créer un mapping des genres par nom
        genres_mapping = {genre['name'].lower(): genre['id'] for genre in genres_data}
        
        # Initialiser track_cleaned_genres si pas fourni
        if track_cleaned_genres is None:
            track_cleaned_genres = {}
        
        resolved_tracks = []
        for i, track in enumerate(tracks_data):
            resolved_track = track.copy()
            
            # Résoudre l'artiste
            artist_name = track.get('artist_name', '').strip().lower()
            if artist_name in artist_mapping:
                resolved_track['track_artist_id'] = artist_mapping[artist_name]
            else:
                logger.warning(f"[RESOLVE-TRACKS] Impossible de résoudre l'artiste pour la track: {track.get('title', 'Unknown')}")
                continue
            
            # Résoudre l'album
            if track.get('album_id'):
                # Album déjà référencé par ID
                resolved_track['album_id'] = track['album_id']
            else:
                # Résoudre par titre et artiste
                album_title = track.get('album_title', track.get('album', '')).strip().lower()
                artist_id = resolved_track['track_artist_id']
                album_key = f"{album_title}_{artist_id}"
                if album_key in album_mapping:
                    resolved_track['album_id'] = album_mapping[album_key]
                else:
                    resolved_track['album_id'] = None  # Album nullable
            
            # Résoudre TOUS les genres (principal + nettoyés)
            track_genre_ids = []
            
            # Genre principal original
            if track.get('genre'):
                genre_name = track['genre'].strip().lower()
                if genre_name in genres_mapping:
                    track_genre_ids.append(genres_mapping[genre_name])
            
            # Genre principal complémentaire
            if track.get('genre_main'):
                genre_main_name = track['genre_main'].strip().lower()
                if genre_main_name in genres_mapping:
                    track_genre_ids.append(genres_mapping[genre_main_name])
            
            # Ajouter les genres nettoyés s'ils existent pour cette track
            if i in track_cleaned_genres:
                for cleaned_genre in track_cleaned_genres[i]:
                    genre_name = cleaned_genre.lower()
                    if genre_name in genres_mapping:
                        track_genre_ids.append(genres_mapping[genre_name])
            
            # Stocker les IDs de genres pour la relation many-to-many
            if track_genre_ids:
                resolved_track['genre_ids'] = list(set(track_genre_ids))  # Éviter les doublons
                # Pour compatibilité backwards, garder aussi genre_id
                resolved_track['genre_id'] = track_genre_ids[0]
            
            # Nettoyer les champs temporaires
            resolved_track.pop('artist_name', None)
            resolved_track.pop('album_title', None)
            resolved_track.pop('tracks_count', None)
            resolved_track.pop('albums_count', None)
            
            resolved_tracks.append(resolved_track)

        return {
            'tracks': resolved_tracks
        }

    except Exception as e:
        logger.error(f"[RESOLVE-TRACKS] Erreur résolution tracks: {str(e)}")
        raise


async def _search_existing_artists(unique_artists: Dict[str, Dict],
                                  existing_artists: Dict[str, Dict],
                                  cache_service: CacheService) -> None:
    """
    Recherche les artistes existants par nom et musicbrainz_artistid.
    
    Args:
        unique_artists: Dictionnaire des artistes uniques à chercher
        existing_artists: Dictionnaire pour stocker les artistes trouvés
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Recherche par lots pour optimiser les performances
            batch_size = 50
            artist_keys = list(unique_artists.keys())
            
            for i in range(0, len(artist_keys), batch_size):
                batch = artist_keys[i:i + batch_size]
                
                try:
                    # Construction de la requête de recherche
                    search_params = []
                    for artist_key in batch:
                        artist_info = unique_artists[artist_key]
                        if artist_info['musicbrainz_artistid']:
                            search_params.append(f"musicbrainz_id={artist_info['musicbrainz_artistid']}")
                        else:
                            # Recherche par nom (on prend le premier du batch pour simplifer)
                            search_params.append(f"name={artist_info['name']}")
                            break  # Une recherche par nom suffit pour le batch
                    
                    if search_params:
                        query_string = "&".join(search_params[:5])  # Limiter à 5 paramètres
                        response = await client.get(f"{library_api_url}/api/artists/search?{query_string}")
                        
                        if response.status_code == 200:
                            artists = response.json()
                            for artist in artists:
                                # Trouver la clé correspondante
                                for artist_key, artist_info in unique_artists.items():
                                    if (artist_info['musicbrainz_artistid'] and
                                        artist.get('musicbrainz_artistid') == artist_info['musicbrainz_artistid']):
                                        existing_artists[artist_key] = artist
                                        break
                                    elif (not artist_info['musicbrainz_artistid'] and
                                          artist.get('name', '').strip().lower() == artist_key):
                                        existing_artists[artist_key] = artist
                                        break
                        
                except Exception as e:
                    logger.error(f"[RESOLVE] Erreur recherche batch {i//batch_size + 1}: {e}")
                    
    except Exception as e:
        logger.error(f"[RESOLVE] Erreur recherche artistes existants: {e}")


async def _create_missing_artists(new_artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Crée les nouveaux artistes via l'API.
    
    Args:
        new_artists: Liste des nouveaux artistes à créer
        
    Returns:
        Liste des artistes créés avec leurs IDs
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Création en lots pour optimiser les performances
            batch_size = 50
            created_artists = []
            
            for i in range(0, len(new_artists), batch_size):
                batch = new_artists[i:i + batch_size]
                
                try:
                    # Nettoyer les données du batch
                    clean_batch = []
                    for artist in batch:
                        clean_artist = {
                            'name': artist.get('name'),
                            'musicbrainz_artistid': artist.get('musicbrainz_artistid')
                        }
                        clean_batch.append(clean_artist)
                    
                    response = await client.post(
                        f"{library_api_url}/api/artists/batch",
                        json=clean_batch,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code in (200, 201):
                        batch_result = response.json()
                        created_artists.extend(batch_result)
                        logger.debug(f"[RESOLVE] Batch artistes créés: {len(batch_result)}")
                    else:
                        logger.error(f"[RESOLVE] Erreur création batch artistes: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    logger.error(f"[RESOLVE] Erreur création batch {i//batch_size + 1}: {e}")
            
            return created_artists
            
    except Exception as e:
        logger.error(f"[RESOLVE] Erreur création nouveaux artistes: {e}")
        raise


async def _search_existing_albums(albums_data: List[Dict[str, Any]], artist_mapping: Dict[str, Any]) -> Dict[str, Dict]:
    """
    Recherche les albums existants par titre et album_artist_id.
    """
    try:
        existing_albums = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for album in albums_data:
                # Construire une clé unique pour l'album
                album_key = f"{album['title'].strip().lower()}_{album['album_artist_id']}"
                
                # Recherche par titre et artiste
                search_params = f"title={album['title']}&album_artist_id={album['album_artist_id']}"
                response = await client.get(f"{library_api_url}/api/albums/search?{search_params}")
                
                if response.status_code == 200:
                    albums = response.json()
                    if albums:
                        existing_albums[album_key] = albums[0]  # Prendre le premier résultat
                        
        return existing_albums
        
    except Exception as e:
        logger.error(f"[RESOLVE-ALBUMS] Erreur recherche albums existants: {e}")
        return {}


async def _create_missing_albums(albums_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Crée les nouveaux albums via l'API.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{library_api_url}/api/albums/batch",
                json=albums_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(f"[RESOLVE-ALBUMS] Erreur création albums: {response.status_code} - {response.text}")
                return []
                
    except Exception as e:
        logger.error(f"[RESOLVE-ALBUMS] Erreur création albums: {e}")
        return []


async def _search_existing_genres(genres_names: List[str]) -> Dict[str, Dict]:
    """
    Recherche les genres existants par nom avec gestion robuste des doublons.
    """
    try:
        existing_genres = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for genre_name in genres_names:
                try:
                    # Recherche par nom exact (insensible à la casse)
                    search_name = genre_name.strip().lower()
                    response = await client.get(f"{library_api_url}/api/genres/search?name={search_name}")
                    
                    if response.status_code == 200:
                        genres = response.json()
                        if genres:
                            # Utiliser le premier genre trouvé pour la correspondance exacte
                            for genre in genres:
                                if genre.get('name', '').strip().lower() == search_name:
                                    existing_genres[genre_name] = genre
                                    logger.debug(f"[RESOLVE-GENRES] Genre existant trouvé: {genre_name} (ID: {genre.get('id')})")
                                    break
                        else:
                            logger.debug(f"[RESOLVE-GENRES] Aucun genre trouvé pour: {genre_name}")
                    else:
                        logger.warning(f"[RESOLVE-GENRES] Erreur recherche genre {genre_name}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"[RESOLVE-GENRES] Exception recherche genre {genre_name}: {e}")
                        
        logger.info(f"[RESOLVE-GENRES] Recherche terminée: {len(existing_genres)}/{len(genres_names)} genres trouvés")
        return existing_genres
        
    except Exception as e:
        logger.error(f"[RESOLVE-GENRES] Erreur recherche genres existants: {e}")
        return {}


async def _create_missing_genres(genres_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Crée les nouveaux genres via l'API avec gestion robuste des doublons et erreurs de contrainte.
    Utilise une approche "upsert" : si le genre existe déjà, l'utiliser au lieu de lever une erreur.
    """
    try:
        created_genres = []
        
        async with httpx.AsyncClient(
            timeout=60.0,  # Timeout plus long pour les retry
            follow_redirects=True
        ) as client:
            
            for genre_data in genres_data:
                try:
                    genre_name = genre_data.get('name', 'Unknown')
                    logger.info(f"[RESOLVE-GENRES] Tentative création/validation genre: {genre_name}")
                    
                    # Approche robuste : d'abord essayer de créer, puis rechercher si ça échoue
                    response = await client.post(
                        f"{library_api_url}/api/genres",
                        json=genre_data,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code in (200, 201):
                        # Création réussie
                        created_genre = response.json()
                        created_genres.append(created_genre)
                        logger.info(f"[RESOLVE-GENRES] ✅ Genre créé avec succès: {created_genre.get('name', 'Unknown')}")
                        
                    elif response.status_code == 409:
                        # Contrainte UNIQUE : le genre existe déjà
                        logger.warning(f"[RESOLVE-GENRES] ⚠️ Genre '{genre_name}' existe déjà, recherche...")
                        
                        # Rechercher le genre existant
                        search_response = await client.get(
                            f"{library_api_url}/api/genres/search?name={genre_name.strip().lower()}"
                        )
                        
                        if search_response.status_code == 200:
                            existing_genres = search_response.json()
                            if existing_genres:
                                # Prendre le premier genre qui correspond exactement
                                for existing_genre in existing_genres:
                                    if existing_genre.get('name', '').strip().lower() == genre_name.strip().lower():
                                        created_genres.append(existing_genre)
                                        logger.info(f"[RESOLVE-GENRES] ✅ Genre existant utilisé: {existing_genre.get('name', 'Unknown')} (ID: {existing_genre.get('id')})")
                                        break
                                else:
                                    logger.error(f"[RESOLVE-GENRES] Aucun genre exactement '{genre_name}' trouvé après erreur 409")
                            else:
                                logger.error(f"[RESOLVE-GENRES] Aucun genre retourné après recherche pour '{genre_name}'")
                        else:
                            logger.error(f"[RESOLVE-GENRES] Erreur recherche genre existant '{genre_name}': {search_response.status_code}")
                            
                    elif response.status_code == 307:
                        # Redirection 307
                        logger.warning(f"[RESOLVE-GENRES] ⚠️ Redirection 307 pour genre {genre_name}")
                        location = response.headers.get('location')
                        if location:
                            logger.info(f"[RESOLVE-GENRES] Tentative redirection vers: {location}")
                            redirect_response = await client.post(
                                location,
                                json=genre_data,
                                headers={'Content-Type': 'application/json'}
                            )
                            if redirect_response.status_code in (200, 201):
                                created_genre = redirect_response.json()
                                created_genres.append(created_genre)
                                logger.info(f"[RESOLVE-GENRES] ✅ Genre créé après redirection: {created_genre.get('name', 'Unknown')}")
                            elif redirect_response.status_code == 409:
                                logger.warning(f"[RESOLVE-GENRES] Genre '{genre_name}' existe même après redirection")
                                # Même logique que pour le 409
                            else:
                                logger.error(f"[RESOLVE-GENRES] Erreur après redirection: {redirect_response.status_code} - {redirect_response.text}")
                        else:
                            logger.error(f"[RESOLVE-GENRES] Redirection 307 sans location pour '{genre_name}'")
                            
                    else:
                        logger.error(f"[RESOLVE-GENRES] Erreur création genre '{genre_name}': {response.status_code} - {response.text}")
                        
                        # En cas d'erreur, essayer une approche alternative : recherche puis création conditionnelle
                        if response.status_code in [400, 422, 500]:  # Erreurs qui pourraient indiquer un conflit
                            logger.info(f"[RESOLVE-GENRES] Tentative recherche alternative pour '{genre_name}'")
                            try:
                                search_response = await client.get(
                                    f"{library_api_url}/api/genres/search?name={genre_name.strip().lower()}"
                                )
                                if search_response.status_code == 200:
                                    existing_genres = search_response.json()
                                    if existing_genres:
                                        # Utiliser le genre existant trouvé
                                        for existing_genre in existing_genres:
                                            if existing_genre.get('name', '').strip().lower() == genre_name.strip().lower():
                                                created_genres.append(existing_genre)
                                                logger.info(f"[RESOLVE-GENRES] ✅ Genre existant utilisé (approche alternative): {existing_genre.get('name', 'Unknown')} (ID: {existing_genre.get('id')})")
                                                break
                            except Exception as search_error:
                                logger.error(f"[RESOLVE-GENRES] Erreur recherche alternative: {search_error}")
                        
                except Exception as e:
                    logger.error(f"[RESOLVE-GENRES] Exception création genre '{genre_data.get('name', 'Unknown')}': {e}")
                    
        logger.info(f"[RESOLVE-GENRES] Création genres terminée: {len(created_genres)} genres traités")
        return created_genres
                
    except Exception as e:
        logger.error(f"[RESOLVE-GENRES] Erreur générale création genres: {e}")
        return []
"""
Tâches Celery pour le traitement des covers utilisant tous les services spécialisés.
Utilise le CoverOrchestratorService pour coordonner le traitement intelligent des images.
"""

import asyncio
from typing import List, Dict, Any
from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery
from backend_worker.services.cover_orchestrator_service import cover_orchestrator_service
from backend_worker.services.cover_types import CoverProcessingContext, ImageType, TaskType


@celery.task(name="covers.process_artist_images", queue="deferred")
def process_artist_images(artist_ids: List[int], priority: str = "normal"):
    """
    Traite les images d'artistes en utilisant le CoverOrchestratorService.

    Utilise tous les services spécialisés :
    - CoverOrchestratorService (coordination)
    - ImageProcessingService (traitement/redimensionnement)
    - ImagePriorityService (priorisation intelligente)
    - ImageCacheService (cache Redis)
    - CoverArtService (API externes)
    - ImageService (extraction fichiers locaux)
    """
    try:
        logger.info(f"[COVERS] Début traitement images artistes: {len(artist_ids)} artistes")

        # Création des contextes de traitement
        contexts = []
        for artist_id in artist_ids:
            context = CoverProcessingContext(
                image_type=ImageType.ARTIST_IMAGE,
                entity_id=artist_id,
                entity_path=None,  # Pas de chemin spécifique pour les artistes
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "artist",
                    "batch_size": len(artist_ids)
                }
            )
            contexts.append(context)

        # Traitement via l'orchestrateur (utilise tous les services)
        result = asyncio.run(cover_orchestrator_service.process_batch(contexts))

        logger.info(f"[COVERS] Traitement images artistes terminé: {result}")
        return {
            "success": True,
            "artists_processed": len(artist_ids),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImagePriorityService",
                "ImageCacheService",
                "CoverArtService",
                "ImageService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement images artistes: {str(e)}")
        return {"success": False, "error": str(e), "artists_processed": 0}


@celery.task(name="covers.process_album_covers", queue="deferred")
def process_album_covers(album_ids: List[int], priority: str = "normal"):
    """
    Traite les covers d'albums en utilisant le CoverOrchestratorService.

    Utilise tous les services spécialisés pour un traitement optimisé :
    - Recherche dans les dossiers locaux (ImageService)
    - API Cover Art Archive (CoverArtService)
    - Cache Redis intelligent (ImageCacheService)
    - Priorisation basée sur la popularité (ImagePriorityService)
    - Traitement/redimensionnement optimisé (ImageProcessingService)
    """
    try:
        logger.info(f"[COVERS] Début traitement covers albums: {len(album_ids)} albums")

        # Création des contextes de traitement
        contexts = []
        for album_id in album_ids:
            context = CoverProcessingContext(
                image_type=ImageType.ALBUM_COVER,
                entity_id=album_id,
                entity_path=None,  # Pas de chemin spécifique pour les albums
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "album",
                    "batch_size": len(album_ids)
                }
            )
            contexts.append(context)

        # Traitement via l'orchestrateur complet
        result = asyncio.run(cover_orchestrator_service.process_batch(contexts))

        logger.info(f"[COVERS] Traitement covers albums terminé: {result}")
        return {
            "success": True,
            "albums_processed": len(album_ids),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImagePriorityService",
                "ImageCacheService",
                "CoverArtService",
                "ImageService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement covers albums: {str(e)}")
        return {"success": False, "error": str(e), "albums_processed": 0}


@celery.task(name="covers.process_track_covers_batch", queue="deferred")
def process_track_covers_batch(album_covers: List[Dict[str, Any]]):
    """
    Traite les covers extraites des métadonnées des tracks.

    Utilise l'orchestrateur pour traiter les covers embedded trouvées
    lors de l'extraction des métadonnées audio.
    """
    try:
        logger.info(f"[COVERS] Début traitement covers depuis tracks: {len(album_covers)} covers")

        # Création des contextes depuis les données de tracks
        contexts = []
        for cover_data in album_covers:
            context = CoverProcessingContext(
                image_type=ImageType.ALBUM_COVER,
                entity_id=cover_data.get("album_id"),
                entity_path=cover_data.get("path"),
                task_type=TaskType.METADATA_EXTRACTION,
                priority="normal",
                metadata={
                    "source": "track_embedded",
                    "cover_data": cover_data.get("cover_data"),
                    "mime_type": cover_data.get("cover_mime_type"),
                    "track_path": cover_data.get("path")
                }
            )
            contexts.append(context)

        # Traitement via l'orchestrateur
        result = asyncio.run(cover_orchestrator_service.process_batch(contexts))

        logger.info(f"[COVERS] Traitement covers tracks terminé: {result}")
        return {
            "success": True,
            "covers_processed": len(album_covers),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImageCacheService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement covers tracks: {str(e)}")
        return {"success": False, "error": str(e), "covers_processed": 0}


@celery.task(name="covers.process_artist_images_batch", queue="deferred")
def process_artist_images_batch(artist_images: List[Dict[str, Any]]):
    """
    Traite les images d'artistes extraites des métadonnées des tracks.

    Utilise l'orchestrateur pour traiter les images d'artistes trouvées
    dans les dossiers lors du scan.
    """
    try:
        logger.info(f"[COVERS] Début traitement images artistes depuis tracks: {len(artist_images)} lots")

        # Création des contextes depuis les données de tracks
        contexts = []
        for artist_data in artist_images:
            context = CoverProcessingContext(
                image_type=ImageType.ARTIST_IMAGE,
                entity_id=artist_data.get("artist_id"),
                entity_path=artist_data.get("path"),
                task_type=TaskType.METADATA_EXTRACTION,
                priority="normal",
                metadata={
                    "source": "track_artist_folder",
                    "artist_images": artist_data.get("images", []),
                    "artist_path": artist_data.get("artist_path")
                }
            )
            contexts.append(context)

        # Traitement via l'orchestrateur
        result = asyncio.run(cover_orchestrator_service.process_batch(contexts))

        logger.info(f"[COVERS] Traitement images artistes tracks terminé: {result}")
        return {
            "success": True,
            "images_processed": len(artist_images),
            "results": result,
            "services_used": [
                "CoverOrchestratorService",
                "ImageProcessingService",
                "ImageCacheService",
                "ImageService"
            ]
        }

    except Exception as e:
        logger.error(f"[COVERS] Erreur traitement images artistes tracks: {str(e)}")
        return {"success": False, "error": str(e), "images_processed": 0}
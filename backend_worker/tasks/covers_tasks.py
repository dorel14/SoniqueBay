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
        logger.info(f"[COVERS] Artist IDs à traiter: {artist_ids}")

        # Récupérer les informations des artistes depuis la base de données via l'API
        import httpx
        import os
        # Utiliser l'URL de l'API depuis les variables d'environnement ou localhost en dev
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[COVERS] API URL utilisée: {api_url}")
        artist_infos = []
        
        for artist_id in artist_ids:
            try:
                # Récupérer les informations de l'artiste via l'API REST
                logger.info(f"[COVERS] Récupération infos artiste {artist_id} depuis {api_url}/api/artists/{artist_id}")
                response = httpx.get(f"{api_url}/api/artists/{artist_id}", timeout=10)
                logger.info(f"[COVERS] Status code réponse API pour artiste {artist_id}: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    logger.info(f"[COVERS] Données artiste {artist_id} récupérées: {artist_data.get('name')}")
                    artist_infos.append(artist_data)
                else:
                    logger.warning(f"[COVERS] Impossible de récupérer les informations de l'artiste {artist_id} - Status: {response.status_code}")
            except Exception as e:
                logger.warning(f"[COVERS] Erreur lors de la récupération des infos de l'artiste {artist_id}: {str(e)}")
                continue

        logger.info(f"[COVERS] Informations récupérées pour {len(artist_infos)} artistes")

        # Création des contextes de traitement
        contexts = []
        for artist_info in artist_infos:
            artist_id = artist_info.get("id")
            artist_name = artist_info.get("name")
            
            # Tentative de détermination du chemin de l'artiste (basé sur les tracks)
            artist_path = None
            try:
                # Récupérer les tracks de l'artiste pour déterminer le chemin
                tracks_response = httpx.get(f"{api_url}/api/artists/{artist_id}/tracks", timeout=10)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        from pathlib import Path
                        track_path = tracks[0].get("path")
                        if track_path:
                            track_dir = Path(track_path).parent
                            # Supposer structure: .../Artiste/Album/Track
                            artist_path = str(track_dir.parent)
                            logger.debug(f"[COVERS] Chemin artiste déduit pour {artist_name}: {artist_path}")
            except Exception as e:
                logger.debug(f"[COVERS] Impossible de déterminer le chemin de l'artiste {artist_id}: {str(e)}")

            context = CoverProcessingContext(
                image_type=ImageType.ARTIST_IMAGE,
                entity_id=artist_id,
                entity_path=artist_path,
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "artist",
                    "batch_size": len(artist_ids),
                    "artist_name": artist_name,
                    "musicbrainz_artistid": artist_info.get("musicbrainz_artistid")
                }
            )
            contexts.append(context)

        logger.info(f"[COVERS] Contextes créés: {len(contexts)}")

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

        # Récupérer les informations des albums depuis la base de données via l'API
        import httpx
        import os
        # Utiliser l'URL de l'API depuis les variables d'environnement ou localhost en dev
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[COVERS] API URL utilisée pour albums: {api_url}")
        album_infos = []
        
        for album_id in album_ids:
            try:
                # Récupérer les informations de l'album via l'API REST
                response = httpx.get(f"{api_url}/api/albums/{album_id}", timeout=10)
                if response.status_code == 200:
                    album_data = response.json()
                    album_infos.append(album_data)
                else:
                    logger.warning(f"[COVERS] Impossible de récupérer les informations de l'album {album_id}")
            except Exception as e:
                logger.warning(f"[COVERS] Erreur lors de la récupération des infos de l'album {album_id}: {str(e)}")
                continue

        logger.info(f"[COVERS] Informations récupérées pour {len(album_infos)} albums")

        # Création des contextes de traitement
        contexts = []
        for album_info in album_infos:
            album_id = album_info.get("id")
            album_title = album_info.get("title")
            
            # Tentative de détermination du chemin de l'album (basé sur les tracks)
            album_path = None
            try:
                # Récupérer les tracks de l'album pour déterminer le chemin
                tracks_response = httpx.get(f"{api_url}/api/albums/{album_id}/tracks", timeout=10)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        from pathlib import Path
                        track_path = tracks[0].get("path")
                        if track_path:
                            album_path = str(Path(track_path).parent)
                            logger.debug(f"[COVERS] Chemin album déduit pour {album_title}: {album_path}")
            except Exception as e:
                logger.debug(f"[COVERS] Impossible de déterminer le chemin de l'album {album_id}: {str(e)}")

            context = CoverProcessingContext(
                image_type=ImageType.ALBUM_COVER,
                entity_id=album_id,
                entity_path=album_path,
                task_type=TaskType.BATCH_PROCESSING,
                priority=priority,
                metadata={
                    "source": "batch_processing",
                    "entity_type": "album",
                    "batch_size": len(album_ids),
                    "album_title": album_title,
                    "artist_name": album_info.get("album_artist_name"),
                    "musicbrainz_albumid": album_info.get("musicbrainz_albumid")
                }
            )
            contexts.append(context)

        logger.info(f"[COVERS] Contextes créés: {len(contexts)}")

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


@celery.task(name="covers.extract_artist_images", queue="deferred")
def extract_artist_images(file_paths: list[str]):
    """
    Extrait les images d'artistes depuis les chemins de fichiers musicaux.
    
    Cette tâche Celery extrait les images d'artistes des dossiers contenant
    les fichiers musicaux et les traite via le CoverOrchestratorService.
    
    Args:
        file_paths: Liste des chemins de fichiers musicaux à analyser
        
    Returns:
        Résultat du traitement avec statistiques
    """
    try:
        logger.info(f"[COVERS] Début extraction images artistes: {len(file_paths)} fichiers")
        
        if not file_paths:
            logger.warning("[COVERS] Aucun fichier fourni pour l'extraction")
            return {"success": True, "files_processed": 0, "artist_images_found": 0}
        
        # Grouper les fichiers par dossier artiste pour optimiser les appels
        artist_folders = {}
        for file_path in file_paths:
            try:
                from pathlib import Path
                parts = Path(file_path).parts
                artist_depth = 3  # Configuration standard pour les dossiers musicaux
                artist_path = Path(*parts[:artist_depth]) if len(parts) > artist_depth else Path(file_path).parent
                artist_path_str = str(artist_path)
                
                if artist_path_str not in artist_folders:
                    artist_folders[artist_path_str] = []
                artist_folders[artist_path_str].append(file_path)
                
            except Exception as e:
                logger.warning(f"[COVERS] Erreur traitement chemin {file_path}: {str(e)}")
                continue
        
        logger.info(f"[COVERS] Regroupement: {len(artist_folders)} dossiers artistes trouvés")
        
        # Extraire les images d'artistes pour chaque dossier
        artist_images_data = []
        for artist_path, files_in_folder in artist_folders.items():
            try:
                logger.debug(f"[COVERS] Extraction images pour dossier artiste: {artist_path}")
                
                # Importer la fonction d'extraction
                from backend_worker.services.music_scan import extract_artist_images as async_extract_artist_images
                import asyncio
                
                # Créer le répertoire de base pour la validation sécurité
                base_path = Path(list(artist_folders.keys())[0]).parent if artist_folders else Path(artist_path).parent
                allowed_base_paths = [base_path.resolve()]
                
                # Extraction asynchrone des images
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    artist_images = loop.run_until_complete(
                        async_extract_artist_images(artist_path, allowed_base_paths)
                    )
                finally:
                    loop.close()
                
                if artist_images:
                    # Préparer les données pour le traitement
                    from pathlib import Path
                    # Trouver l'ID artiste correspondant (premier fichier du dossier)
                    sample_file = files_in_folder[0] if files_in_folder else None
                    artist_name = Path(artist_path).name
                    
                    artist_images_data.append({
                        "artist_path": artist_path,
                        "artist_name": artist_name,
                        "files_count": len(files_in_folder),
                        "images": artist_images
                    })
                    
                    logger.info(f"[COVERS] {len(artist_images)} images trouvées pour {artist_name}")
                else:
                    logger.debug(f"[COVERS] Aucune image trouvée pour {artist_path}")
                    
            except Exception as e:
                logger.error(f"[COVERS] Erreur extraction images pour {artist_path}: {str(e)}")
                continue
        
        # Traiter les images via la tâche existante si des images ont été trouvées
        if artist_images_data:
            logger.info(f"[COVERS] Lancement traitement de {len(artist_images_data)} lots d'images")
            
            # Utiliser la tâche de traitement existante
            result = process_artist_images_batch(artist_images_data)
            
            return {
                "success": True,
                "files_processed": len(file_paths),
                "artist_folders_processed": len(artist_folders),
                "artist_images_found": len(artist_images_data),
                "processing_result": result
            }
        else:
            logger.info("[COVERS] Aucune image d'artiste trouvée dans les dossiers analysés")
            return {
                "success": True,
                "files_processed": len(file_paths),
                "artist_folders_processed": len(artist_folders),
                "artist_images_found": 0,
                "message": "Aucune image d'artiste trouvée"
            }
            
    except Exception as e:
        logger.error(f"[COVERS] Erreur extraction images artistes: {str(e)}")
        return {
            "success": False, 
            "error": str(e), 
            "files_processed": len(file_paths) if 'file_paths' in locals() else 0
        }


@celery.task(name="covers.extract_embedded", queue="deferred")
def extract_embedded(file_paths: list[str]):
    """
    Extrait les covers intégrées (embedded) depuis les fichiers musicaux.
    
    Cette tâche Celery extrait les covers intégrées dans les métadonnées
    des fichiers musicaux et les traite via le CoverOrchestratorService.
    
    Args:
        file_paths: Liste des chemins de fichiers musicaux à analyser
        
    Returns:
        Résultat du traitement avec statistiques
    """
    try:
        logger.info(f"[COVERS] Début extraction covers intégrées: {len(file_paths)} fichiers")
        
        if not file_paths:
            logger.warning("[COVERS] Aucun fichier fourni pour l'extraction")
            return {"success": True, "files_processed": 0, "embedded_covers_found": 0}
        
        # Préparer les données pour le traitement batch
        album_covers_data = []
        
        for file_path in file_paths:
            try:
                from pathlib import Path
                
                # Extraire les covers intégrées via mutagen
                from mutagen import File
                from backend_worker.services.music_scan import get_cover_art
                
                # Ouvrir le fichier audio de manière sécurisée
                path_obj = Path(file_path)
                if not path_obj.exists() or not path_obj.is_file():
                    logger.warning(f"[COVERS] Fichier non trouvé: {file_path}")
                    continue
                
                # Lire le fichier avec mutagen
                audio = File(file_path)
                if audio is None:
                    logger.warning(f"[COVERS] Impossible de lire le fichier: {file_path}")
                    continue
                
                # Créer les chemins de base pour la validation sécurité
                base_path = path_obj.parent.parent.parent  # Remonter 3 niveaux
                allowed_base_paths = [base_path.resolve()]
                
                # Extraction asynchrone de la cover
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    cover_data, mime_type = loop.run_until_complete(
                        get_cover_art(file_path, audio, allowed_base_paths)
                    )
                finally:
                    loop.close()
                
                if cover_data:
                    # Déterminer l'ID de l'album (chemin parent)
                    album_path = path_obj.parent
                    
                    album_covers_data.append({
                        "album_id": None,  # Sera résolu plus tard
                        "path": file_path,
                        "cover_data": cover_data,
                        "cover_mime_type": mime_type
                    })
                    
                    logger.debug(f"[COVERS] Cover intégrée trouvée: {file_path}")
                else:
                    logger.debug(f"[COVERS] Aucune cover intégrée: {file_path}")
                    
            except Exception as e:
                logger.warning(f"[COVERS] Erreur extraction cover pour {file_path}: {str(e)}")
                continue
        
        # Traiter les covers via la tâche existante si des covers ont été trouvées
        if album_covers_data:
            logger.info(f"[COVERS] Lancement traitement de {len(album_covers_data)} covers intégrées")
            
            # Utiliser la tâche de traitement existante
            result = process_track_covers_batch(album_covers_data)
            
            return {
                "success": True,
                "files_processed": len(file_paths),
                "embedded_covers_found": len(album_covers_data),
                "processing_result": result
            }
        else:
            logger.info("[COVERS] Aucune cover intégrée trouvée dans les fichiers analysés")
            return {
                "success": True,
                "files_processed": len(file_paths),
                "embedded_covers_found": 0,
                "message": "Aucune cover intégrée trouvée"
            }
            
    except Exception as e:
        logger.error(f"[COVERS] Erreur extraction covers intégrées: {str(e)}")
        return {
            "success": False, 
            "error": str(e), 
            "files_processed": len(file_paths) if 'file_paths' in locals() else 0
        }
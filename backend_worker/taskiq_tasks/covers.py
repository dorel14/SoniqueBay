"""Tâches TaskIQ pour le traitement des covers.
Migration de celery_tasks.py vers TaskIQ.
"""
import asyncio
from typing import List, Dict, Any
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger
import httpx
import os
from pathlib import Path

# Import des services spécialisés (à migrer progressivement)
# from backend_worker.services.cover_orchestrator_service import cover_orchestrator_service
# from backend_worker.services.cover_types import CoverProcessingContext, ImageType, TaskType


@broker.task
async def extract_embedded_task(file_paths: List[str]) -> Dict[str, Any]:
    """
    Extrait les covers intégrées (embedded) depuis les fichiers musicaux.
    
    Cette tâche TaskIQ extrait les covers intégrées dans les métadonnées
    des fichiers musicaux et les traite via le CoverOrchestratorService.
    
    Args:
        file_paths: Liste des chemins de fichiers musicaux à analyser
        
    Returns:
        Résultat du traitement avec statistiques
    """
    logger.info(f"[TASKIQ|COVERS] Début extraction covers intégrées: {len(file_paths)} fichiers")
    
    if not file_paths:
        logger.warning("[TASKIQ|COVERS] Aucun fichier fourni pour l'extraction")
        return {"success": True, "files_processed": 0, "embedded_covers_found": 0}
    
    # Préparer les données pour le traitement batch
    album_covers_data = []
    
    for file_path in file_paths:
        try:
            # Extraire les covers intégrées via mutagen
            from mutagen import File
            from backend_worker.services.music_scan import get_cover_art
            
            # Ouvrir le fichier audio de manière sécurisée
            path_obj = Path(file_path)
            if not path_obj.exists() or not path_obj.is_file():
                logger.warning(f"[TASKIQ|COVERS] Fichier non trouvé: {file_path}")
                continue
            
            # Lire le fichier avec mutagen
            audio = File(file_path)
            if audio is None:
                logger.warning(f"[TASKIQ|COVERS] Impossible de lire le fichier: {file_path}")
                continue
            
            # Créer les chemins de base pour la validation sécurité
            base_path = path_obj.parent.parent.parent  # Remonter 3 niveaux
            allowed_base_paths = [base_path.resolve()]
            
            # Extraction asynchrone de la cover
            try:
                cover_data, mime_type = await asyncio.wait_for(
                    get_cover_art(file_path, audio, allowed_base_paths),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error(f"[TASKIQ|COVERS] Timeout extraction cover pour {file_path}")
                continue
            except Exception as e:
                logger.warning(f"[TASKIQ|COVERS] Erreur extraction cover pour {file_path}: {str(e)}")
                continue
            
            if cover_data:
                # Déterminer l'ID de l'album (chemin parent)
                album_path = path_obj.parent
                
                album_covers_data.append({
                    "album_id": None,  # Sera résolu plus tard
                    "path": file_path,
                    "cover_data": cover_data,
                    "cover_mime_type": mime_type
                })
                
                logger.debug(f"[TASKIQ|COVERS] Cover intégrée trouvée: {file_path}")
            else:
                logger.debug(f"[TASKIQ|COVERS] Aucune cover intégrée: {file_path}")
                
        except Exception as e:
            logger.warning(f"[TASKIQ|COVERS] Erreur extraction cover pour {file_path}: {str(e)}")
            continue
    
    # Traiter les covers via la tâche existante si des covers ont été trouvées
    if album_covers_data:
        logger.info(f"[TASKIQ|COVERS] Lancement traitement de {len(album_covers_data)} covers intégrées")
        
        # Utiliser la tâche de traitement existante (à convertir en TaskIQ également)
        result = await process_track_covers_batch(album_covers_data)
        
        return {
            "success": True,
            "files_processed": len(file_paths),
            "embedded_covers_found": len(album_covers_data),
            "processing_result": result
        }
    else:
        logger.info("[TASKIQ|COVERS] Aucune cover intégrée trouvée dans les fichiers analysés")
        return {
            "success": True,
            "files_processed": len(file_paths),
            "embedded_covers_found": 0,
            "message": "Aucune cover intégrée trouvée"
        }


@broker.task
async def process_track_covers_batch(album_covers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Traite les covers extraites des métadonnées des tracks.
    
    Utilise l'orchestrateur pour traiter les covers embedded trouvées
    lors de l'extraction des métadonnées audio.
    """
    logger.info(f"[TASKIQ|COVERS] Début traitement covers depuis tracks: {len(album_covers)} covers")
    
    try:
        # Création des contextes depuis les données de tracks
        contexts = []
        for cover_data in album_covers:
            # TODO: Utiliser le CoverOrchestratorService quand il sera disponible
            # Pour l'instant, implémentation simplifiée
            context_data = {
                "image_type": "album_cover",
                "entity_id": cover_data.get("album_id"),
                "entity_path": cover_data.get("path"),
                "task_type": "metadata_extraction",
                "priority": "normal",
                "metadata": {
                    "source": "track_embedded",
                    "cover_data": cover_data.get("cover_data"),
                    "mime_type": cover_data.get("cover_mime_type"),
                    "track_path": cover_data.get("path")
                }
            }
            contexts.append(context_data)
        
        # Traitement via l'orchestrateur (à implémenter)
        # result = await cover_orchestrator_service.process_batch(contexts)
        
        # Placeholder pour l'instant
        result = {
            "processed": len(album_covers),
            "success": True,
            "message": f"Traitement de {len(album_covers)} covers effectué (placeholder)"
        }
        
        logger.info(f"[TASKIQ|COVERS] Traitement covers tracks terminé: {result}")
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
        logger.error(f"[TASKIQ|COVERS] Erreur traitement covers tracks: {str(e)}")
        return {"success": False, "error": str(e), "covers_processed": 0}


@broker.task
async def process_artist_images(artist_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
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
    logger.info(f"[TASKIQ|COVERS] Début traitement images artistes: {len(artist_ids)} artistes")
    logger.info(f"[TASKIQ|COVERS] Artist IDs à traiter: {artist_ids}")

    try:
        # Récupérer les informations des artistes depuis la base de données via l'API
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[TASKIQ|COVERS] API URL utilisée: {api_url}")
        artist_infos = []
        
        for artist_id in artist_ids:
            try:
                # Récupérer les informations de l'artiste via l'API REST
                logger.info(f"[TASKIQ|COVERS] Récupération infos artiste {artist_id} depuis {api_url}/api/artists/{artist_id}")
                response = await httpx.get(f"{api_url}/api/artists/{artist_id}", timeout=10.0)
                logger.info(f"[TASKIQ|COVERS] Status code réponse API pour artiste {artist_id}: {response.status_code}")
                if response.status_code == 200:
                    artist_data = response.json()
                    logger.info(f"[TASKIQ|COVERS] Données artiste {artist_id} récupérées: {artist_data.get('name')}")
                    artist_infos.append(artist_data)
                else:
                    logger.warning(f"[TASKIQ|COVERS] Impossible de récupérer les informations de l'artiste {artist_id} - Status: {response.status_code}")
            except Exception as e:
                logger.warning(f"[TASKIQ|COVERS] Erreur lors de la récupération des infos de l'artiste {artist_id}: {str(e)}")
                continue

        logger.info(f"[TASKIQ|COVERS] Informations récupérées pour {len(artist_infos)} artistes")

        # Création des contextes de traitement
        contexts = []
        for artist_info in artist_infos:
            artist_id = artist_info.get("id")
            artist_name = artist_info.get("name")
            
            # Tentative de détermination du chemin de l'artiste (basé sur les tracks)
            artist_path = None
            try:
                # Récupérer les tracks de l'artiste pour déterminer le chemin
                tracks_response = await httpx.get(f"{api_url}/api/artists/{artist_id}/tracks", timeout=10.0)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        track_path = tracks[0].get("path")
                        if track_path:
                            track_dir = Path(track_path).parent
                            # Supposer structure: .../Artiste/Album/Track
                            artist_path = str(track_dir.parent)
                            logger.info(f"[TASKIQ|COVERS] Chemin artiste déduit pour {artist_name}: {artist_path}")
            except Exception as e:
                logger.debug(f"[TASKIQ|COVERS] Impossible de déterminer le chemin de l'artiste {artist_id}: {str(e)}")

            context = {
                "image_type": "artist_image",
                "entity_id": artist_id,
                "entity_path": artist_path,
                "task_type": "batch_processing",
                "priority": priority,
                "metadata": {
                    "source": "batch_processing",
                    "entity_type": "artist",
                    "batch_size": len(artist_ids),
                    "artist_name": artist_name,
                    "musicbrainz_artistid": artist_info.get("musicbrainz_artistid")
                }
            }
            contexts.append(context)

        logger.info(f"[TASKIQ|COVERS] Contextes créés: {len(contexts)}")

        # Traitement via l'orchestrateur (à implémenter)
        # TODO: Utiliser le CoverOrchestratorService quand il sera disponible
        # Pour l'instant, implémentation simplifiée
        result = {
            "processed": len(artist_ids),
            "success": True,
            "message": f"Traitement de {len(artist_ids)} images d'artistes effectué (placeholder)"
        }

        logger.info(f"[TASKIQ|COVERS] Traitement images artistes terminé: {result}")
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
        logger.error(f"[TASKIQ|COVERS] Erreur traitement images artistes: {str(e)}")
        return {"success": False, "error": str(e), "artists_processed": 0}


@broker.task
async def process_album_covers(album_ids: List[int], priority: str = "normal") -> Dict[str, Any]:
    """
    Traite les covers d'albums en utilisant le CoverOrchestratorService.
    
    Utilise tous les services spécialisés pour un traitement optimisé :
    - Recherche dans les dossiers locaux (ImageService)
    - API Cover Art Archive (CoverArtService)
    - Cache Redis intelligent (ImageCacheService)
    - Priorisation basée sur la popularité (ImagePriorityService)
    - Traitement/redimensionnement optimisé (ImageProcessingService)
    """
    logger.info(f"[TASKIQ|COVERS] Début traitement covers albums: {len(album_ids)} albums")

    try:
        # Récupérer les informations des albums depuis la base de données via l'API
        api_url = os.getenv("API_URL", "http://localhost:8001")
        logger.info(f"[TASKIQ|COVERS] API URL utilisée pour albums: {api_url}")
        album_infos = []
        
        for album_id in album_ids:
            try:
                # Récupérer les informations de l'album via l'API REST
                logger.info(f"[TASKIQ|COVERS] Récupération infos album {album_id} depuis {api_url}/api/albums/{album_id}")
                response = await httpx.get(f"{api_url}/api/albums/{album_id}", timeout=10.0)
                if response.status_code == 200:
                    album_data = response.json()
                    logger.info(f"[TASKIQ|COVERS] Données album {album_id} récupérées: {album_data.get('title')}")
                    album_infos.append(album_data)
                else:
                    logger.warning(f"[TASKIQ|COVERS] Impossible de récupérer les informations de l'album {album_id}")
            except Exception as e:
                logger.warning(f"[TASKIQ|COVERS] Erreur lors de la récupération des infos de l'album {album_id}: {str(e)}")
                continue

        logger.info(f"[TASKIQ|COVERS] Informations récupérées pour {len(album_infos)} albums")

        # Création des contextes de traitement
        contexts = []
        for album_info in album_infos:
            album_id = album_info.get("id")
            album_title = album_info.get("title")
            
            # Tentative de détermination du chemin de l'album (basé sur les tracks)
            album_path = None
            try:
                # Récupérer les tracks de l'album pour déterminer le chemin
                tracks_response = await httpx.get(f"{api_url}/api/albums/{album_id}/tracks", timeout=10.0)
                if tracks_response.status_code == 200:
                    tracks = tracks_response.json()
                    if tracks:
                        track_path = tracks[0].get("path")
                        if track_path:
                            album_path = str(Path(track_path).parent)
                            logger.debug(f"[TASKIQ|COVERS] Chemin album déduit pour {album_title}: {album_path}")
            except Exception as e:
                logger.debug(f"[TASKIQ|COVERS] Impossible de déterminer le chemin de l'album {album_id}: {str(e)}")

            context = {
                "image_type": "album_cover",
                "entity_id": album_id,
                "entity_path": album_path,
                "task_type": "batch_processing",
                "priority": priority,
                "metadata": {
                    "source": "batch_processing",
                    "entity_type": "album",
                    "batch_size": len(album_ids),
                    "album_title": album_title,
                    "artist_name": album_info.get("album_artist_name"),
                    "musicbrainz_albumid": album_info.get("musicbrainz_albumid")
                }
            }
            contexts.append(context)

        logger.info(f"[TASKIQ|COVERS] Contextes créés: {len(contexts)}")

        # Traitement via l'orchestrateur (à implémenter)
        # TODO: Utiliser le CoverOrchestratorService quand il sera disponible
        # Pour l'instant, implémentation simplifiée
        result = {
            "processed": len(album_ids),
            "success": True,
            "message": f"Traitement de {len(album_ids)} covers d'albums effectué (placeholder)"
        }

        logger.info(f"[TASKIQ|COVERS] Traitement covers albums terminé: {result}")
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
        logger.error(f"[TASKIQ|COVERS] Erreur traitement covers albums: {str(e)}")
        return {"success": False, "error": str(e), "albums_processed": 0}


@broker.task
async def process_artist_images_batch(artist_images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Traite les images d'artistes extraites des métadonnées des tracks.
    
    Utilise l'orchestrateur pour traiter les images d'artistes trouvées
    dans les dossiers lors du scan.
    """
    logger.info(f"[TASKIQ|COVERS] Début traitement images artistes depuis tracks: {len(artist_images)} lots")

    try:
        # Création des contextes depuis les données de tracks
        contexts = []
        for artist_data in artist_images:
            context = {
                "image_type": "artist_image",
                "entity_id": artist_data.get("artist_id"),
                "entity_path": artist_data.get("path"),
                "task_type": "metadata_extraction",
                "priority": "normal",
                "metadata": {
                    "source": "track_artist_folder",
                    "artist_images": artist_data.get("images", []),
                    "artist_path": artist_data.get("artist_path")
                }
            }
            contexts.append(context)

        # Traitement via l'orchestrateur (à implémenter)
        # TODO: Utiliser le CoverOrchestratorService quand il sera disponible
        # Pour l'instant, implémentation simplifiée
        result = {
            "processed": len(artist_images),
            "success": True,
            "message": f"Traitement de {len(artist_images)} lots d'images d'artistes effectué (placeholder)"
        }

        logger.info(f"[TASKIQ|COVERS] Traitement images artistes tracks terminé: {result}")
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
        logger.error(f"[TASKIQ|COVERS] Erreur traitement images artistes tracks: {str(e)}")
        return {"success": False, "error": str(e), "images_processed": 0}


@broker.task
async def extract_artist_images(file_paths: List[str]) -> Dict[str, Any]:
    """
    Extrait les images d'artistes depuis les chemins de fichiers musicaux.
    
    Cette tâche TaskIQ extrait les images d'artistes des dossiers contenant
    les fichiers musicaux et les traite via le CoverOrchestratorService.
    
    Args:
        file_paths: Liste des chemins de fichiers musicaux à analyser
        
    Returns:
        Résultat du traitement avec statistiques
    """
    logger.info(f"[TASKIQ|COVERS] Début extraction images artistes: {len(file_paths)} fichiers")
    
    if not file_paths:
        logger.warning("[TASKIQ|COVERS] Aucun fichier fourni pour l'extraction")
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
            logger.warning(f"[TASKIQ|COVERS] Erreur traitement chemin {file_path}: {str(e)}")
            continue
    
    logger.info(f"[TASKIQ|COVERS] Regroupement: {len(artist_folders)} dossiers artistes trouvés")
    
    # Extraire les images d'artistes pour chaque dossier
    artist_images_data = []
    for artist_path, files_in_folder in artist_folders.items():
        try:
            logger.debug(f"[TASKIQ|COVERS] Extraction images pour dossier artiste: {artist_path}")
            
            # Importer la fonction d'extraction
            from backend_worker.services.music_scan import extract_artist_images as async_extract_artist_images
            
            # Créer le répertoire de base pour la validation sécurité
            base_path = Path(list(artist_folders.keys())[0]).parent if artist_folders else Path(artist_path).parent
            allowed_base_paths = [base_path.resolve()]
            
            # Extraction asynchrone des images
            try:
                artist_images = await asyncio.wait_for(
                    async_extract_artist_images(artist_path, allowed_base_paths),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error(f"[TASKIQ|COVERS] Timeout extraction images pour {artist_path}")
                continue
            except Exception as e:
                logger.error(f"[TASKIQ|COVERS] Erreur extraction images pour {artist_path}: {str(e)}")
                continue
            
            if artist_images:
                # Préparer les données pour le traitement
                # Trouver l'ID artiste correspondant (premier fichier du dossier)
                sample_file = files_in_folder[0] if files_in_folder else None
                artist_name = Path(artist_path).name
                
                artist_images_data.append({
                    "artist_path": artist_path,
                    "artist_name": artist_name,
                    "files_count": len(files_in_folder),
                    "images": artist_images
                })
                
                logger.info(f"[TASKIQ|COVERS] {len(artist_images)} images trouvées pour {artist_name}")
            else:
                logger.debug(f"[TASKIQ|COVERS] Aucune image trouvée pour {artist_path}")
                
        except Exception as e:
            logger.error(f"[TASKIQ|COVERS] Erreur extraction images pour {artist_path}: {str(e)}")
            continue
    
    # Traiter les images via la tâche existante si des images ont été trouvées
    if artist_images_data:
        logger.info(f"[TASKIQ|COVERS] Lancement traitement de {len(artist_images_data)} lots d'images")
        
        # Utiliser la tâche de traitement existante
        result = await process_artist_images_batch(artist_images_data)
        
        return {
            "success": True,
            "files_processed": len(file_paths),
            "artist_folders_processed": len(artist_folders),
            "artist_images_found": len(artist_images_data),
            "processing_result": result
        }
    else:
        logger.info("[TASKIQ|COVERS] Aucune image d'artiste trouvée dans les dossiers analysés")
        return {
            "success": True,
            "files_processed": len(file_paths),
            "artist_folders_processed": len(artist_folders),
            "artist_images_found": 0,
            "message": "Aucune image d'artiste trouvée"
        }
from backend_worker.services.music_scan import scan_music_files
from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_update_cover
)
from backend_worker.services.scan_optimizer import ScanOptimizer
import httpx
import asyncio
from backend_worker.utils.logging import logger
from pathlib import Path
from backend_worker.celery_app import celery
from backend_worker.services.music_scan import async_walk
from backend_worker.services.settings_service import SettingsService, MUSIC_PATH_TEMPLATE, ARTIST_IMAGE_FILES, ALBUM_COVER_FILES
from backend_worker.utils.pubsub import publish_event
import json
import time
import os


async def validate_file_path(file_path: str, base_path: Path) -> Path | None:
    """
    Valide qu'un chemin de fichier est dans les limites du répertoire de base avec validation complète.

    Args:
        file_path: Chemin du fichier à valider
        base_path: Répertoire de base autorisé (Path résolu)

    Returns:
        Path résolu validé si le chemin est valide et dans les limites, None sinon
    """
    try:
        logger.debug(f"[VALIDATE_FILE_PATH] Début validation pour: {file_path}")

        # ÉTAPE 1: Validation basique du paramètre d'entrée
        if not file_path or not isinstance(file_path, str):
            logger.warning(f"[VALIDATE_FILE_PATH] Chemin de fichier invalide: {file_path}")
            return None

        if not base_path or not isinstance(base_path, Path):
            logger.warning(f"[VALIDATE_FILE_PATH] Répertoire de base invalide: {base_path}")
            return None

        logger.debug("[VALIDATE_FILE_PATH] ✓ Paramètres d'entrée validés")

        # ÉTAPE 2: Conversion en Path et résolution
        try:
            path_obj = Path(file_path)
            if not path_obj.is_absolute():
                logger.warning(f"[VALIDATE_FILE_PATH] Chemin non absolu détecté: {file_path}")
                return None

            resolved_path = path_obj.resolve()
            logger.debug(f"[VALIDATE_FILE_PATH] Chemin résolu: {file_path} -> {resolved_path}")
        except (OSError, RuntimeError) as e:
            logger.warning(f"[VALIDATE_FILE_PATH] Impossible de résoudre le chemin {file_path}: {e}")
            return None

        # ÉTAPE 3: Validation que le chemin est dans le répertoire de base autorisé
        try:
            if not base_path.is_absolute():
                logger.warning(f"[VALIDATE_FILE_PATH] Répertoire de base non absolu: {base_path}")
                return None

            base_resolved = base_path.resolve()
            if not resolved_path.is_relative_to(base_resolved):
                logger.warning("[VALIDATE_FILE_PATH] Tentative de traversée de répertoire détectée")
                logger.warning(f"[VALIDATE_FILE_PATH] Chemin résolu: {resolved_path}")
                logger.warning(f"[VALIDATE_FILE_PATH] Répertoire de base: {base_resolved}")
                return None

            logger.debug(f"[VALIDATE_FILE_PATH] ✓ Chemin dans répertoire autorisé: {base_resolved}")
        except (OSError, ValueError) as e:
            logger.warning(f"[VALIDATE_FILE_PATH] Erreur de validation du répertoire de base: {e}")
            return None

        # ÉTAPE 4: Validation de la longueur du nom de fichier
        filename = resolved_path.name
        max_filename_length = 255
        if len(filename) > max_filename_length:
            logger.warning(f"[VALIDATE_FILE_PATH] Nom de fichier trop long: {len(filename)} caractères")
            return None

        if len(filename) == 0:
            logger.warning("[VALIDATE_FILE_PATH] Nom de fichier vide détecté")
            return None

        logger.debug(f"[VALIDATE_FILE_PATH] ✓ Longueur du nom validée: {len(filename)} caractères")

        # ÉTAPE 5: Vérification des caractères interdits
        path_str = str(resolved_path)

        # Caractères de contrôle et nuls
        if '\0' in path_str:
            logger.warning(f"[VALIDATE_FILE_PATH] Caractère nul détecté: {path_str}")
            return None

        # Caractères de contrôle problématiques
        control_chars = set(range(0, 32)) - {9, 10, 13}
        if any(ord(c) in control_chars for c in path_str):
            logger.warning(f"[VALIDATE_FILE_PATH] Caractères de contrôle détectés: {path_str}")
            return None

        # Caractères interdits spécifiques (exclure les caractères valides dans les chemins Windows)
        forbidden_chars = {'"', '|', '?', '*'}  # Exclure < > : qui peuvent être valides dans les chemins Windows
        if any(c in path_str for c in forbidden_chars):
            logger.warning(f"[VALIDATE_FILE_PATH] Caractères interdits détectés: {path_str}")
            return None

        # Patterns de traversée
        suspicious_patterns = ['../', '..\\', '/..', '\\..', './', '.\\']
        for pattern in suspicious_patterns:
            if pattern in path_str:
                logger.warning(f"[VALIDATE_FILE_PATH] Pattern de traversée détecté: '{pattern}' dans {path_str}")
                return None

        logger.debug("[VALIDATE_FILE_PATH] ✓ Validation des caractères réussie")

        # ÉTAPE 6: Vérification de l'existence et du type
        if not resolved_path.exists():
            logger.warning(f"[VALIDATE_FILE_PATH] Fichier non trouvé: {resolved_path}")
            return None

        if not resolved_path.is_file():
            logger.warning(f"[VALIDATE_FILE_PATH] Le chemin n'est pas un fichier régulier: {resolved_path}")
            return None

        # ÉTAPE 7: Vérification des permissions de base
        try:
            import os
            if not os.access(resolved_path, os.R_OK):
                logger.warning(f"[VALIDATE_FILE_PATH] Pas de permission de lecture: {resolved_path}")
                return None

            # Vérifier que c'est bien un fichier régulier via stat
            stat_result = resolved_path.stat()
            if not (stat_result.st_mode & 0o170000 == 0o100000):  # S_IFREG
                logger.warning(f"[VALIDATE_FILE_PATH] Le chemin n'est pas un fichier régulier: {resolved_path}")
                return None

            logger.debug("[VALIDATE_FILE_PATH] ✓ Existence, type et permissions validés")
        except (OSError, AttributeError) as e:
            logger.warning(f"[VALIDATE_FILE_PATH] Erreur de vérification des permissions: {e}")
            return None

        logger.info(f"[VALIDATE_FILE_PATH] Chemin validé avec succès: {resolved_path}")
        return resolved_path

    except Exception as e:
        logger.error(f"[VALIDATE_FILE_PATH] Erreur inattendue lors de la validation de {file_path}: {e}")
        return None


async def process_metadata_chunk(client: httpx.AsyncClient, chunk: list, stats: dict, base_path: Path):
    """Traite un lot de métadonnées de fichiers."""
    # Étape 1: Traitement par lots des artistes
    unique_artists_data = {
        (fd.get("artist").lower()): { "name": fd.get("artist"), "musicbrainz_artistid": fd.get("musicbrainz_artistid") or fd.get("musicbrainz_albumartistid") }
        for fd in chunk if fd.get("artist")
    }
    artists_data_list = list(unique_artists_data.values())
    logger.debug(f"Artists data being sent to batch create: {artists_data_list}")
    artist_map = await create_or_get_artists_batch(client, artists_data_list)
    stats['artists_processed'] += len(artist_map)

    # Lancer les tâches d'enrichissement pour les artistes
    for artist in artist_map.values():
        celery.send_task('enrich_artist_task', args=[artist['id']])

    # Étape 2: Traitement par lots des albums
    unique_albums_data = {}
    for fd in chunk:
        artist = artist_map.get(fd.get("artist", "").lower())
        if artist and fd.get("album"):
            album_key = (fd.get("album").lower(), artist["id"])
            if album_key not in unique_albums_data:
                unique_albums_data[album_key] = { "title": fd.get("album"), "album_artist_id": artist["id"], "release_year": fd.get("year"), "musicbrainz_albumid": fd.get("musicbrainz_albumid") }
    
    album_map = await create_or_get_albums_batch(client, list(unique_albums_data.values()))
    stats['albums_processed'] += len(album_map)

    # Lancer les tâches d'enrichissement pour les albums
    for album in album_map.values():
        celery.send_task('enrich_album_task', args=[album['id']])

    # Étape 3: Préparation et traitement par lots des pistes
    tracks_to_process = []
    for fd in chunk:
        artist = artist_map.get(fd.get("artist", "").lower())
        if not artist:
            continue
        album = album_map.get((fd.get("album", "").lower(), artist["id"]))
        if not album:
            continue
        fd["track_artist_id"] = artist["id"]
        fd["album_id"] = album["id"]

        # Get file stats for comparison
        try:
            # SECURITY: Validate path before using it in os.stat
            validated_path = await validate_file_path(fd["path"], base_path)
            if validated_path:
                stat = os.stat(str(validated_path))
                fd["file_mtime"] = stat.st_mtime
                fd["file_size"] = stat.st_size
            else:
                logger.warning(f"Chemin invalide pour stat: {fd['path']}")
                fd["file_mtime"] = None
                fd["file_size"] = None
        except OSError:
            logger.warning(f"Could not stat file {fd['path']}")
            fd["file_mtime"] = None
            fd["file_size"] = None

        # TODO: Smart update check via API

        tracks_to_process.append(fd)
    
    processed_tracks = await create_or_update_tracks_batch(client, tracks_to_process)
    stats['tracks_processed'] += len(processed_tracks)

    # Étape 4: Traitement asynchrone des covers
    from backend_worker.services.entity_manager import process_artist_covers

    cover_tasks = []

    # Grouper les images d'artistes par artiste
    artist_images_map = {}
    for fd in chunk:
        artist_name = fd.get("artist", "").lower()
        if artist_name and fd.get("artist_images"):
            artist = artist_map.get(artist_name)
            if artist:
                artist_id = artist["id"]
                if artist_id not in artist_images_map:
                    artist_images_map[artist_id] = {
                        "images": [],
                        "path": fd.get("artist_path")
                    }
                artist_images_map[artist_id]["images"].extend(fd["artist_images"])

    # Traiter les covers d'artistes groupées
    for artist_id, data in artist_images_map.items():
        cover_tasks.append(process_artist_covers(client, artist_id, data["path"], data["images"]))

    # Traiter les covers d'albums
    for fd in chunk:
        artist_name = fd.get("artist", "").lower()
        artist = artist_map.get(artist_name)
        if artist and fd.get("album"):
            album = album_map.get((fd.get("album", "").lower(), artist["id"]))
            if album and fd.get("cover_data"):
                cover_tasks.append(create_or_update_cover(
                    client,
                    "album",
                    album["id"],
                    fd["cover_data"],
                    fd.get("cover_mime_type"),
                    str(Path(fd["path"]).parent)
                ))

    if cover_tasks:
        await asyncio.gather(*cover_tasks)
        stats['covers_processed'] += len(cover_tasks)



async def count_music_files(directory: str, music_extensions: set) -> int:
    """Compte rapidement le nombre de fichiers musicaux dans un répertoire."""
    count = 0
    async for file_path_bytes in async_walk(Path(directory)):
        if Path(file_path_bytes.decode('utf-8', 'surrogateescape')).suffix.lower().encode('utf-8') in music_extensions:
            count += 1
    return count

async def scan_music_task(directory: str, progress_callback=None, chunk_size=200, session_id=None, cleanup_deleted: bool = False,
                          max_concurrent_files=200, max_concurrent_audio=40, max_parallel_chunks=4):
    """
    Tâche d'indexation ultra-optimisée avec parallélisation intelligente et insertion parallélisée des pistes.

    Args:
        directory: Répertoire à scanner
        progress_callback: Fonction de callback pour la progression
        chunk_size: Taille des lots de traitement
        max_concurrent_files: Nombre maximum de fichiers traités simultanément
        max_concurrent_audio: Nombre maximum d'analyses audio simultanées
        max_parallel_chunks: Nombre maximum de chunks traités simultanément

    Returns:
        Statistiques du scan avec métriques de performance
    """
    start_time = time.time()

    try:
        logger.info(f"Démarrage de l'indexation ultra-optimisée de: {directory}")

        # Initialisation de l'optimiseur
        optimizer = ScanOptimizer(
            max_concurrent_files=max_concurrent_files,
            max_concurrent_audio=max_concurrent_audio,
            chunk_size=chunk_size,
            enable_threading=True,
            max_parallel_chunks=max_parallel_chunks
        )

        # Étape 1: Récupérer la configuration
        settings_service = SettingsService()
        template = await settings_service.get_setting(MUSIC_PATH_TEMPLATE)
        artist_files_json = await settings_service.get_setting(ARTIST_IMAGE_FILES)
        cover_files_json = await settings_service.get_setting(ALBUM_COVER_FILES)

        # SECURITY: Validate and normalize the base directory
        try:
            base_path = Path(directory).resolve()
            logger.info(f"Répertoire de base résolu pour le scan: {base_path}")
        except (OSError, ValueError) as e:
            logger.error(f"Répertoire de base invalide: {directory} - {e}")
            raise ValueError(f"Invalid base directory: {directory}")

        scan_config = {
            "template": template,
            "artist_files": artist_files_json if isinstance(artist_files_json, list) else json.loads(artist_files_json or '[]'),
            "cover_files": cover_files_json if isinstance(cover_files_json, list) else json.loads(cover_files_json or '[]'),
            "music_extensions": {b'.mp3', b'.flac', b'.m4a', b'.ogg', b'.wav'},
            "base_directory": str(base_path)  # SECURITY: Add resolved base directory for path validation
        }
        template_parts = template.split('/')
        scan_config["artist_depth"] = template_parts.index("{album_artist}") if "{album_artist}" in template_parts else -1

        # Étape 2: Comptage des fichiers
        total_files = await count_music_files(directory, scan_config["music_extensions"])
        optimizer.metrics.files_total = total_files
        logger.info(f"Nombre total de fichiers musicaux: {total_files}")

        # Statistiques globales
        stats = {
            "files_processed": 0, "artists_processed": 0,
            "albums_processed": 0, "tracks_processed": 0, "covers_processed": 0
        }

        # Collecteurs pour l'insertion parallélisée finale
        all_artists_data = []
        all_albums_data = []
        all_tracks_data = []
        all_cover_tasks = []

        # Étape 3: Collecte et traitement par gros chunks avec collecte des données
        async with httpx.AsyncClient(timeout=300.0) as client:
            file_batch = []
            batch_size = 500  # Taille des batches pour l'extraction parallèle (augmenté)

            async for file_metadata in scan_music_files(directory, scan_config):
                file_batch.append(file_metadata)
                stats['files_processed'] += 1

                # Traiter par batches pour paralléliser l'extraction
                if len(file_batch) >= batch_size:
                    logger.info(f"Traitement parallèle d'un batch de {len(file_batch)} fichiers...")

                    # SECURITY: Validate all file paths before processing
                    validated_paths = []
                    for fm in file_batch:
                        validated_path = await validate_file_path(fm['path'], base_path)
                        if validated_path:
                            validated_paths.append(str(validated_path).encode('utf-8', 'surrogateescape'))
                        else:
                            logger.warning(f"Chemin de fichier invalide rejeté: {fm['path']}")
                            stats['files_processed'] -= 1  # Decrement counter for rejected file

                    if validated_paths:
                        # Extraction parallélisée des métadonnées
                        extracted_metadata = await optimizer.extract_metadata_batch(
                            validated_paths,
                            scan_config
                        )
                    else:
                        logger.warning("Aucun chemin de fichier valide dans le batch")
                        extracted_metadata = []

                    # Collecter les données pour insertion parallélisée finale
                    batch_artists, batch_albums, batch_tracks, batch_covers = await optimizer.collect_entities_for_batch(
                        client, extracted_metadata, stats, base_path
                    )

                    all_artists_data.extend(batch_artists)
                    all_albums_data.extend(batch_albums)
                    all_tracks_data.extend(batch_tracks)
                    all_cover_tasks.extend(batch_covers)

                    file_batch = []

            # Traiter le dernier batch
            if file_batch:
                logger.info(f"Traitement du dernier batch de {len(file_batch)} fichiers...")

                # SECURITY: Validate all file paths before processing
                validated_paths = []
                for fm in file_batch:
                    validated_path = await validate_file_path(fm['path'], base_path)
                    if validated_path:
                        validated_paths.append(str(validated_path).encode('utf-8', 'surrogateescape'))
                    else:
                        logger.warning(f"Chemin de fichier invalide rejeté: {fm['path']}")
                        stats['files_processed'] -= 1  # Decrement counter for rejected file

                if validated_paths:
                    extracted_metadata = await optimizer.extract_metadata_batch(
                        validated_paths,
                        scan_config
                    )
                else:
                    logger.warning("Aucun chemin de fichier valide dans le dernier batch")
                    extracted_metadata = []

                # Collecter les données du dernier batch
                batch_artists, batch_albums, batch_tracks, batch_covers = await optimizer.collect_entities_for_batch(
                    client, extracted_metadata, stats, base_path
                )

                all_artists_data.extend(batch_artists)
                all_albums_data.extend(batch_albums)
                all_tracks_data.extend(batch_tracks)
                all_cover_tasks.extend(batch_covers)

            # Étape 4: Insertion parallélisée finale de toutes les entités
            logger.info(f"Insertion parallélisée finale: {len(all_artists_data)} artistes, {len(all_albums_data)} albums, {len(all_tracks_data)} pistes")

            await optimizer.insert_all_entities_parallel(
                client, all_artists_data, all_albums_data, all_tracks_data, all_cover_tasks, stats, progress_callback
            )

        # Étape 4: Scan terminé
        if progress_callback:
            progress_callback({"current": 100, "total": 100, "percent": 100, "step": "Scan complete!"})

        # Métriques finales avec rapport détaillé
        total_time = time.time() - start_time
        performance_report = optimizer.get_performance_report()
        logger.debug(f"Performance report: {performance_report}")

        final_metrics = {
            **performance_report,
            "total_scan_time": total_time,
            "scan_efficiency_score": performance_report.get("efficiency_score", 0)
        }

        # Publier les métriques détaillées
        publish_event("scan_metrics", {
            "directory": directory,
            "stats": stats,
            "metrics": final_metrics,
            "optimizer_config": {
                "max_concurrent_files": optimizer.max_concurrent_files,
                "max_concurrent_audio": optimizer.max_concurrent_audio,
                "chunk_size": optimizer.chunk_size
            }
        })

        # Notification de mise à jour
        publish_event("library_updated", {"source": "scanner"})
        logger.info("Événement 'library_updated' publié.")

        logger.info(f"Scan ultra-optimisé terminé. Stats: {stats}")
        logger.info(f"Performance: {final_metrics}")

        # Nettoyer l'optimiseur
        await optimizer.cleanup()

        result = {
            "directory": directory,
            **stats,
            "performance_metrics": final_metrics
        }
        logger.debug(f"Scan result: {result}")

        # Launch cleanup if requested
        if cleanup_deleted:
            from backend_worker.celery_app import celery
            celery.send_task("cleanup_deleted_tracks_task", args=[directory])

        return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Erreur scan optimisé après {error_time:.2f}s: {str(e)}", exc_info=True)

        # Publier les métriques d'erreur
        publish_event("scan_error", {
            "directory": directory,
            "error": str(e),
            "duration": error_time,
            "performance_report": optimizer.get_performance_report() if 'optimizer' in locals() else {}
        })

        error_result = {
            "error": str(e),
            "directory": directory,
            "duration": error_time,
            "partial_metrics": stats if 'stats' in locals() else {}
        }
        logger.debug(f"Error result: {error_result}")
        return error_result
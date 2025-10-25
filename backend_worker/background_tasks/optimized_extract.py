"""
TÂCHES D'EXTRACTION OPTIMISÉES POUR HAUTE PERFORMANCE

Extraction massive et parallélisée des métadonnées audio avec ThreadPoolExecutor
pour maximiser l'utilisation CPU.
"""

import asyncio
import time
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event




def extract_single_file_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extrait les métadonnées d'un fichier unique (fonction synchrone pour ThreadPoolExecutor).

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
            get_cover_art, convert_to_base64
        )
        from backend_worker.services.audio_features_service import extract_audio_features

        # Validation et sanitisation du chemin
        try:
            sanitized_path = sanitize_path(file_path)
            file_path_obj = Path(sanitized_path)
        except ValueError as e:
            logger.warning(f"[EXTRACT] Chemin invalide {file_path}: {e}")
            return None

        # Vérification existence fichier
        if not file_path_obj.exists() or not file_path_obj.is_file():
            logger.warning(f"[EXTRACT] Fichier inexistant: {file_path}")
            return None

        # Ouverture et lecture du fichier
        try:
            audio = File(file_path, easy=False)
            if audio is None:
                logger.warning(f"[EXTRACT] Impossible de lire: {file_path}")
                return None
        except Exception as e:
            logger.error(f"[EXTRACT] Erreur lecture {file_path}: {e}")
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

            # Extraction des caractéristiques audio (si fichier accessible)
            try:
                # Pour l'instant, on ne fait que l'extraction de base
                # L'analyse audio complète sera faite plus tard si nécessaire
                audio_features = {
                    "bpm": None,
                    "key": None,
                    "scale": None,
                    "danceability": None,
                    "mood_happy": None,
                    "mood_aggressive": None,
                    "mood_party": None,
                    "mood_relaxed": None,
                    "instrumental": None,
                    "acoustic": None,
                    "tonal": None,
                    "genre_main": None,
                    "camelot_key": None,
                }
                metadata.update(audio_features)

            except Exception as e:
                logger.debug(f"[EXTRACT] Pas de caractéristiques audio pour {file_path}: {e}")

            # Nettoyer les valeurs None
            metadata = {k: v for k, v in metadata.items() if v is not None}

            logger.debug(f"[EXTRACT] Métadonnées extraites: {file_path}")
            return metadata

        except Exception as e:
            logger.error(f"[EXTRACT] Erreur traitement {file_path}: {e}")
            return None

    except Exception as e:
        logger.error(f"[EXTRACT] Erreur générale {file_path}: {e}")
        return None


@celery.task(name='extract_metadata_batch', queue='extract', bind=True)
def extract_metadata_batch(self, file_paths: List[str], batch_id: str = None):
    """
    Extrait les métadonnées de milliers de fichiers en parallèle avec ThreadPoolExecutor.

    Args:
        file_paths: Liste des chemins de fichiers à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Liste des métadonnées extraites
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[EXTRACT] Démarrage extraction batch: {len(file_paths)} fichiers")
        logger.info(f"[EXTRACT] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[EXTRACT] Batch ID: {batch_id}")

        # Validation des chemins
        valid_paths = []
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_paths.append(file_path)
            else:
                logger.warning(f"[EXTRACT] Fichier invalide ignoré: {file_path}")

        if not valid_paths:
            logger.warning("[EXTRACT] Aucun fichier valide dans le batch")
            return []

        logger.info(f"[EXTRACT] Fichiers valides: {len(valid_paths)}/{len(file_paths)}")

        # Configuration ThreadPoolExecutor optimisée
        # Utiliser tous les cœurs disponibles avec une marge pour l'OS
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), 32)

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
                    metadata = future.result(timeout=300)  # 5 minutes timeout par fichier
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
                            'step': f'Extracted {completed}/{len(valid_paths)} files'
                        })

                except Exception as e:
                    logger.error(f"[EXTRACT] Erreur traitement fichier: {e}")
                    completed += 1

        # Métriques de performance
        total_time = time.time() - start_time
        files_per_second = len(extracted_metadata) / total_time if total_time > 0 else 0

        logger.info(f"[EXTRACT] Extraction terminée: {len(extracted_metadata)}/{len(valid_paths)} fichiers en {total_time:.2f}s")
        logger.info(f"[EXTRACT] Performance: {files_per_second:.2f} fichiers/seconde")

        # Publier les métriques
        publish_event("extract_progress", {
            "task_id": task_id,
            "batch_id": batch_id,
            "files_processed": len(extracted_metadata),
            "files_total": len(valid_paths),
            "extraction_time": total_time,
            "files_per_second": files_per_second
        })

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
        logger.error(f"[EXTRACT] Erreur batch après {error_time:.2f}s: {str(e)}")

        # Publier l'erreur
        publish_event("extract_error", {
            "task_id": task_id,
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        })

        raise


@celery.task(name='extract_audio_features_batch', queue='extract')
def extract_audio_features_batch(metadata_list: List[Dict], force_analysis: bool = False):
    """
    Extrait les caractéristiques audio pour un lot de métadonnées.

    Args:
        metadata_list: Liste des métadonnées avec chemins de fichiers
        force_analysis: Forcer l'analyse même si déjà présente

    Returns:
        Liste des métadonnées enrichies avec caractéristiques audio
    """
    start_time = time.time()

    try:
        logger.info(f"[EXTRACT_AUDIO] Traitement de {len(metadata_list)} fichiers")

        # Filtrer les fichiers qui ont besoin d'analyse
        files_to_analyze = []
        for metadata in metadata_list:
            file_path = metadata.get('path')
            if file_path and os.path.exists(file_path):
                # Vérifier si l'analyse est nécessaire
                has_audio_features = any(
                    metadata.get(key) is not None
                    for key in ['bpm', 'key', 'danceability', 'mood_happy']
                )

                if not has_audio_features or force_analysis:
                    files_to_analyze.append(metadata)

        if not files_to_analyze:
            logger.info("[EXTRACT_AUDIO] Tous les fichiers ont déjà des caractéristiques audio")
            return metadata_list

        logger.info(f"[EXTRACT_AUDIO] Analyse nécessaire pour {len(files_to_analyze)}/{len(metadata_list)} fichiers")

        # Analyse audio avec ThreadPoolExecutor
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), 16)

        enriched_metadata = list(metadata_list)  # Copie de la liste originale

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Analyser les fichiers en parallèle
            future_to_index = {}

            for i, metadata in enumerate(files_to_analyze):
                file_path = metadata.get('path')
                if file_path:
                    future = executor.submit(analyze_single_audio_file, file_path)
                    future_to_index[future] = i

            # Collecter les résultats
            for future in future_to_index:
                try:
                    audio_features = future.result(timeout=600)  # 10 minutes timeout
                    if audio_features:
                        # Trouver l'index correspondant dans la liste enrichie
                        original_index = future_to_index[future]
                        if original_index < len(enriched_metadata):
                            # Fusionner les caractéristiques audio
                            enriched_metadata[original_index].update(audio_features)

                except Exception as e:
                    logger.error(f"[EXTRACT_AUDIO] Erreur analyse fichier: {e}")

        total_time = time.time() - start_time
        logger.info(f"[EXTRACT_AUDIO] Analyse terminée en {total_time:.2f}s")

        return enriched_metadata

    except Exception as e:
        logger.error(f"[EXTRACT_AUDIO] Erreur batch: {e}")
        return metadata_list


def analyze_single_audio_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Analyse un fichier audio unique (fonction synchrone).

    Args:
        file_path: Chemin du fichier à analyser

    Returns:
        Dictionnaire de caractéristiques audio
    """
    try:
        # Import ici pour éviter les imports circulaires
        from backend_worker.services.audio_features_service import extract_audio_features

        # Extraire les caractéristiques audio
        audio_features = extract_audio_features(
            audio=None,  # Pas d'objet Mutagen
            tags={},     # Pas de tags
            file_path=file_path
        )

        if audio_features:
            logger.debug(f"[ANALYZE] Caractéristiques extraites: {file_path}")
            return audio_features
        else:
            logger.debug(f"[ANALYZE] Pas de caractéristiques: {file_path}")
            return {}

    except Exception as e:
        logger.error(f"[ANALYZE] Erreur analyse {file_path}: {e}")
        return None
"""
Tâches Celery pour l'analyse audio avec Librosa.

Ce module contient les tâches asynchrones pour l'extraction des caractéristiques audio
(BPM, tonalité, spectral) en utilisant Librosa comme fallback quand les tags AcoustID
ne sont pas disponibles.
"""

from typing import Dict, Any, Optional
from celery import shared_task

from backend_worker.services.audio_features_service import extract_audio_features
from backend_worker.utils.logging import logger as task_logger

logger = task_logger


@shared_task(
    name="backend_worker.tasks.audio_analysis_tasks.analyze_track_audio_features",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="audio_analysis",
)
def analyze_track_audio_features(
    self,
    track_id: int,
    file_path: str,
    acoustid_tags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyse les caractéristiques audio d'une piste avec Librosa.

    Cette tâche est utilisée comme fallback quand les tags AcoustID ne sont pas
    disponibles ou incomplets. Elle extrait les caractéristiques audio directement
    depuis le fichier audio en utilisant Librosa.

    Args:
        track_id: ID de la piste dans la base de données
        file_path: Chemin vers le fichier audio
        acoustid_tags: Tags AcoustID optionnels (si disponibles)

    Returns:
        Dictionnaire contenant les caractéristiques audio extraites :
        - bpm: BPM détecté
        - key: Tonalité détectée
        - mode: Mode (majeur/mineur)
        - danceability: Score de danceabilité
        - energy: Score d'énergie
        - acousticness: Score d'acousticité
        - instrumentalness: Score d'instrumentalité
        - liveness: Score de liveness
        - speechiness: Score de speechiness
        - valence: Score de valence

    Raises:
        Exception: Si l'analyse échoue après 3 tentatives
    """
    logger.info(
        f"Analyse audio pour track_id={track_id}, file_path={file_path}",
        extra={"track_id": track_id, "file_path": file_path},
    )

    try:
        # Importer mutagen pour lire les métadonnées du fichier
        from mutagen import File

        # Charger le fichier audio avec mutagen
        audio = File(file_path, easy=True)

        if audio is None:
            logger.error(
                f"Impossible de charger le fichier audio: {file_path}",
                extra={"track_id": track_id, "file_path": file_path},
            )
            return {
                "track_id": track_id,
                "success": False,
                "error": "Impossible de charger le fichier audio",
            }

        # Extraire les caractéristiques audio (tags AcoustID d'abord, puis Librosa en fallback)
        features = extract_audio_features(
            audio=audio,
            tags=acoustid_tags or {},
            file_path=file_path,
            track_id=track_id
        )

        # Ajouter le track_id au résultat
        features["track_id"] = track_id
        features["success"] = True

        logger.info(
            f"Analyse audio réussie pour track_id={track_id}: "
            f"BPM={features.get('bpm')}, Key={features.get('key')}",
            extra={
                "track_id": track_id,
                "bpm": features.get("bpm"),
                "key": features.get("key"),
            },
        )

        return features

    except ImportError as e:
        logger.error(
            f"Dépendance manquante pour l'analyse audio: {e}",
            extra={"track_id": track_id, "error": str(e)},
        )
        return {
            "track_id": track_id,
            "success": False,
            "error": f"Dépendance manquante: {str(e)}",
        }

    except Exception as e:
        logger.error(
            f"Erreur lors de l'analyse audio pour track_id={track_id}: {e}",
            extra={"track_id": track_id, "error": str(e)},
            exc_info=True,
        )

        # Retenter la tâche si ce n'est pas la dernière tentative
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retentative {self.request.retries + 1}/{self.max_retries} "
                f"pour track_id={track_id}",
                extra={"track_id": track_id, "retry": self.request.retries + 1},
            )
            raise self.retry(exc=e)

        return {
            "track_id": track_id,
            "success": False,
            "error": str(e),
        }


@shared_task(
    name="backend_worker.tasks.audio_analysis_tasks.batch_analyze_tracks",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="audio_analysis",
)
def batch_analyze_tracks(
    self,
    tracks_data: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyse en lot les caractéristiques audio de plusieurs pistes.

    Args:
        tracks_data: Liste de dictionnaires contenant track_id et file_path

    Returns:
        Dictionnaire contenant les résultats de l'analyse pour chaque piste
    """
    logger.info(
        f"Analyse audio en lot pour {len(tracks_data)} pistes",
        extra={"track_count": len(tracks_data)},
    )

    results = {
        "total": len(tracks_data),
        "success": 0,
        "failed": 0,
        "tracks": [],
    }

    for track_data in tracks_data:
        track_id = track_data.get("track_id")
        file_path = track_data.get("file_path")
        acoustid_tags = track_data.get("acoustid_tags")

        if not track_id or not file_path:
            logger.warning(
                f"Données incomplètes pour l'analyse: {track_data}",
                extra={"track_data": track_data},
            )
            results["failed"] += 1
            continue

        try:
            # Analyser la piste
            result = analyze_track_audio_features(
                track_id=track_id,
                file_path=file_path,
                acoustid_tags=acoustid_tags,
            )

            results["tracks"].append(result)

            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            logger.error(
                f"Erreur lors de l'analyse de track_id={track_id}: {e}",
                extra={"track_id": track_id, "error": str(e)},
                exc_info=True,
            )
            results["failed"] += 1
            results["tracks"].append(
                {
                    "track_id": track_id,
                    "success": False,
                    "error": str(e),
                }
            )

    logger.info(
        f"Analyse en lot terminée: {results['success']} succès, {results['failed']} échecs",
        extra=results,
    )

    return results

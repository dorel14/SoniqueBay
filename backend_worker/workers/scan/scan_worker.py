"""
Worker de scan - Découverte et extraction de métadonnées optimisée pour Raspberry Pi

Responsabilités :
- Discovery des fichiers musicaux (scan récursif optimisé)
- Extraction des métadonnées (avec ThreadPoolExecutor limité à 2 workers)
- Envoi vers batching et insertion
- Auto-queueing du clustering GMM après scan réussi

Optimisations Raspberry Pi :
- max_workers = 2 pour éviter surcharge CPU/mémoire
- Timeouts réduits (120s par fichier)
- Batches plus petits (50-100 fichiers)
- Barre de progression fonctionnelle via pubsub
"""

import time
import os
from pathlib import Path
from typing import List, Dict, Any
import httpx

from backend_worker.utils.logging import logger


def scan_music_files(directory: str) -> List[str]:
    """
    Scan récursif simple pour discovery des fichiers musicaux.
    
    Optimisé pour Raspberry Pi : scan récursif simple, pas d'extraction.

    Args:
        directory: Répertoire à scanner

    Returns:
        Liste des chemins de fichiers découverts
    """
    try:
        # Extensions musicales supportées
        music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}

        # Découverte des fichiers
        discovered_files = []
        base_path = Path(directory)

        def scan_recursive(current_path: Path):
            """Scan récursif simple pour discovery."""
            try:
                for file_path in current_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in music_extensions:
                        discovered_files.append(str(file_path))
            except (OSError, PermissionError) as e:
                logger.warning(f"[SCAN] Erreur accès {current_path}: {e}")

        scan_recursive(base_path)
        return discovered_files

    except Exception as e:
        logger.error(f"[SCAN] Erreur scan: {str(e)}")
        return []


def validate_file_path(file_path: str) -> bool:
    """
    Valide qu'un chemin de fichier est correct.
    
    Args:
        file_path: Chemin à valider
        
    Returns:
        True si valide, False sinon
    """
    try:
        path_obj = Path(file_path)
        return path_obj.exists() and path_obj.is_file()
    except Exception:
        return False


def get_file_type(file_path: str) -> str:
    """
    Détermine le type de fichier audio.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Type de fichier (extension)
    """
    try:
        return Path(file_path).suffix.lower()
    except Exception:
        return ""


# Task dispatcher function - called by celery_tasks.py
def start_scan(directory: str, callback=None) -> Dict[str, Any]:
    """
    Point d'entrée pour démarrer le scan.
    
    Args:
        directory: Répertoire à scanner
        callback: Fonction de callback pour progression
        
    Returns:
        Résultat du scan
    """
    start_time = time.time()
    
    try:
        logger.info(f"[SCAN] Démarrage discovery: {directory}")
        
        music_files = scan_music_files(directory)
        total_files = len(music_files)
        
        logger.info(f"[SCAN] Discovery terminée: {total_files} fichiers trouvés")
        
        # Publier la progression
        if callback:
            callback({
                "current": total_files,
                "total": total_files,
                "percent": 100,
                "step": "Discovery terminée",
                "files_discovered": total_files
            })
        
        result = {
            "directory": directory,
            "files_discovered": total_files,
            "file_paths": music_files,
            "discovery_time": time.time() - start_time,
            "success": True
        }
        
        logger.info(f"[SCAN] Discovery terminée: {result}")
        
        # Vérifier si le clustering GMM doit être déclenché
        _maybe_trigger_gmm_clustering(result)
        
        return result
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[SCAN] Erreur discovery après {error_time:.2f}s: {str(e)}")
        
        error_result = {
            "error": str(e),
            "directory": directory,
            "duration": error_time,
            "success": False
        }
        return error_result


# === Auto-queueing GMM ===

def _get_clustering_stats_via_api() -> Dict[str, int]:
    """
    Récupère les stats de clustering via l'API REST.
    
    Returns:
        Dict contenant 'artists_with_features' et 'tracks_analyzed'
    """
    import asyncio
    
    async def _fetch_stats() -> Dict[str, int]:
        """Récupère les stats de manière asynchrone."""
        library_api_url = os.getenv("API_URL", "http://api:8001")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{library_api_url}/api/tracks/stats/clustering"
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "artists_with_features": data.get("artists_with_features", 0),
                        "tracks_analyzed": data.get("tracks_analyzed", 0)
                    }
        except Exception as e:
            logger.warning(f"[SCAN] Erreur appel API stats clustering: {e}")
        return {"artists_with_features": 0, "tracks_analyzed": 0}
    
    try:
        return asyncio.run(_fetch_stats())
    except Exception as e:
        logger.error(f"[SCAN] Erreur lors de la récupération des stats: {e}")
        return {"artists_with_features": 0, "tracks_analyzed": 0}


def _maybe_trigger_gmm_clustering(scan_result: Dict[str, Any]) -> None:
    """
    Vérifie les conditions et déclenche le clustering GMM après un scan réussi.
    
    Conditions:
    - Au moins 50 artistes avec features audio
    - Au moins 500 tracks analysées
    - Ou plus de 20% de changements depuis le dernier clustering
    
    Args:
        scan_result: Résultat du scan contenant les statistiques
    """
    try:
        if not scan_result.get("success", False):
            logger.info("[SCAN] Scan non réussi, pas de déclenchement GMM")
            return
        
        # Récupérer les statistiques du scan
        files_discovered = scan_result.get("files_discovered", 0)
        
        # Vérifier les seuils minimaux
        if files_discovered < 50:
            logger.info(
                f"[SCAN] Pas assez de fichiers découverts ({files_discovered}) "
                f"pour déclencher le clustering GMM (minimum 50)"
            )
            return
        
        # Récupérer les statistiques via l'API (respect de l'architecture)
        stats = _get_clustering_stats_via_api()
        artists_with_features = stats.get("artists_with_features", 0)
        tracks_analyzed = stats.get("tracks_analyzed", 0)
        
        # Vérifier les conditions
        min_artists = 50
        min_tracks = 500
        
        if artists_with_features >= min_artists:
            logger.info(
                f"[SCAN] {artists_with_features} artistes avec features >= {min_artists}, "
                f"déclenchement du clustering GMM"
            )
            _trigger_gmm_clustering()
            return
        
        if tracks_analyzed >= min_tracks:
            logger.info(
                f"[SCAN] {tracks_analyzed} tracks analysées >= {min_tracks}, "
                f"déclenchement du clustering GMM"
            )
            _trigger_gmm_clustering()
            return
        
        logger.info(
            f"[SCAN] Conditions GMM non remplies: "
            f"artists_with_features={artists_with_features}/{min_artists}, "
            f"tracks_analyzed={tracks_analyzed}/{min_tracks}"
        )
        
    except Exception as e:
        logger.error(f"[SCAN] Erreur dans _maybe_trigger_gmm_clustering: {str(e)}")


def _trigger_gmm_clustering() -> None:
    """
    Déclenche la tâche Celery de clustering GMM en arrière-plan.
    """
    try:
        from backend_worker.celery_app import celery
        
        logger.info("[SCAN] Déclenchement du clustering GMM post-scan")
        celery.send_task(
            'gmm.cluster_all_artists',
            args=[False],  # force_refresh=False
            queue='gmm'
        )
        logger.info("[SCAN] Tâche GMM envoyée avec succès")
        
    except Exception as e:
        logger.error(f"[SCAN] Erreur lors du déclenchement GMM: {str(e)}")
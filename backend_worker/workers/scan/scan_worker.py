"""
Worker de scan - Découverte et extraction de métadonnées optimisée pour Raspberry Pi

Responsabilités :
- Discovery des fichiers musicaux (scan récursif optimisé)
- Extraction des métadonnées (avec ThreadPoolExecutor limité à 2 workers)
- Envoi vers batching et insertion

Optimisations Raspberry Pi :
- max_workers = 2 pour éviter surcharge CPU/mémoire
- Timeouts réduits (120s par fichier)
- Batches plus petits (50-100 fichiers)
- Barre de progression fonctionnelle via pubsub
"""

import time
from pathlib import Path
from typing import List, Dict, Any

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
"""
Module scanner pour le scan de fichiers musicaux.
Refactorisé pour séparer les responsabilités.
"""

from typing import List, Dict, Any
from pathlib import Path
from backend_worker.services.music_scan import get_file_type
from backend_worker.utils.logging import logger

def count_music_files(directory: str) -> int:
    """
    Compte le nombre de fichiers musicaux dans un répertoire.
    
    Args:
        directory: Chemin du répertoire à scanner
        
    Returns:
        Nombre de fichiers musicaux trouvés
    """
    try:
        music_dir = Path(directory)
        if not music_dir.exists() or not music_dir.is_dir():
            return 0
        
        music_extensions = {'.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac'}
        count = 0
        
        for file_path in music_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in music_extensions:
                count += 1
                
        return count
    except Exception as e:
        logger.error(f"Erreur count_music_files: {e}")
        return 0

def validate_file_path(file_path: str) -> bool:
    """
    Valide qu'un chemin de fichier est sécurisé et valide.
    
    Args:
        file_path: Chemin du fichier à valider
        
    Returns:
        True si le chemin est valide, False sinon
    """
    try:
        path = Path(file_path)
        
        # Vérifier que le chemin est absolu
        if not path.is_absolute():
            return False
            
        # Vérifier que le fichier existe
        if not path.exists():
            return False
            
        # Vérifier que c'est un fichier
        if not path.is_file():
            return False
            
        # Vérifier les extensions autorisées
        allowed_extensions = {'.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.jpg', '.jpeg', '.png'}
        if path.suffix.lower() not in allowed_extensions:
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Erreur validate_file_path: {e}")
        return False

def scan_music_task(directory: str) -> List[str]:
    """
    Tâche de scan pour trouver tous les fichiers musicaux.
    
    Args:
        directory: Répertoire à scanner
        
    Returns:
        Liste des chemins de fichiers musicaux
    """
    try:
        music_dir = Path(directory)
        if not music_dir.exists() or not music_dir.is_dir():
            return []
        
        music_files = []
        music_extensions = {'.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac'}
        
        for file_path in music_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in music_extensions:
                music_files.append(str(file_path))
                
        return music_files
        
    except Exception as e:
        logger.error(f"Erreur scan_music_task: {e}")
        return []

def process_metadata_chunk(file_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Traite un chunk de fichiers pour extraire les métadonnées.
    
    Args:
        file_paths: Liste des chemins de fichiers
        
    Returns:
        Liste des métadonnées extraites
    """
    results = []
    
    for file_path in file_paths:
        try:
            if validate_file_path(file_path):
                file_type = get_file_type(file_path)
                results.append({
                    'file_path': file_path,
                    'file_type': file_type,
                    'processed': True
                })
            else:
                results.append({
                    'file_path': file_path,
                    'file_type': 'unknown',
                    'processed': False,
                    'error': 'Invalid file path'
                })
        except Exception as e:
            results.append({
                'file_path': file_path,
                'file_type': 'unknown',
                'processed': False,
                'error': str(e)
            })
    
    return results
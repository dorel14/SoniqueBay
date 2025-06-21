from fastapi import APIRouter, HTTPException, status
from backend.utils.celery_app import celery
#from backend.background_tasks.tasks import index_music_task
from helpers.logging import logger
import os


router = APIRouter(prefix="/api", tags=["scan"])

def convert_path_to_docker(input_path: str) -> str:
    """Convertit un chemin Windows en chemin Docker."""
    try:
        # Détecter si c'est un chemin Windows
        if ':' in input_path:
            # Extraire le chemin après la lettre du lecteur (Y:\)
            path = input_path.split(':', 1)[1]
            # Nettoyer le chemin et le convertir au format Unix
            clean_path = path.replace('\\', '/').lstrip('/')
            # Construire le chemin Docker
            docker_path = f"/music/{clean_path}"
            logger.info(f"Conversion chemin: {input_path} -> {docker_path}")
            return docker_path
        return input_path
    except Exception as e:
        logger.error(f"Erreur conversion chemin: {str(e)}")
        return input_path

@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def launch_scan(directory: str):
    try:
        # Log des variables d'environnement
        logger.info(f"MUSIC_PATH: {os.getenv('MUSIC_PATH')}")
        logger.info(f"PLATFORM: {os.getenv('PLATFORM')}")
        
        docker_directory = convert_path_to_docker(directory)
        logger.info(f"Tentative d'accès au chemin Docker: {docker_directory}")
        
        # Vérifier les permissions et l'existence du dossier racine
        try:
            path_to_scan=f'/music/{directory}' 
            logger.info("Test d'accès au dossier /music:")
            music_stat = os.stat(path_to_scan)
            logger.info(f"Permissions {path_to_scan} {oct(music_stat.st_mode)}")
            logger.info("Contenu de {path_to_scan}:")
            for item in os.listdir(path_to_scan):
                full_path = os.path.join(path_to_scan, item)
                logger.info(f"  - {item} ({'dossier' if os.path.isdir(full_path) else 'fichier'})")
        except Exception as e:
            logger.error(f"Erreur accès {path_to_scan}: {str(e)}")

        # Convertir le chemin Windows en chemin Docker
        docker_directory = convert_path_to_docker(path_to_scan)
        logger.info(f"Tentative d'accès au chemin Docker: {docker_directory}")
        
        # Lister le contenu pour déboguer
        try:
            logger.info("Contenu de {path_to_scan}:")
            for item in os.listdir(path_to_scan):
                logger.info(f"  - {item}")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du dossier {path_to_scan}: {e}")
        
        # Vérifier que le chemin existe
        if not os.path.exists(docker_directory):
            logger.error(f"Chemin non trouvé dans Docker: {docker_directory}")
            raise HTTPException(
                status_code=400,
                detail=f"Le répertoire {path_to_scan} n'est pas accessible dans le conteneur"
            )
        result = celery.send_task("scan_music_task", args=[docker_directory])
        return {"task_id": result.id, "status": f"Scan lancé avec succès sur {docker_directory}"}

    except Exception as e:
        logger.error(f"Erreur lancement scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


from token import OP
from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.utils.celery_app import celery
from backend.utils.logging import logger
import os


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Prevent extra fields

    directory: Optional[str] = None


router = APIRouter(prefix="/api", tags=["scan"])

def convert_path_to_docker(input_path: str) -> str:
    """Convertit un chemin Windows en chemin Unix."""
    try:
        # Détecter si c'est un chemin Windows
        if ':' in input_path:
            # Extraire le chemin après la lettre du lecteur (Y:\)
            path = input_path.split(':', 1)[1]
            # Nettoyer le chemin et le convertir au format Unix
            clean_path = path.replace('\\', '/')
            logger.info(f"Conversion chemin: {input_path} -> {clean_path}")
            return clean_path
        return input_path
    except Exception as e:
        logger.error(f"Erreur conversion chemin: {str(e)}")
        return input_path

@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def launch_scan(request: Optional[ScanRequest] = Body(None)):
    """Lance un scan de la bibliothèque musicale."""
    try:
        # Convertir le répertoire si fourni, sinon utiliser le répertoire par défaut
        if not request or not request.directory:
            docker_directory = os.getenv('MUSIC_PATH', '/music')
        else:
            # Convertir les chemins Windows en chemins Unix
            converted_directory = convert_path_to_docker(request.directory)
            docker_directory = f'/music/{converted_directory.lstrip("/")}'

        # Log des variables d'environnement
        logger.info(f"MUSIC_PATH: {os.getenv('MUSIC_PATH')}")
        logger.info(f"PLATFORM: {os.getenv('PLATFORM')}")
        logger.info(f"Répertoire à scanner: {docker_directory}")

        # Vérifier les permissions et l'existence du dossier
        if not os.path.exists(docker_directory):
            logger.error(f"Chemin non trouvé dans Docker: {docker_directory}")
            raise HTTPException(
                status_code=400,
                detail=f"Le répertoire {docker_directory} n'est pas accessible dans le conteneur"
            )

        # Tester l'accès au répertoire
        try:
            music_stat = os.stat(docker_directory)
            logger.info(f"Permissions {docker_directory} {oct(music_stat.st_mode)}")
            # Tester os.listdir pour vérifier les permissions de lecture
            os.listdir(docker_directory)
        except PermissionError:
            logger.error(f"Permissions insuffisantes pour {docker_directory}")
            raise HTTPException(
                status_code=400,
                detail=f"Le répertoire {docker_directory} n'est pas accessible"
            )
        except Exception as e:
            logger.error(f"Erreur système lors de l'accès à {docker_directory}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur système: {str(e)}"
            )

        result = celery.send_task("scan_music_task", args=[docker_directory])
        return {"task_id": result.id, "status": f"Scan lancé avec succès sur {docker_directory}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lancement scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


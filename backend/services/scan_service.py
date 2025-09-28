"""
Service métier pour le scan de la bibliothèque musicale.
Déplace toute la logique métier depuis scan_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.utils.celery_app, backend.utils.logging
"""
from backend.utils.celery_app import celery
from backend.utils.logging import logger
import os
from backend.api.models.scan_sessions_model import ScanSession
from sqlalchemy.orm import Session

class ScanService:
    @staticmethod
    def convert_path_to_docker(input_path: str) -> str:
        try:
            if ':' in input_path:
                path = input_path.split(':', 1)[1]
                clean_path = path.replace('\\', '/')
                logger.info(f"Conversion chemin: {input_path} -> {clean_path}")
                return clean_path
            return input_path
        except Exception as e:
            logger.error(f"Erreur conversion chemin: {str(e)}")
            return input_path

    @staticmethod
    def launch_scan(directory: str = None, db: Session = None, cleanup_deleted: bool = False):
        if not directory:
            docker_directory = os.getenv('MUSIC_PATH', '/music')
        else:
            converted_directory = ScanService.convert_path_to_docker(directory)
            docker_directory = f'/music/{converted_directory.lstrip('/')}'
        logger.info(f"MUSIC_PATH: {os.getenv('MUSIC_PATH')}")
        logger.info(f"PLATFORM: {os.getenv('PLATFORM')}")
        logger.info(f"Répertoire à scanner: {docker_directory}")

        # Check for existing active scan
        if db:
            existing_scan = db.query(ScanSession).filter(
                ScanSession.directory == docker_directory,
                ScanSession.status.in_(['running', 'paused'])
            ).first()
            if existing_scan:
                logger.warning(f"Scan already active for {docker_directory}, task_id: {existing_scan.task_id}")
                return {"task_id": existing_scan.task_id, "status": "Scan déjà en cours", "resume": True}

        if not os.path.exists(docker_directory):
            logger.error(f"Chemin non trouvé dans Docker: {docker_directory}")
            raise FileNotFoundError(f"Le répertoire {docker_directory} n'est pas accessible dans le conteneur")
        try:
            music_stat = os.stat(docker_directory)
            logger.info(f"Permissions {docker_directory} {oct(music_stat.st_mode)}")
            os.listdir(docker_directory)
        except PermissionError:
            logger.error(f"Permissions insuffisantes pour {docker_directory}")
            raise PermissionError(f"Le répertoire {docker_directory} n'est pas accessible")
        except Exception as e:
            logger.error(f"Erreur système lors de l'accès à {docker_directory}: {str(e)}")
            raise RuntimeError(f"Erreur système: {str(e)}")

        # Create scan session
        if db:
            scan_session = ScanSession(directory=docker_directory, status='running')
            db.add(scan_session)
            db.commit()
            db.refresh(scan_session)
            logger.info(f"Created scan session {scan_session.id} for {docker_directory}")

        result = celery.send_task("scan_music_task", args=[docker_directory, cleanup_deleted])
        if db and scan_session:
            scan_session.task_id = result.id
            db.commit()
        return {"task_id": result.id, "status": f"Scan lancé avec succès sur {docker_directory}"}

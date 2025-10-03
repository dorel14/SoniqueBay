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
    def validate_base_directory(directory: str) -> None:
        """
        Valide le répertoire de base pour le scan en interdisant les racines système
        et en limitant la profondeur du répertoire.

        Args:
            directory: Chemin du répertoire à valider

        Raises:
            ValueError: Si le répertoire n'est pas valide
        """
        from pathlib import Path

        path = Path(directory)

        # Interdire les racines système
        system_roots = [
            '/',  # Linux/Unix root
            '/etc', '/usr', '/var', '/bin', '/sbin',  # Linux system dirs
            '/System', '/Library', '/Applications',  # macOS system dirs
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',  # Windows system dirs
            'C:\\System32', 'C:\\SysWOW64',  # Windows system dirs
        ]

        resolved_path = path.resolve()
        resolved_str = str(resolved_path)

        for root in system_roots:
            if resolved_str.startswith(root) or resolved_str == root.rstrip('\\').rstrip('/'):
                logger.error(f"Répertoire système interdit détecté: {resolved_str}")
                raise ValueError(f"Le répertoire {resolved_str} est un répertoire système protégé et ne peut pas être scanné")

        # Limiter la profondeur du répertoire (maximum 10 niveaux)
        parts = resolved_path.parts
        depth = len(parts)
        max_depth = 10

        if depth > max_depth:
            logger.error(f"Profondeur de répertoire trop grande: {depth} niveaux (maximum autorisé: {max_depth})")
            raise ValueError(f"La profondeur du répertoire {resolved_str} ({depth} niveaux) dépasse la limite de sécurité ({max_depth} niveaux)")

        logger.info(f"Validation base_directory réussie: {resolved_str} (profondeur: {depth})")

    @staticmethod
    def launch_scan(directory: str = None, db: Session = None, cleanup_deleted: bool = False):
        if not directory:
            docker_directory = os.getenv('MUSIC_PATH', '/music')
        else:
            converted_directory = ScanService.convert_path_to_docker(directory)
            docker_directory = f'/music/{converted_directory.lstrip('/')}'
        logger.info(f"MUSIC_PATH: {os.getenv('MUSIC_PATH')}")
        logger.info(f"PLATFORM: {os.getenv('PLATFORM')}")
        logger.info(f"Répertoire à scanner avant résolution: {docker_directory}")
        # SECURITY: Résoudre le chemin pour nettoyer les ../ et éviter Path Traversal
        from pathlib import Path
        resolved_docker_directory = str(Path(docker_directory).resolve())
        logger.info(f"Répertoire à scanner après résolution: {resolved_docker_directory}")
        docker_directory = resolved_docker_directory

        # SECURITY: Validation renforcée pour base_directory
        ScanService.validate_base_directory(docker_directory)

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

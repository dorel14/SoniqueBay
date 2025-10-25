"""
Service métier pour le scan de la bibliothèque musicale.
Déplace toute la logique métier depuis scan_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.utils.celery_app, backend.utils.logging
"""
from backend.library_api.utils.celery_app import celery
from backend.library_api.utils.logging import logger
import os
from backend.library_api.api.models.scan_sessions_model import ScanSession
from sqlalchemy.orm import Session
from fastapi import HTTPException

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
        # DIAGNOSTIC: Vérifier toutes les variables d'environnement disponibles
        logger.info("=== DIAGNOSTIC VARIABLES D'ENVIRONNEMENT ===")
        for key in sorted(os.environ.keys()):
            if any(env_var in key for env_var in ['MUSIC', 'PLATFORM', 'CELERY', 'DOCKER']):
                logger.info(f"ENV: {key}={os.environ[key]}")

        if not directory:
            music_path_env = os.getenv('MUSIC_PATH')
            logger.info(f"MUSIC_PATH env var: '{music_path_env}' (type: {type(music_path_env)})")
            docker_directory = music_path_env if music_path_env else '/music'
            logger.info(f"Using default directory: '{docker_directory}'")
        else:
            converted_directory = ScanService.convert_path_to_docker(directory)
            # Si le répertoire converti commence déjà par /music, l'utiliser tel quel
            if converted_directory.startswith('/music'):
                docker_directory = converted_directory
            else:
                # Sinon, l'ajouter au préfixe /music
                docker_directory = f'/music/{converted_directory.lstrip("/")}'

        logger.info(f"MUSIC_PATH: {os.getenv('MUSIC_PATH')}")
        logger.info(f"PLATFORM: {os.getenv('PLATFORM')}")
        logger.info(f"Répertoire à scanner avant résolution: {docker_directory}")

        # DIAGNOSTIC: Vérifier si le répertoire existe et ses permissions
        logger.info(f"=== DIAGNOSTIC RÉPERTOIRE {docker_directory} ===")
        if os.path.exists(docker_directory):
            logger.info(f"✓ Répertoire existe: {docker_directory}")
            try:
                stat_info = os.stat(docker_directory)
                logger.info(f"✓ Stat réussi: mode={oct(stat_info.st_mode)}, uid={stat_info.st_uid}, gid={stat_info.st_gid}")
                try:
                    contents = os.listdir(docker_directory)
                    logger.info(f"✓ Liste contents réussi: {len(contents)} éléments")
                    logger.info(f"Premiers éléments: {contents[:5]}")
                except Exception as list_error:
                    logger.error(f"✗ Erreur listdir: {list_error}")
            except Exception as stat_error:
                logger.error(f"✗ Erreur stat: {stat_error}")
        else:
            logger.error(f"✗ Répertoire n'existe PAS: {docker_directory}")
            # Lister le répertoire parent pour diagnostic
            parent_dir = os.path.dirname(docker_directory)
            if os.path.exists(parent_dir):
                logger.info(f"Parent existe: {parent_dir}")
                try:
                    parent_contents = os.listdir(parent_dir)
                    logger.info(f"Contents parent: {parent_contents}")
                except Exception as parent_error:
                    logger.error(f"Erreur listdir parent: {parent_error}")
            else:
                logger.error(f"✗ Parent n'existe pas non plus: {parent_dir}")
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

        logger.info(f"Configuration Celery - Broker: {celery.conf.broker_url}")
        logger.info(f"Configuration Celery - Include: {celery.conf.include}")

        # Utiliser directement les variables d'environnement pour éviter les problèmes de configuration Celery
        backend_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
        logger.info(f"Configuration Celery - Backend (env): {backend_url}")
        logger.info(f"Envoi de la tâche scan_music_task vers Celery avec args: {docker_directory}, {cleanup_deleted}")

        # Test de connectivité Redis avant envoi
        try:
            from backend.library_api.utils.celery_app import celery as celery_app
            logger.info(f"Test de connectivité Redis...")
            # Ping simple pour vérifier la connexion
            ping_result = celery_app.broker_connection().ensure_connection(max_retries=1)
            logger.info(f"Connexion Redis OK: {ping_result}")

            # Debug: Vérifier les workers actifs
            inspect = celery_app.control.inspect()
            active_workers = inspect.ping()
            logger.info(f"DEBUG: Workers actifs détectés: {active_workers}")

            # Debug: Vérifier les tâches en attente
            reserved_tasks = inspect.reserved()
            active_tasks = inspect.active()
            logger.info(f"DEBUG: Tâches réservées: {reserved_tasks}")
            logger.info(f"DEBUG: Tâches actives: {active_tasks}")

        except Exception as redis_error:
            logger.error(f"Erreur de connectivité Redis: {str(redis_error)}")
            logger.error(f"Exception Redis type: {type(redis_error)}")
            raise HTTPException(status_code=500, detail=f"Erreur de connectivité Redis: {str(redis_error)}")

        # Créer la session de scan seulement APRÈS le succès de l'envoi de la tâche
        scan_session = None
        try:
            logger.info(f"Appel de celery.send_task...")
            # IMPORTANT: Spécifier explicitement la queue scan (celle écoutée par les workers)
            result = celery.send_task(
                "scan_music_task",
                args=[docker_directory, cleanup_deleted],
                queue="scan"  # Queue écoutée par les scan-workers
            )
            logger.info(f"Tâche envoyée avec succès - Task ID: {result.id}")
            logger.info(f"Tâche envoyée avec succès - Status: {result.status}")
            logger.info(f"Tâche envoyée avec succès - Backend: {result.backend}")
            logger.info(f"Tâche envoyée vers la queue: scan")

            # Créer la session de scan seulement si la tâche a été envoyée avec succès
            if db:
                scan_session = ScanSession(directory=docker_directory, status='running')
                db.add(scan_session)
                db.commit()
                db.refresh(scan_session)
                logger.info(f"Created scan session {scan_session.id} for {docker_directory}")

                # Mettre à jour avec le task_id
                scan_session.task_id = result.id
                db.commit()
                logger.info(f"Session de scan mise à jour avec succès - task_id: {result.id}")

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la tâche Celery: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        logger.info(f"Retour du résultat: task_id={result.id}, status=Scan lancé avec succès sur {docker_directory}")
        return {"task_id": result.id, "status": f"Scan lancé avec succès sur {docker_directory}"}

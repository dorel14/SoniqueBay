"""Service métier pour le scan de la bibliothèque musicale.

Refactorisé pour utiliser la nouvelle architecture de tâches Celery :
- scan.discovery (au lieu de l'ancienne scan_music_task)
- Pipeline optimisé pour Raspberry Pi
- Messages structurés et logging amélioré
"""

import os
import time
from pathlib import Path

from backend.api.utils.celery_app import celery
from backend.api.utils.logging import logger
from backend.api.models.scan_sessions_model import ScanSession
from sqlalchemy.orm import Session
from fastapi import HTTPException


class ScanService:
    """Service métier pour la gestion des scans de bibliothèque musicale."""
    
    @staticmethod
    def convert_path_to_docker(input_path: str) -> str:
        """Convertit un chemin utilisateur en chemin Docker.
        
        Args:
            input_path: Chemin fourni par l'utilisateur
            
        Returns:
            Chemin converti pour l'environnement Docker
        """
        try:
            if ':' in input_path:
                path = input_path.split(':', 1)[1]
                clean_path = path.replace('\\', '/')
                logger.info(f"[SCAN] Conversion chemin: {input_path} -> {clean_path}")
                return clean_path
            return input_path
        except Exception as e:
            logger.error(f"[SCAN] Erreur conversion chemin: {str(e)}")
            return input_path

    @staticmethod
    def validate_base_directory(directory: str) -> None:
        """Valide le répertoire de base pour le scan.
        
        Interdit les racines système et limite la profondeur du répertoire.
        
        Args:
            directory: Chemin du répertoire à valider
            
        Raises:
            ValueError: Si le répertoire n'est pas valide
        """
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
                logger.error(f"[SCAN] Répertoire système interdit détecté: {resolved_str}")
                raise ValueError(f"Le répertoire {resolved_str} est un répertoire système protégé et ne peut pas être scanné")

        # Limiter la profondeur du répertoire (maximum 10 niveaux)
        parts = resolved_path.parts
        depth = len(parts)
        max_depth = 10

        if depth > max_depth:
            logger.error(f"[SCAN] Profondeur de répertoire trop grande: {depth} niveaux (maximum autorisé: {max_depth})")
            raise ValueError(f"La profondeur du répertoire {resolved_str} ({depth} niveaux) dépasse la limite de sécurité ({max_depth} niveaux)")

        logger.info(f"[SCAN] Validation base_directory réussie: {resolved_str} (profondeur: {depth})")

    @staticmethod
    def launch_scan(directory: str = None, db: Session = None, cleanup_deleted: bool = False):
        """Lance un scan de la bibliothèque musicale.
        
        Utilise la nouvelle architecture de tâches Celery avec scan.discovery.
        Le paramètre cleanup_deleted est ignoré pour compatibilité (déprécié).
        
        Args:
            directory: Répertoire à scanner (optionnel, utilise MUSIC_PATH si None)
            db: Session de base de données (optionnel)
            cleanup_deleted: Paramètre déprécié, ignoré pour compatibilité
            
        Returns:
            Dict avec task_id et status du scan
        """
        start_time = time.time()
        logger.info(f"[SCAN] Démarrage du scan - répertoire: {directory or 'par défaut'}")
        
        # DIAGNOSTIC: Variables d'environnement
        logger.info("[SCAN] === DIAGNOSTIC VARIABLES D'ENVIRONNEMENT ===")
        for key in sorted(os.environ.keys()):
            if any(env_var in key for env_var in ['MUSIC', 'PLATFORM', 'CELERY', 'DOCKER']):
                logger.info(f"[SCAN] ENV: {key}={os.environ[key]}")

        # Déterminer le répertoire à scanner
        if not directory:
            music_path_env = os.getenv('MUSIC_PATH')
            logger.info(f"[SCAN] MUSIC_PATH env: '{music_path_env}'")
            docker_directory = music_path_env if music_path_env else '/music'
            logger.info(f"[SCAN] Répertoire par défaut: '{docker_directory}'")
        else:
            converted_directory = ScanService.convert_path_to_docker(directory)
            if converted_directory.startswith('/music'):
                docker_directory = converted_directory
            else:
                docker_directory = f'/music/{converted_directory.lstrip("/")}'

        # Résolution et validation du chemin
        resolved_docker_directory = str(Path(docker_directory).resolve())
        logger.info(f"[SCAN] Répertoire résolu: {resolved_docker_directory}")
        ScanService.validate_base_directory(resolved_docker_directory)

        # Vérification existence et permissions
        if not os.path.exists(resolved_docker_directory):
            logger.error(f"[SCAN] Répertoire non trouvé: {resolved_docker_directory}")
            raise FileNotFoundError(f"Le répertoire {resolved_docker_directory} n'est pas accessible")
        
        try:
            os.listdir(resolved_docker_directory)
        except PermissionError:
            logger.error(f"[SCAN] Permissions insuffisantes: {resolved_docker_directory}")
            raise PermissionError(f"Accès refusé au répertoire {resolved_docker_directory}")
        except Exception as e:
            logger.error(f"[SCAN] Erreur accès répertoire: {str(e)}")
            raise RuntimeError(f"Erreur système: {str(e)}")

        # Vérifier scan existant
        if db:
            existing_scan = db.query(ScanSession).filter(
                ScanSession.directory == resolved_docker_directory,
                ScanSession.status.in_(['running', 'paused'])
            ).first()
            if existing_scan:
                logger.warning(f"[SCAN] Scan déjà actif pour {resolved_docker_directory}")
                return {"task_id": existing_scan.task_id, "status": "Scan déjà en cours", "resume": True}

        # Configuration Celery
        logger.info(f"[SCAN] Configuration Celery - Broker: {celery.conf.broker_url}")
        backend_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
        logger.info(f"[SCAN] Backend: {backend_url}")

        # Test connectivité Redis
        try:
            from backend.api.utils.celery_app import celery as celery_app
            celery_app.broker_connection().ensure_connection(max_retries=1)
            inspect = celery_app.control.inspect()
            active_workers = inspect.ping()
            logger.info(f"[SCAN] Workers actifs: {active_workers}")
        except Exception as redis_error:
            logger.error(f"[SCAN] Erreur Redis: {redis_error}")
            raise HTTPException(status_code=500, detail=f"Erreur de connectivité Redis: {str(redis_error)}")

        # Envoyer la nouvelle tâche scan.discovery
        try:
            logger.info("[SCAN] Envoi de la tâche scan.discovery vers Celery")
            logger.info("[SCAN] Queue cible: scan")
            logger.info(f"[SCAN] Répertoire: {resolved_docker_directory}")

            result = celery.send_task(
                "scan.discovery",  # Utilise la nouvelle tâche
                args=[resolved_docker_directory],  # Plus de cleanup_deleted
                queue="scan"
            )

            logger.info(f"[SCAN] Tâche envoyée - ID: {result.id}")
            logger.info(f"[SCAN] Tâche envoyée - Status: {result.status}")
            logger.info("[SCAN] Tâche envoyée vers queue: scan")

            # Vérification supplémentaire: inspecter les workers actifs
            try:
                inspect = celery.control.inspect()
                active_queues = inspect.active_queues()
                logger.info(f"[SCAN] Queues actives sur les workers: {active_queues}")

                if active_queues:
                    has_scan_queue = any('scan' in str(queues) for queues in active_queues.values())
                    logger.info(f"[SCAN] Queue 'scan' disponible: {has_scan_queue}")
                    if not has_scan_queue:
                        logger.warning("[SCAN] ATTENTION: Aucun worker n'écoute la queue 'scan'!")
            except Exception as inspect_error:
                logger.warning(f"[SCAN] Impossible d'inspecter les queues: {inspect_error}")

            # Créer session de scan
            if db:
                scan_session = ScanSession(directory=resolved_docker_directory, status='running')
                db.add(scan_session)
                db.commit()
                db.refresh(scan_session)
                logger.info(f"[SCAN] Session créée: {scan_session.id}")

                # Mettre à jour avec task_id
                scan_session.task_id = result.id
                db.commit()
                logger.info(f"[SCAN] Session mise à jour - task_id: {result.id}")

            duration = time.time() - start_time
            logger.info(f"[SCAN] Scan lancé avec succès en {duration:.2f}s")
            
            return {
                "task_id": result.id, 
                "status": f"Scan lancé avec succès sur {resolved_docker_directory}",
                "duration": duration,
                "architecture": "nouvelle"
            }

        except Exception as e:
            logger.error(f"[SCAN] Erreur envoi tâche: {str(e)}")
            import traceback
            logger.error(f"[SCAN] Traceback: {traceback.format_exc()}")
            raise

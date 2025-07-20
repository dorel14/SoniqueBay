import os
from fastapi import HTTPException
from typing import Optional
from utils.celery_app import celery
from utils.logging import logger

class ScanService:
    def convert_path_to_docker(self, input_path: str) -> str:
        """Convertit un chemin Windows en chemin Docker."""
        try:
            if ':' in input_path:
                path = input_path.split(':', 1)[1]
                clean_path = path.replace('\\', '/').lstrip('/')
                docker_path = f"/music/{clean_path}"
                logger.info(f"Conversion chemin: {input_path} -> {docker_path}")
                return docker_path
            return input_path
        except Exception as e:
            logger.error(f"Erreur conversion chemin: {str(e)}")
            return input_path

    async def launch_scan(self, directory: Optional[str] = None):
        """Lance un scan de la bibliothèque musicale."""
        try:
            if not directory:
                path_to_scan = os.getenv('MUSIC_PATH', '/music')
            else:
                path_to_scan=f'/music/{directory}'

            docker_directory = self.convert_path_to_docker(path_to_scan)
            logger.info(f"Tentative d'accès au chemin Docker: {docker_directory}")
            
            # Vérifier que le chemin existe (cette partie est pour le débogage et peut être simplifiée)
            # Dans un environnement Docker, os.path.exists() doit être exécuté dans le conteneur
            # où le chemin est monté. Ici, nous nous fions à la tâche Celery pour la validation finale.
            # Cependant, pour un feedback immédiat, on peut laisser une vérification simple.
            if not os.path.exists(docker_directory):
                logger.error(f"Chemin non trouvé dans Docker: {docker_directory}")
                # Cette HTTPException sera levée si le chemin n'existe pas sur le système de fichiers
                # où le backend FastAPI est exécuté, pas nécessairement dans le conteneur Celery.
                # Pour une validation plus robuste, la tâche Celery devrait gérer cela.
                # Pour l'instant, nous laissons cette vérification pour un feedback rapide.
                raise HTTPException(
                    status_code=400,
                    detail=f"Le répertoire {path_to_scan} n'est pas accessible dans le conteneur"
                )

            result = celery.send_task("scan_music_task", args=[docker_directory])
            return {"task_id": result.id, "status": f"Scan lancé avec succès sur {docker_directory}"}

        except Exception as e:
            logger.error(f"Erreur lancement scan: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
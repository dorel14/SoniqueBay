# -*- coding: utf-8 -*-

import subprocess
import time
import os
from helpers.logging import logger



def launch_api():
        return subprocess.Popen(["python", "./backend/start_api.py"])



def launch_celery():
    logger.info("Démarrage du Worker Celery...")
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.abspath('.')  # Assure que le chemin Python est correct
        return subprocess.Popen(
            ["celery", "-A", "backend.celery_app", "worker",
            "--loglevel=info",
            "--pool=solo",  # Forcer le pool solo sur Windows
            "--concurrency=1",
            "--include=backend.celery_tasks"],  # Explicitement inclure les tâches
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
    except Exception as e:
        logger.error(f"Erreur au démarrage de Celery: {e}")
        return None

def launch_ui():
        logger.info("Démarrage du Frontend NiceGUI...")
        return subprocess.Popen(["python", "./frontend/start_ui.py"])



if __name__ == "__main__":
        logger.info("Démarrage de l'API FastAPI...")
        api_process = launch_api()
        # Attendre que l'API soit complètement démarrée
        time.sleep(3)  # Augmentation du délai à 3 secondes

        logger.info("Démarrage du Frontend NiceGUI...")
        ui_process = launch_ui()

        logger.info("Démarrage du Worker Celery...")
        celery_process = launch_celery()

        try:
                ui_process.wait()
                api_process.wait()
                if celery_process:
                    celery_process.wait()
        except KeyboardInterrupt:
                logger.info("Arrêt de SoniqueBay...")
                ui_process.terminate()
                api_process.terminate()
                if celery_process:
                    celery_process.terminate()


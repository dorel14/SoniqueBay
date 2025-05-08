# -*- coding: utf-8 -*-

import subprocess
import time
from helpers.logging import logger

def launch_api():
        return subprocess.Popen(["python", "./backend/start_api.py"])

def launch_ui():
        logger.info("Démarrage du Frontend NiceGUI...")
        return subprocess.Popen(["python", "./frontend/start_ui.py"])

def launch_celery():
    return subprocess.Popen(["celery", "-A", "backend.celery_app.celery", "worker", "--loglevel=info"])

if __name__ == "__main__":
        logger.info("Démarrage de l'API FastAPI...")
        api_process = launch_api()
        # Attendre que l'API soit complètement démarrée
        time.sleep(3)  # Augmentation du délai à 3 secondes

        logger.info("Démarrage du Frontend NiceGUI...")
        ui_process = launch_ui()

        try:
                ui_process.wait()
                api_process.wait()
        except KeyboardInterrupt:
                logger.info("Arrêt de SoniqueBay...")
                ui_process.terminate()
                api_process.terminate()


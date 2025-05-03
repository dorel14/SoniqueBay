# -*- coding: utf-8 -*-

import subprocess
import time
from helpers.logging import logger
def launch_ui():
        logger.info("Démarrage du Frontend NiceGUI...")
        return subprocess.Popen(["python", "./frontend/start_ui.py"])

def launch_api():
        return subprocess.Popen(["python", "./backend/start_api.py"])

def launch_celery():
    return subprocess.Popen(["celery", "-A", "backend.celery_app.celery", "worker", "--loglevel=info"])

if __name__ == "__main__":
        logger.info("Démarrage du Frontend NiceGUI...")
        ui_process = launch_ui()
        time.sleep(1)

        logger.info("Démarrage de l'API FastAPI...")
        api_process = launch_api()
        time.sleep(1)

        #logger.info("Démarrage du Worker Celery...")
        #celery_process = launch_celery()

        try:
                ui_process.wait()
                api_process.wait()
                #celery_process.wait()
        except KeyboardInterrupt:
                logger.info("Arrêt de SoniqueBay...")
                ui_process.terminate()
                api_process.terminate()
                #celery_process.terminate()


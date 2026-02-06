"""Test de communication API → Worker Celery.

Ce script valide que la configuration Celery de l'API peut envoyer
des tâches vers le worker sans erreur Kombu.
"""

import os
import sys
import time
from pathlib import Path
from backend.api.utils.celery_app import celery_app
from backend.api.utils.logging import logger
# Ajouter le répertoire racine au path Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))




def test_celery_connection():
    """Teste la connexion Celery et l'envoi de tâches."""
    logger.info("=" * 60)
    logger.info("TEST DE COMMUNICATION CELERY API → WORKER")
    logger.info("=" * 60)
    
    # 1. Vérifier la configuration Celery
    logger.info("\n[1] Configuration Celery de l'API:")
    logger.info(f"    App name: {celery_app.main}")
    logger.info(f"    Broker URL: {celery_app.conf.broker_url}")
    logger.info(f"    Backend URL: {celery_app.conf.result_backend}")
    logger.info(f"    Task routes: {list(celery_app.conf.task_routes.keys())}")
    logger.info(f"    Task queues: {[q.name for q in celery_app.conf.task_queues]}")
    
    # 2. Tester la connexion au broker
    logger.info("\n[2] Test de connexion au broker Redis...")
    try:
        connection = celery_app.broker_connection()
        connection.ensure_connection(max_retries=3)
        logger.info("    ✓ Connexion au broker réussie")
    except Exception as e:
        logger.error(f"    ✗ Erreur de connexion au broker: {e}")
        return False
    
    # 3. Tester l'inspection des workers
    logger.info("\n[3] Test d'inspection des workers...")
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        
        if active_workers:
            logger.info(f"    ✓ Workers actifs détectés: {list(active_workers.keys())}")
            
            # Vérifier les queues actives
            active_queues = inspect.active_queues()
            if active_queues:
                logger.info(f"    ✓ Queues actives: {active_queues}")
            else:
                logger.warning("    ⚠ Aucune queue active détectée")
        else:
            logger.warning("    ⚠ Aucun worker actif détecté")
            logger.warning("    Vérifiez que le worker Celery est démarré")
    except Exception as e:
        logger.error(f"    ✗ Erreur d'inspection: {e}")
        return False
    
    # 4. Tester l'envoi d'une tâche simple
    logger.info("\n[4] Test d'envoi d'une tâche simple...")
    try:
        # Envoyer une tâche de test (scan.discovery avec un répertoire vide)
        test_directory = "/tmp/test_scan"
        result = celery_app.send_task(
            'scan.discovery',
            args=[test_directory],
            queue='scan',
            priority=9
        )
        
        logger.info(f"    ✓ Tâche envoyée avec succès")
        logger.info(f"    Task ID: {result.id}")
        logger.info(f"    Task status: {result.status}")
        
        # Attendre un peu pour voir si la tâche est acceptée
        time.sleep(2)
        
        # Vérifier le statut de la tâche
        updated_status = result.status
        logger.info(f"    Task status après 2s: {updated_status}")
        
        if updated_status in ['PENDING', 'STARTED', 'SUCCESS']:
            logger.info("    ✓ Tâche acceptée par le worker")
            return True
        else:
            logger.warning(f"    ⚠ Statut inattendu: {updated_status}")
            return False
            
    except Exception as e:
        logger.error(f"    ✗ Erreur lors de l'envoi de la tâche: {e}")
        import traceback
        logger.error(f"    Traceback: {traceback.format_exc()}")
        return False


def main():
    """Fonction principale."""
    try:
        success = test_celery_connection()
        
        logger.info("\n" + "=" * 60)
        if success:
            logger.info("RÉSULTAT: ✓ TEST RÉUSSI")
            logger.info("La communication API → Worker fonctionne correctement")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("RÉSULTAT: ✗ TEST ÉCHOUÉ")
            logger.error("Vérifiez les logs et la configuration Celery")
            logger.error("=" * 60)
            return 1
            
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

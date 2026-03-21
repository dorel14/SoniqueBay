"""Tâches TaskIQ de maintenance.

Migration de celery_tasks.py et maintenance_tasks.py vers TaskIQ.
"""
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger
import os
import asyncio
from backend_worker.services.deferred_queue_service import deferred_queue_service


@broker.task
async def cleanup_expired_tasks_task(max_age_seconds: int = 86400) -> dict:
    """Nettoie les tâches expirées dans toutes les queues différées.
    
    Args:
        max_age_seconds: Âge maximum des tâches à conserver
        
    Returns:
        Statistiques du nettoyage
    """
    logger.info(f"[TASKIQ|MAINTENANCE] Démarrage nettoyage tâches expirées (> {max_age_seconds}s)")
    
    try:
        result = deferred_queue_service.cleanup_expired_tasks(max_age_seconds)
        
        if isinstance(result, dict) and "error" not in result:
            total_cleaned = sum(result.values())
            logger.info(f"[TASKIQ|MAINTENANCE] Nettoyage terminé: {total_cleaned} tâches supprimées")
        else:
            logger.warning(f"[TASKIQ|MAINTENANCE] Erreur nettoyage: {result}")
            
        logger.info(f"[TASKIQ|MAINTENANCE] Fin cleanup_expired_tasks_task (success=True)")
        return result
        
    except Exception as e:
        logger.error(f"[TASKIQ|MAINTENANCE] Exception nettoyage: {str(e)}")
        logger.info(f"[TASKIQ|MAINTENANCE] Fin cleanup_expired_tasks_task (success=False)")
        return {"error": str(e)}


@broker.task
async def archive_old_logs_task(days_to_keep: int = 30) -> dict:
    """Archive les anciens logs des workers.
    
    Args:
        days_to_keep: Nombre de jours de logs à conserver
        
    Returns:
        Résultats de l'archivage
    """
    logger.info(f"[TASKIQ|MAINTENANCE] Démarrage archivage logs (> {days_to_keep} jours)")
    
    try:
        # En production, implémenter la logique d'archivage des logs
        # Pour l'instant, juste un placeholder
        result = {
            "message": f"Archivage simulé pour {days_to_keep} jours",
            "logs_archived": 0,
            "space_saved": "0 MB"
        }
        
        logger.info(f"[TASKIQ|MAINTENANCE] Archivage logs terminé: {result}")
        logger.info(f"[TASKIQ|MAINTENANCE] Fin archive_old_logs_task (success=True)")
        return result
        
    except Exception as e:
        logger.error(f"[TASKIQ|MAINTENANCE] Erreur archivage logs: {str(e)}")
        logger.info(f"[TASKIQ|MAINTENANCE] Fin archive_old_logs_task (success=False)")
        return {"error": str(e)}
"""Utilitaires pour TaskIQ.

Fournit des wrappers pour exécuter des tâches TaskIQ de manière synchrone ou asynchrone.
"""
import asyncio
from typing import Any, Callable
from backend.workers.utils.logging import logger


def run_taskiq_sync(task_func: Callable, *args, **kwargs) -> Any:
    """Exécute une tâche TaskIQ de manière synchrone.
    
    Args:
        task_func: Fonction de tâche TaskIQ
        *args: Arguments positionnels
        **kwargs: Arguments nommés
        
    Returns:
        Résultat de la tâche
    """
    try:
        # Obtenir ou créer une boucle d'événements
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Exécuter la tâche de manière synchrone
        result = loop.run_until_complete(task_func(*args, **kwargs))
        
        return result
        
    except Exception as e:
        logger.error(f"[TASKIQ] Erreur exécution synchrone: {e}")
        raise


async def run_taskiq_async(task_func: Callable, *args, **kwargs) -> Any:
    """Exécute une tâche TaskIQ de manière asynchrone.
    
    Args:
        task_func: Fonction de tâche TaskIQ
        *args: Arguments positionnels
        **kwargs: Arguments nommés
        
    Returns:
        Résultat de la tâche
    """
    try:
        result = await task_func(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"[TASKIQ] Erreur exécution asynchrone: {e}")
        raise

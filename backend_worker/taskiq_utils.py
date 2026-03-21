"""Utilitaires pour TaskIQ.

Ce module fournit des fonctionnalités utilitaires pour faciliter
l'utilisation de TaskIQ dans un environnement synchrone.
"""
import asyncio
from typing import Any, Callable


def run_taskiq_sync(task_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Exécute une tâche TaskIQ asynchrone depuis du code synchrone.

    Args:
        task_func: Tâche TaskIQ asynchrone à exécuter
        *args: Arguments positionnels pour la tâche
        **kwargs: Arguments nommés pour la tâche

    Returns:
        Résultat de l'exécution de la tâche

    Raises:
        Exception: Toute exception levée par la tâche
    """
    try:
        # Tentative d'obtenir la boucle d'événements existante
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Si aucune boucle n'existe, en créer une nouvelle
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(task_func.kiq(*args, **kwargs))
    finally:
        # Si nous avons créé une boucle, nous devons la fermer
        if "loop" in locals() and loop.is_closed() is False:
            loop.close()

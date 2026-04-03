"""Gestion des feature flags pour la migration Celery → TaskIQ.

Ce module centralise la lecture des variables d'environnement
pour contrôler le comportement de migration.
"""
import os


def get_flag(flag_name: str, default: bool = False) -> bool:
    """
    Lit une variable d'environnement et la convertit en booléen.

    Args:
        flag_name: Nom de la variable d'environnement
        default: Valeur par défaut si la variable n'existe pas

    Returns:
        Valeur booléenne de la variable
    """
    value = os.getenv(flag_name, str(default)).lower().strip()
    return value in ("true", "1", "yes", "on")


# Flags par tâche
USE_TASKIQ_FOR_MAINTENANCE = get_flag("USE_TASKIQ_FOR_MAINTENANCE", False)
USE_TASKIQ_FOR_COVERS = get_flag("USE_TASKIQ_FOR_COVERS", False)
USE_TASKIQ_FOR_INSERT = get_flag("USE_TASKIQ_FOR_INSERT", False)
USE_TASKIQ_FOR_VECTORIZATION = get_flag("USE_TASKIQ_FOR_VECTORIZATION", False)
USE_TASKIQ_FOR_METADATA = get_flag("USE_TASKIQ_FOR_METADATA", False)
USE_TASKIQ_FOR_BATCH = get_flag("USE_TASKIQ_FOR_BATCH", False)
USE_TASKIQ_FOR_SCAN = get_flag("USE_TASKIQ_FOR_SCAN", False)

# Flags globaux
ENABLE_CELERY_FALLBACK = get_flag("ENABLE_CELERY_FALLBACK", True)
WORKER_DIRECT_DB_ENABLED = get_flag("WORKER_DIRECT_DB_ENABLED", False)

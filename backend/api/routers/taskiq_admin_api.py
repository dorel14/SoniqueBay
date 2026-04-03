"""
API endpoints pour l'administration des tâches TaskIQ.
Permet de visualiser les tâches en échec et de les relancer.

⚠️ SECURITE: Ces endpoints sont protégés par une clé API admin.
La clé doit être définie dans la variable d'environnement TASKIQ_ADMIN_API_KEY.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import redis
import os

from backend.api.utils.logging import logger

router = APIRouter(prefix="/api/admin/taskiq", tags=["taskiq-admin"])


# ============================================================================
# SECURITE: Authentification par clé API admin
# ============================================================================


def verify_admin_key(
    x_admin_key: str = Header(..., description="Clé API admin pour l'accès TaskIQ")
):
    """
    Vérifie la clé API admin pour l'accès aux endpoints d'administration TaskIQ.

    La clé doit être définie dans la variable d'environnement TASKIQ_ADMIN_API_KEY.
    En l'absence de clé configurée, l'accès est refusé par défaut (fail-secure).
    """
    expected_key = os.getenv("TASKIQ_ADMIN_API_KEY")

    # Fail-secure: si aucune clé n'est configurée, l'accès est refusé
    if not expected_key:
        logger.error(
            f"[TASKIQ ADMIN] Tentative d'accès sans TASKIQ_ADMIN_API_KEY configurée"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service non configuré: TASKIQ_ADMIN_API_KEY manquante",
        )

    # Constant-time comparison pour éviter les attaques timing
    if not _secure_compare(x_admin_key, expected_key):
        logger.warning("[CELERY ADMIN] Tentative d'accès avec clé invalide")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API admin invalide",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


def _secure_compare(a: str, b: str) -> bool:
    """
    Comparaison en temps constant pour éviter les attaques par timing.
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0


class FailedTask(BaseModel):
    """Modèle pour une tâche en échec."""

    task_id: str
    task_name: str
    exception: str
    exception_type: str
    args: str
    kwargs: str
    timestamp: str
    retry_count: int


class FailedTasksResponse(BaseModel):
    """Réponse pour la liste des tâches en échec."""

    tasks: List[FailedTask]
    count: int


# Whitelist des tâches TaskIQ autorisées à être relancées via l'API admin
# TODO: Ajuster selon les besoins de production
ALLOWED_RETRY_TASKS = {
    "backend_worker.taskiq_tasks.process_audio_file",
    "backend_worker.taskiq_tasks.extract_metadata",
    "backend_worker.taskiq_tasks.vectorize_track",
    "backend_worker.taskiq_tasks.enrich_track_metadata",
    "backend_worker.taskiq_tasks.deferred_enrichment",
    "backend_worker.taskiq_tasks.insert_batch",
}


class RetryTaskRequest(BaseModel):
    """Requête pour relancer une tâche."""

    task_id: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"task_id": "abc123-def456-ghi789"}}
    )


class RetryTaskResponse(BaseModel):
    """Réponse pour le retry d'une tâche."""

    success: bool
    message: str
    task_id: Optional[str] = None


def get_redis_client():
    """Obtient un client Redis."""
    redis_url = os.getenv("TASKIQ_BROKER_URL", "redis://redis:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


@router.get(
    "/failed-tasks",
    response_model=FailedTasksResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def get_failed_tasks(limit: int = 100):
    """
    Récupère la liste des tâches TaskIQ en échec stockées dans Redis.

    Les tâches sont stockées après épuisement des retries (max 5 tentatives).
    """
    try:
        client = get_redis_client()

        # Récupérer toutes les clés correspondant aux tâches échouées
        keys = client.keys("taskiq:failed:*")
        failed_tasks = []

        for key in keys[:limit]:
            task_info = client.hgetall(key)
            if task_info:
                failed_tasks.append(
                    FailedTask(
                        task_id=task_info.get("task_id", ""),
                        task_name=task_info.get("task_name", ""),
                        exception=task_info.get("exception", ""),
                        exception_type=task_info.get("exception_type", ""),
                        args=task_info.get("args", ""),
                        kwargs=task_info.get("kwargs", ""),
                        timestamp=task_info.get("timestamp", ""),
                        retry_count=int(task_info.get("retry_count", 0)),
                    )
                )

        # Trier par timestamp décroissant
        failed_tasks.sort(key=lambda x: x.timestamp, reverse=True)

        logger.info(f"[TASKIQ ADMIN] {len(failed_tasks)} tâches en échec récupérées")

        return FailedTasksResponse(tasks=failed_tasks, count=len(failed_tasks))

    except Exception as e:
        logger.error(
            f"[CELERY ADMIN] Erreur lors de la récupération des tâches en échec: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Erreur Redis: {str(e)}")


@router.post(
    "/retry-task",
    response_model=RetryTaskResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def retry_failed_task(request: RetryTaskRequest):
    """
    Relance une tâche précédemment en échec.

    La tâche est supprimée de la DLQ et renvoyée dans sa queue d'origine.
    """
    try:
        client = get_redis_client()
        key = f"taskiq:failed:{request.task_id}"

        # Vérifier si la tâche existe
        task_info = client.hgetall(key)
        if not task_info:
            return RetryTaskResponse(
                success=False,
                message=f"Tâche {request.task_id} non trouvée dans la DLQ",
                task_id=request.task_id,
            )

        # Vérifier que la tâche est dans la whitelist (sécurité)
        task_name = task_info.get("task_name")
        if task_name not in ALLOWED_RETRY_TASKS:
            logger.warning(
                f"[CELERY ADMIN] Tentative de retry d'une tâche non autorisée: {task_name}"
            )
            return RetryTaskResponse(
                success=False,
                message=f"Tâche '{task_name}' non autorisée pour retry via API. Contactez l'administrateur.",
                task_id=request.task_id,
            )

        # Importer TaskIQ pour relancer la tâche
        from backend.api.utils.taskiq_broker import taskiq_broker

        args_str = task_info.get("args", "()")
        kwargs_str = task_info.get("kwargs", "{}")

        # Évaluer les arguments (sécurisé car on contrôle le format)
        import ast

        try:
            args = ast.literal_eval(args_str) if args_str else ()
            kwargs = ast.literal_eval(kwargs_str) if kwargs_str else {}
        except (ValueError, SyntaxError) as e:
            logger.error(
                f"[TASKIQ ADMIN] Erreur parsing args pour tâche {request.task_id}: {e}"
            )
            return RetryTaskResponse(
                success=False,
                message=f"Erreur parsing arguments: {str(e)}",
                task_id=request.task_id,
            )

        # Relancer la tâche via TaskIQ
        result = await taskiq_broker.send_task(task_name, args=args, kwargs=kwargs)

        # Supprimer de la DLQ
        client.delete(key)

        logger.info(
            f"[TASKIQ ADMIN] Tâche {request.task_id} ({task_name}) relancée avec succès"
        )

        return RetryTaskResponse(
            success=True,
            message=f"Tâche relancée avec succès",
            task_id=request.task_id,
        )

    except Exception as e:
        logger.error(
            f"[CELERY ADMIN] Erreur lors du retry de la tâche {request.task_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Erreur lors du retry: {str(e)}")


@router.delete("/failed-tasks/{task_id}", dependencies=[Depends(verify_admin_key)])
async def delete_failed_task(task_id: str):
    """
    Supprime une tâche en échec de la DLQ sans la relancer.
    """
    try:
        client = get_redis_client()
        key = f"taskiq:failed:{task_id}"

        # Vérifier si la tâche existe
        if not client.exists(key):
            raise HTTPException(
                status_code=404, detail=f"Tâche {task_id} non trouvée dans la DLQ"
            )

        # Supprimer
        client.delete(key)

        logger.info(f"[TASKIQ ADMIN] Tâche {task_id} supprimée de la DLQ")

        return {"success": True, "message": f"Tâche {task_id} supprimée de la DLQ"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[CELERY ADMIN] Erreur lors de la suppression de la tâche {task_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/retry-stats", dependencies=[Depends(verify_admin_key)])
async def get_retry_stats():
    """
    Récupère les statistiques de retry pour les tâches TaskIQ.
    """
    try:
        client = get_redis_client()

        # Compter les tâches en échec
        failed_keys = client.keys("taskiq:failed:*")

        # Compter par type d'exception
        exception_counts = {}
        for key in failed_keys:
            task_info = client.hgetall(key)
            exc_type = task_info.get("exception_type", "Unknown")
            exception_counts[exc_type] = exception_counts.get(exc_type, 0) + 1

        return {
            "total_failed_tasks": len(failed_keys),
            "exception_breakdown": exception_counts,
            "max_retries_configured": 5,
            "backoff_strategy": "exponential with jitter",
            "retry_backoff_max": 3600,
            "retry_jitter": True,
            "default_retry_delay": 60,
            "dlq_retention_days": 7,
        }

    except Exception as e:
        logger.error(f"[TASKIQ ADMIN] Erreur lors de la récupération des stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

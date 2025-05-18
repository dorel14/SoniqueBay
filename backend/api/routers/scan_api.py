from fastapi import APIRouter, HTTPException, status, WebSocket
from backend.task_system import AsyncTask, register_ws
from backend.background_tasks.tasks import index_music_task  # Import explicite
from helpers.logging import logger

router = APIRouter(prefix="/api", tags=["scan"])

@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def launch_scan(directory: str):
    """Lance un scan sur le dossier spécifié avec monitoring."""
    try:
        if "index_music" not in AsyncTask.registry:
            logger.error("Tâche index_music non trouvée dans le registre")
            raise HTTPException(
                status_code=500,
                detail="Tâche d'indexation non disponible"
            )

        task = AsyncTask.registry["index_music"]
        logger.info(f"Lancement du scan sur: {directory}")
        await task.run(directory)
        return {
            "status": "success",
            "message": f"Scan lancé en arrière-plan pour: {directory}"
        }
    except KeyError as e:
        logger.error(f"Tâche non trouvée: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration de tâche invalide")
    except Exception as e:
        logger.error(f"Erreur lancement scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    """Point de terminaison WebSocket pour le monitoring des tâches."""
    await register_ws(websocket)


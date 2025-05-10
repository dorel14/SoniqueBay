from fastapi import APIRouter, HTTPException, status
from backend.indexing.music_scan import scan_music_files
from backend.celery_tasks.tasks import scan_and_index_music


router = APIRouter(prefix="/api", tags=["scan"])
@router.post("/scan", status_code=status.HTTP_201_CREATED,tags=["scan"])
async def launch_scan(directory: str):
    """Lance un scan sur le dossier spécifié."""

    try:
        scan_results = scan_music_files(directory)  # Appel de la fonction de scan
        # Lancer la tâche Celery en arrière-plan avec delay()
        scan_and_index_music.delay(directory)
        return {
            "status": "success",
            "message": "Scan lancé en arrière-plan",
            "files_found": scan_results
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


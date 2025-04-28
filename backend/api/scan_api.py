from fastapi import APIRouter, HTTPException, status

from backend.music_scan import scan_music_files

router = APIRouter(prefix="/api/v1")


@router.post("/scan", status_code=status.HTTP_201_CREATED,tags=["scan"])
async def launch_scan(directory: str):
    """Lance un scan sur le dossier spécifié."""

    try:
        scan_results = scan_music_files(directory)  # Appel de la fonction de scan
        return scan_results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


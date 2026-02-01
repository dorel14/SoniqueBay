 
from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import Optional
import os
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.utils.database import get_async_session

from backend.api.services.scan_service import ScanService
from backend.api.schemas.scan_schema import ScanRequest


router = APIRouter(prefix='', tags=["scan"])



@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def launch_scan(request: Optional[ScanRequest] = Body(None), db: AsyncSession = Depends(get_async_session)):
    """Lance un scan de la bibliothèque musicale."""
    from backend.api.utils.logging import logger
    logger.info("Endpoint /scan appelé avec request: %s", request)
    try:
        directory = request.directory if request and request.directory else None
        cleanup_deleted = request.cleanup_deleted if request else False
        try:
            result = await ScanService.launch_scan(directory, db, cleanup_deleted)
        except FileNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PermissionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def convert_path_to_docker(path: Optional[str]) -> Optional[str]:
    """Convertit un chemin Windows vers un chemin Docker."""
    if path is None:
        return None
    
    music_dir = os.getenv('MUSIC_DIR', '/music')
    
    # Si c'est un chemin Windows (avec drive letter)
    if os.path.isabs(path) and len(path) > 2 and path[1] == ':':
        # Extraire le chemin relatif après le drive
        drive, tail = os.path.splitdrive(path)
        relative_path = tail.lstrip(os.sep).lstrip('music').lstrip(os.sep)
        # Remplacer par le chemin Docker
        docker_path = music_dir + '/' + relative_path.replace(os.sep, '/')
        return docker_path
    
    # Si c'est déjà un chemin relatif ou Unix, le retourner tel quel
    return path

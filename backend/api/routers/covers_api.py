from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.api.utils.database import get_db
from backend.api.schemas.covers_schema import CoverCreate, Cover as CoverSchema
from backend.api.services.covers_service import CoverService
from backend.api.models.covers_model import EntityCoverType
from backend.api.utils.logging import logger
from backend.api.utils.celery_app import celery_app

router = APIRouter(prefix="/covers", tags=["covers"])

@router.post("/", response_model=CoverSchema)
async def create_cover(cover: CoverCreate, db: SQLAlchemySession = Depends(get_db)):
    """Crée une nouvelle cover."""
    try:
        service = CoverService(db)
        return service.create_or_update_cover(cover)
    except Exception as e:
        logger.error(f"Erreur création cover: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def get_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Récupère une cover par type et ID d'entité."""
    try:
        service = CoverService(db)
        cover = service.get_cover(entity_type, entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if cover is None:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    return cover

@router.get("/", response_model=List[CoverSchema])
async def get_covers(
    entity_type: Optional[EntityCoverType] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Liste les covers avec filtrage optionnel par type."""
    service = CoverService(db)
    return service.get_covers(entity_type)

@router.delete("/{entity_type}/{entity_id}")
async def delete_cover(
    entity_type: EntityCoverType,
    entity_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Supprime une cover."""
    service = CoverService(db)
    deleted = service.delete_cover(entity_type, entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    return {"status": "success"}

@router.put("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def update_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    cover: CoverCreate,
    db: SQLAlchemySession = Depends(get_db)
):
    """Met à jour une cover existante."""
    service = CoverService(db)
    db_cover = service.update_cover(entity_type, entity_id, cover)
    if db_cover is None:
        raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
    logger.info(f"Cover mise à jour pour {entity_type} {entity_id}")
    return db_cover

@router.post("/scan/artist/{artist_id}")
async def scan_artist_images(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Relance le scan des images d'un artiste spécifique."""
    try:
        logger.info(f"[COVER API] Début scan images pour artiste {artist_id}")
        
        # Appeler la tâche Celery pour traiter les images de l'artiste
        task_result = celery_app.send_task(
            "covers.process_artist_images",
            args=[[artist_id]],
            queue="deferred"
        )
        
        logger.info(f"[COVER API] Tâche process_artist_images déclenchée avec ID: {task_result.id}")
        
        return {
            "status": "success",
            "message": f"Scan des images de l'artiste {artist_id} déclenché",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"[COVER API] Erreur lors du scan des images de l'artiste {artist_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan/album/{album_id}")
async def scan_album_images(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Relance le scan des images d'un album spécifique."""
    try:
        logger.info(f"[COVER API] Début scan images pour album {album_id}")
        
        # Appeler la tâche Celery pour traiter les images de l'album
        task_result = celery_app.send_task(
            "covers.process_album_covers",
            args=[[album_id]],
            queue="deferred"
        )
        
        logger.info(f"[COVER API] Tâche process_album_covers déclenchée avec ID: {task_result.id}")
        
        return {
            "status": "success",
            "message": f"Scan des images de l'album {album_id} déclenché",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"[COVER API] Erreur lors du scan des images de l'album {album_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan/artists")
async def scan_all_artist_images(db: SQLAlchemySession = Depends(get_db)):
    """Relance le scan des images de tous les artistes."""
    try:
        logger.info("[COVER API] Début scan images pour tous les artistes")
        
        # Récupérer tous les IDs d'artistes depuis la DB
        from backend.api.models.artists_model import Artist
        artist_ids = [artist.id for artist in db.query(Artist.id).all()]
        
        logger.info(f"[COVER API] {len(artist_ids)} artistes à traiter")
        
        # Appeler la tâche Celery pour traiter les images des artistes
        task_result = celery_app.send_task(
            "covers.process_artist_images",
            args=[artist_ids],
            queue="deferred"
        )
        
        logger.info(f"[COVER API] Tâche process_artist_images déclenchée avec ID: {task_result.id}")
        
        return {
            "status": "success",
            "message": f"Scan des images de {len(artist_ids)} artistes déclenché",
            "task_id": task_result.id,
            "artists_count": len(artist_ids)
        }
        
    except Exception as e:
        logger.error(f"[COVER API] Erreur lors du scan des images des artistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan/albums")
async def scan_all_album_images(db: SQLAlchemySession = Depends(get_db)):
    """Relance le scan des images de tous les albums."""
    try:
        logger.info("[COVER API] Début scan images pour tous les albums")
        
        # Récupérer tous les IDs d'albums depuis la DB
        from backend.api.models.albums_model import Album
        album_ids = [album.id for album in db.query(Album.id).all()]
        
        logger.info(f"[COVER API] {len(album_ids)} albums à traiter")
        
        # Appeler la tâche Celery pour traiter les images des albums
        task_result = celery_app.send_task(
            "covers.process_album_covers",
            args=[album_ids],
            queue="deferred"
        )
        
        logger.info(f"[COVER API] Tâche process_album_covers déclenchée avec ID: {task_result.id}")
        
        return {
            "status": "success",
            "message": f"Scan des images de {len(album_ids)} albums déclenché",
            "task_id": task_result.id,
            "albums_count": len(album_ids)
        }
        
    except Exception as e:
        logger.error(f"[COVER API] Erreur lors du scan des images des albums: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan/embedded")
async def scan_embedded_covers(directory: Optional[str] = None, db: SQLAlchemySession = Depends(get_db)):
    """Relance le scan des covers intégrées dans les fichiers musicaux."""
    try:
        logger.info(f"[COVER API] Début scan des covers intégrées{' dans ' + directory if directory else ''}")
        
        # Si un répertoire est spécifié, scanner les fichiers dans ce répertoire
        if directory:
            from pathlib import Path
            music_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
            file_paths = []
            
            # Parcourir le répertoire pour trouver les fichiers musicaux
            for ext in music_extensions:
                for file in Path(directory).rglob(f"*{ext}"):
                    file_paths.append(str(file))
            
            logger.info(f"[COVER API] {len(file_paths)} fichiers musicaux trouvés")
        else:
            # Sinon, récupérer tous les chemins de fichiers musicaux depuis la DB
            from backend.api.models.tracks_model import Track
            file_paths = [track.path for track in db.query(Track.path).all()]
            
            logger.info(f"[COVER API] {len(file_paths)} fichiers musicaux à traiter")
        
        # Appeler la tâche Celery pour extraire les covers intégrées
        task_result = celery_app.send_task(
            "covers.extract_embedded",
            args=[file_paths],
            queue="deferred"
        )
        
        logger.info(f"[COVER API] Tâche extract_embedded déclenchée avec ID: {task_result.id}")
        
        return {
            "status": "success",
            "message": f"Scan des covers intégrées dans {len(file_paths)} fichiers déclenché",
            "task_id": task_result.id,
            "files_count": len(file_paths)
        }
        
    except Exception as e:
        logger.error(f"[COVER API] Erreur lors du scan des covers intégrées: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema")
async def get_cover_schema():
    """Retourne le schéma JSON attendu pour CoverCreate."""
    return CoverCreate.model_json_schema()

@router.get("/types")
async def get_cover_types():
    """Retourne les types de couverture disponibles."""
    return CoverService.get_cover_types()


@router.post("/rescans/artist/{artist_id}")
async def rescan_artist_images(
    artist_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Relance le scan des images d'un artiste."""
    try:
        logger.info(f"Début rescan des images pour l'artiste {artist_id}")
        
        # Déclencher la tâche Celery pour traiter les images de l'artiste
        from backend_worker.tasks.covers_tasks import process_artist_images
        task_result = process_artist_images.delay([artist_id], priority="normal")
        
        logger.info(f"Tâche de rescan des images de l'artiste {artist_id} déclenchée avec ID: {task_result.id}")
        
        return {
            "success": True,
            "message": f"Rescan des images de l'artiste {artist_id} initié",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du rescan des images de l'artiste {artist_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rescans/album/{album_id}")
async def rescan_album_covers(
    album_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Relance le scan des covers d'un album."""
    try:
        logger.info(f"Début rescan des covers pour l'album {album_id}")
        
        # Déclencher la tâche Celery pour traiter les covers de l'album
        from backend_worker.tasks.covers_tasks import process_album_covers
        task_result = process_album_covers.delay([album_id], priority="normal")
        
        logger.info(f"Tâche de rescan des covers de l'album {album_id} déclenchée avec ID: {task_result.id}")
        
        return {
            "success": True,
            "message": f"Rescan des covers de l'album {album_id} initié",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du rescan des covers de l'album {album_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rescans/track/{track_id}")
async def rescan_track_embedded_cover(
    track_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Relance le scan de la cover intégrée d'une track."""
    try:
        logger.info(f"Début rescan de la cover de la track {track_id}")
        
        # Récupérer les informations sur la track
        from backend.api.services.track_service import TrackService
        track_service = TrackService(db)
        track = track_service.get_track(track_id)
        
        if not track:
            raise HTTPException(status_code=404, detail="Track non trouvée")
            
        # Déclencher la tâche Celery pour traiter la cover intégrée de la track
        from backend_worker.tasks.covers_tasks import extract_embedded
        task_result = extract_embedded.delay([track.path])
        
        logger.info(f"Tâche de rescan de la cover de la track {track_id} déclenchée avec ID: {task_result.id}")
        
        return {
            "success": True,
            "message": f"Rescan de la cover de la track {track_id} initié",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du rescan de la cover de la track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
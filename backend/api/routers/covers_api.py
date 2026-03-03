from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.api.utils.database import get_async_session
from backend.api.schemas.covers_schema import CoverCreate, Cover as CoverSchema
from backend.api.services.covers_service import CoverService
from backend.api.models.covers_model import EntityCoverType
from backend.api.utils.logging import logger
from backend.api.utils.celery_app import celery_app
import base64
from pathlib import Path

router = APIRouter(prefix="/covers", tags=["covers"])

# Chemin absolu vers le placeholder (calculé depuis l'emplacement de ce fichier)
PLACEHOLDER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "static" / "logo.png"

@router.post("/", response_model=CoverSchema)
async def create_cover(cover: CoverCreate, db: AsyncSession = Depends(get_async_session)):
    """Crée une cover et la convertit en WebP."""
    service = CoverService(db)
    try:
        # Conversion base64 → WebP
        binary = base64.b64decode(cover.cover_data)
        webp_bytes = service.normalize_cover(binary, size=256)

        # Stockage WebP sur disque
        service.store_entity_cover(cover.entity_type, cover.entity_id, webp_bytes)

        cover.url = f"/covers/{cover.entity_type}/{cover.entity_id}"
        return await service.create_or_update_cover(cover)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{entity_type}/{entity_id}")
async def serve_cover(entity_type: str, entity_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Sert une cover WebP.
    - Si WebP existe sur disque → renvoie directement
    - Sinon si base64 en DB → convertit à la volée, stocke en WebP, renvoie
    - Sinon → placeholder
    """
    service = CoverService(db)

    # 1️⃣ Vérifie si WebP existe sur disque
    logger.info(f"[COVER API] Appel de get_cover_path avec entity_type={entity_type}, entity_id={entity_id}")
    webp_path = service.get_cover_path(entity_type, entity_id)
    logger.info(f"[COVER API] Résultat get_cover_path: {webp_path}")
    if webp_path:
        return FileResponse(
            webp_path,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    # 2️⃣ Fallback base64
    logger.info(f"[COVER API] Tentative fallback base64 pour {entity_type}/{entity_id}")
    cover_db = await service.get_cover(entity_type, entity_id)
    logger.info(f"[COVER API] Résultat get_cover DB: {cover_db}")
    if cover_db and getattr(cover_db, "cover_data", None):
        try:
            logger.info(f"[COVER API] Conversion base64 → WebP pour {entity_type}/{entity_id}")
            binary = base64.b64decode(cover_db.cover_data)
            webp_bytes = service.normalize_cover(binary, size=256)
            service.store_entity_cover(entity_type, entity_id, webp_bytes)
            return Response(
                content=webp_bytes,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=86400"}
            )
        except Exception as e:
            logger.error(f"[COVER API] Erreur conversion WebP: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erreur conversion WebP: {str(e)}")

    # Fallback placeholder
    logger.warning(f"[COVER API] Aucune cover trouvée pour {entity_type}/{entity_id}, utilisation du placeholder")
    
    # Vérifier si le fichier placeholder existe
    if PLACEHOLDER_PATH.exists():
        logger.info(f"[COVER API] Placeholder trouvé: {PLACEHOLDER_PATH}")
        return FileResponse(
            str(PLACEHOLDER_PATH),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    else:
        # Si le fichier n'existe pas, retourner une erreur 404 explicite
        logger.error(f"[COVER API] Placeholder non trouvé: {PLACEHOLDER_PATH}")
        raise HTTPException(
            status_code=404,
            detail=f"Aucune cover trouvée pour {entity_type}/{entity_id} et placeholder indisponible"
        )



@router.get("/", response_model=List[CoverSchema])
async def get_covers(
    entity_type: Optional[EntityCoverType] = Query(None),
    db: AsyncSession = Depends(get_async_session)
):
    """Liste les covers avec filtrage optionnel par type."""
    service = CoverService(db)
    return await service.get_covers(entity_type)

@router.delete("/{entity_type}/{entity_id}")
async def delete_cover(
    entity_type: EntityCoverType,
    entity_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Supprime une cover."""
    service = CoverService(db)
    deleted = await service.delete_cover(entity_type, entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    return {"status": "success"}

@router.put("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def update_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    cover: CoverCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Met à jour une cover existante."""
    service = CoverService(db)
    db_cover = await service.update_cover(entity_type, entity_id, cover)
    if db_cover is None:
        raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
    logger.info(f"Cover mise à jour pour {entity_type} {entity_id}")
    return db_cover

@router.post("/scan/artist/{artist_id}")
async def scan_artist_images(artist_id: int, db: AsyncSession = Depends(get_async_session)):
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
async def scan_album_images(album_id: int, db: AsyncSession = Depends(get_async_session)):
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
async def scan_all_artist_images(db: AsyncSession = Depends(get_async_session)):
    """Relance le scan des images de tous les artistes."""
    try:
        logger.info("[COVER API] Début scan images pour tous les artistes")
        
        # Récupérer tous les IDs d'artistes depuis la DB
        from sqlalchemy import select
        from backend.api.models.artists_model import Artist
        result = await db.execute(select(Artist.id))
        artist_ids = [row[0] for row in result.all()]
        
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
async def scan_all_album_images(db: AsyncSession = Depends(get_async_session)):
    """Relance le scan des images de tous les albums."""
    try:
        logger.info("[COVER API] Début scan images pour tous les albums")
        
        # Récupérer tous les IDs d'albums depuis la DB
        from sqlalchemy import select
        from backend.api.models.albums_model import Album
        result = await db.execute(select(Album.id))
        album_ids = [row[0] for row in result.all()]
        
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
async def scan_embedded_covers(directory: Optional[str] = None, db: AsyncSession = Depends(get_async_session)):
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
            from sqlalchemy import select
            from backend.api.models.tracks_model import Track
            result = await db.execute(select(Track.path))
            file_paths = [row[0] for row in result.all()]
            
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
    db: AsyncSession = Depends(get_async_session)
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
    db: AsyncSession = Depends(get_async_session)
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
    db: AsyncSession = Depends(get_async_session)
):
    """Relance le scan de la cover intégrée d'une track."""
    try:
        logger.info(f"Début rescan de la cover de la track {track_id}")
        
        # Récupérer les informations sur la track
        from backend.api.services.track_service import TrackService
        track_service = TrackService(db)
        track = await track_service.read_track(track_id)
        
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
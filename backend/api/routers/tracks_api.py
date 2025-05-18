from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from typing import List, Optional
from backend.database import get_db
from backend.api.schemas.tracks_schema import TrackCreate, Track, TrackWithRelations
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.models.artists_model import Artist as ArtistModel
from helpers.logging import logger

router = APIRouter(prefix="/api/tracks", tags=["tracks"])

@router.get("/search", response_model=List[Track])
async def search_tracks(
    title: Optional[str] = Query(None),
    artist: Optional[str] = Query(None),
    album: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    path: Optional[str] = Query(None),
    musicbrainz_id: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche avancée de pistes."""
    query = db.query(TrackModel)

    if title:
        query = query.filter(func.lower(TrackModel.title).like(f"%{title.lower()}%"))
    if path:
        query = query.filter(TrackModel.path == path)
    if genre:
        query = query.filter(func.lower(TrackModel.genre).like(f"%{genre.lower()}%"))
    if year:
        query = query.filter(TrackModel.year == year)
    if musicbrainz_id:
        query = query.filter(TrackModel.musicbrainz_id == musicbrainz_id)

    return query.all()

@router.post("/", response_model=Track)
async def create_track(track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        # Vérifier si la piste existe
        existing_track = db.query(TrackModel).filter(TrackModel.path == track.path).first()
        if existing_track:
            # Mettre à jour les infos manquantes
            updated = False
            for key, value in track.model_dump(exclude_unset=True).items():
                if value and not getattr(existing_track, key):
                    setattr(existing_track, key, value)
                    updated = True
            
            if updated:
                existing_track.date_modified = func.now()
                db.commit()
                db.refresh(existing_track)
            
            return Track.model_validate(existing_track)

        # Vérifier que l'artiste existe
        artist = db.query(ArtistModel).filter(ArtistModel.id == track.artist_id).first()
        if not artist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artiste {track.artist_id} non trouvé"
            )

        # Créer la nouvelle piste
        track_data = track.model_dump(exclude_unset=True)
        db_track = TrackModel(**track_data)
        
        try:
            db.add(db_track)
            db.commit()
            db.refresh(db_track)
            logger.info(f"Nouvelle piste créée: {track.path}")
            return Track.model_validate(db_track)
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Erreur d'intégrité: {str(e)}")
            if "UNIQUE constraint" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cette piste existe déjà"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=List[Track])
async def read_tracks(
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySession = Depends(get_db)
):
    try:
        tracks = db.query(TrackModel).offset(skip).limit(limit).all()
        return tracks
    except Exception as e:
        logger.error(f"Erreur lecture pistes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{track_id}", response_model=TrackWithRelations)
async def read_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    return track

@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if db_track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    for key, value in track.dict().items():
        setattr(db_track, key, value)
    
    db.commit()
    db.refresh(db_track)
    return db_track

@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    db.delete(track)
    db.commit()
    return {"ok": True}



from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_

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
    genre_tags: Optional[List[str]] = Query(None),
    mood_tags: Optional[List[str]] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche avancée de pistes."""
    query = db.query(TrackModel).distinct()

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
    if genre_tags:
        query = query.join(TrackModel.genre_tags).filter(
            TrackModel.genre_tags.any(name=tag) for tag in genre_tags
        )
    if mood_tags:
        query = query.join(TrackModel.mood_tags).filter(
            TrackModel.mood_tags.any(name=tag) for tag in mood_tags
        )

    return query.all()

@router.post("/", response_model=Track)
async def create_track(track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    """Création d'une nouvelle piste avec gestion des tags."""
    try:
        from backend.api.models.tracks_model import Track as TrackModel, GenreTag, MoodTag

        # Vérifier si la piste existe
        existing_track = db.query(TrackModel).filter(TrackModel.path == track.path).first()
        if existing_track:
            # Extraire les tags
            genre_tags = track.genre_tags if hasattr(track, 'genre_tags') else []
            mood_tags = track.mood_tags if hasattr(track, 'mood_tags') else []
            
            # Mettre à jour les infos de base
            track_data = track.model_dump(exclude={'genre_tags', 'mood_tags'})
            for key, value in track_data.items():
                if value and hasattr(existing_track, key):
                    setattr(existing_track, key, value)
            
            # Mettre à jour les genre_tags si fournis
            if genre_tags:
                existing_track.genre_tags = []
                for tag_name in genre_tags:
                    tag = db.query(GenreTag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = GenreTag(name=tag_name)
                        db.add(tag)
                    existing_track.genre_tags.append(tag)

            # Mettre à jour les mood_tags si fournis
            if mood_tags:
                existing_track.mood_tags = []
                for tag_name in mood_tags:
                    tag = db.query(MoodTag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = MoodTag(name=tag_name)
                        db.add(tag)
                    existing_track.mood_tags.append(tag)

            existing_track.date_modified = func.now()
            db.commit()
            db.refresh(existing_track)
            return Track.model_validate(existing_track)

        # Créer une nouvelle piste
        # Extraire les tags avant la création
        genre_tags = track.genre_tags if hasattr(track, 'genre_tags') else []
        mood_tags = track.mood_tags if hasattr(track, 'mood_tags') else []
        
        # Créer la piste sans les tags
        track_data = track.model_dump(exclude={'genre_tags', 'mood_tags'})
        db_track = TrackModel(**track_data)

        # Ajouter les genre_tags
        for tag_name in genre_tags:
            tag = db.query(GenreTag).filter_by(name=tag_name).first()
            if not tag:
                tag = GenreTag(name=tag_name)
                db.add(tag)
            db_track.genre_tags.append(tag)

        # Ajouter les mood_tags
        for tag_name in mood_tags:
            tag = db.query(MoodTag).filter_by(name=tag_name).first()
            if not tag:
                tag = MoodTag(name=tag_name)
                db.add(tag)
            db_track.mood_tags.append(tag)

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
    """Récupère une piste avec ses relations."""
    track = (
        db.query(TrackModel)
        .filter(TrackModel.id == track_id)
        .options(
            joinedload(TrackModel.track_artist),
            joinedload(TrackModel.album),
            joinedload(TrackModel.genres),
            joinedload(TrackModel.genre_tags),
            joinedload(TrackModel.mood_tags)
        )
        .first()
    )
    
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    # Convertir en dict pour la sérialisation
    track_dict = {
        **track.__dict__,
        "track_artist": track.track_artist.__dict__ if track.track_artist else None,
        "album": track.album.__dict__ if track.album else None,
        "genres": [genre.__dict__ for genre in track.genres] if track.genres else [],
        "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],
        "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else []
    }
    
    # Nettoyer les attributs SQLAlchemy
    for dict_obj in [track_dict, track_dict["track_artist"], track_dict["album"], *track_dict["genres"]]:
        if dict_obj and "_sa_instance_state" in dict_obj:
            del dict_obj["_sa_instance_state"]
    
    return track_dict

@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    """Mise à jour d'une piste."""
    from backend.api.models.tracks_model import Track as TrackModel, GenreTag, MoodTag
    
    db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if db_track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    # Extraire les tags avant la mise à jour
    genre_tags = track.genre_tags if hasattr(track, 'genre_tags') else []
    mood_tags = track.mood_tags if hasattr(track, 'mood_tags') else []
    
    # Mettre à jour les attributs simples
    track_data = track.dict(exclude={'genre_tags', 'mood_tags'})
    for key, value in track_data.items():
        if hasattr(db_track, key):
            setattr(db_track, key, value)
    
    # Mettre à jour les genre_tags
    if genre_tags is not None:
        db_track.genre_tags = []
        for tag_name in genre_tags:
            tag = db.query(GenreTag).filter_by(name=tag_name).first()
            if not tag:
                tag = GenreTag(name=tag_name)
                db.add(tag)
            db_track.genre_tags.append(tag)
    
    # Mettre à jour les mood_tags
    if mood_tags is not None:
        db_track.mood_tags = []
        for tag_name in mood_tags:
            tag = db.query(MoodTag).filter_by(name=tag_name).first()
            if not tag:
                tag = MoodTag(name=tag_name)
                db.add(tag)
            db_track.mood_tags.append(tag)
    
    db.commit()
    db.refresh(db_track)
    return db_track

@router.put("/{track_id}/tags", response_model=Track)
async def update_track_tags(
    track_id: int,
    genre_tags: Optional[List[str]] = None,
    mood_tags: Optional[List[str]] = None,
    db: SQLAlchemySession = Depends(get_db)
):
    """Mise à jour des tags d'une piste."""
    from backend.api.models.tracks_model import GenreTag, MoodTag
    
    db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if db_track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    if genre_tags is not None:
        # Supprimer les anciens tags
        db_track.genre_tags = []
        # Ajouter les nouveaux tags
        for tag_name in genre_tags:
            tag = db.query(GenreTag).filter_by(name=tag_name).first()
            if not tag:
                tag = GenreTag(name=tag_name)
                db.add(tag)
            db_track.genre_tags.append(tag)
    
    if mood_tags is not None:
        # Supprimer les anciens tags
        db_track.mood_tags = []
        # Ajouter les nouveaux tags
        for tag_name in mood_tags:
            tag = db.query(MoodTag).filter_by(name=tag_name).first()
            if not tag:
                tag = MoodTag(name=tag_name)
                db.add(tag)
            db_track.mood_tags.append(tag)
    
    db_track.date_modified = func.now()
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



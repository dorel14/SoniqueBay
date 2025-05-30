from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.api.schemas.albums_schema import AlbumCreate, Album, AlbumWithRelations
from backend.api.models.albums_model import Album as AlbumModel
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional
from backend.database import get_db
from sqlalchemy.exc import IntegrityError
from helpers.logging import logger

router = APIRouter(prefix="/api/albums", tags=["albums"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Album])
async def search_albums(
    title: Optional[str] = Query(None),
    artist_id: Optional[int] = Query(None),
    musicbrainz_albumid: Optional[str] = Query(None),
    musicbrainz_albumartistid: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des albums avec critères MusicBrainz."""
    query = db.query(AlbumModel)

    if title:
        query = query.filter(func.lower(AlbumModel.title).like(f"%{title.lower()}%"))
    if artist_id:
        query = query.filter(AlbumModel.album_artist_id == artist_id)
    if musicbrainz_albumid:
        query = query.filter(AlbumModel.musicbrainz_albumid == musicbrainz_albumid)
    if musicbrainz_albumartistid:
        query = query.filter(AlbumModel.musicbrainz_albumartistid == musicbrainz_albumartistid)

    albums = query.all()
    return [Album.model_validate(album) for album in albums]

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
def create_album(album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        # Vérifier si l'album existe déjà par musicbrainz_id
        if album.musicbrainz_albumid:
            existing_album = db.query(AlbumModel).filter(
                AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
            ).first()
            if existing_album:
                return Album.model_validate(existing_album)

        # Vérifier par titre et artiste
        existing_album = db.query(AlbumModel).filter(
            AlbumModel.title == album.title,
            AlbumModel.album_artist_id == album.album_artist_id
        ).first()
        if existing_album:
            return Album.model_validate(existing_album)

        # Créer le nouvel album
        db_album = AlbumModel(
            **album.model_dump(exclude={"date_added", "date_modified"}),
            date_added=func.now(),
            date_modified=func.now()
        )
        db.add(db_album)
        db.commit()
        db.refresh(db_album)
        return Album.model_validate(db_album)

    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: albums.musicbrainz_albumid" in str(e):
            # Double vérification en cas de race condition
            existing = db.query(AlbumModel).filter(
                AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
            ).first()
            if existing:
                return Album.model_validate(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un album avec cet identifiant existe déjà"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Album])
def read_albums(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    albums = db.query(AlbumModel).offset(skip).limit(limit).all()
    # Convertir les dates None en datetime.now()
    return [Album.model_validate(
        {**album.__dict__,
        "date_added": album.date_added or datetime.utcnow(),
        "date_modified": album.date_modified or datetime.utcnow()
        }
    ) for album in albums]

@router.get("/{album_id}", response_model=AlbumWithRelations)
async def read_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère un album par son ID."""
    album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    
    # Créer un dictionnaire avec tous les champs nécessaires
    result = {
        "id": album.id,
        "title": album.title,
        "album_artist_id": album.album_artist_id,
        "release_year": album.release_year,
        "musicbrainz_albumid": album.musicbrainz_albumid,
        "musicbrainz_albumartistid": album.musicbrainz_albumartistid,
        "genre": album.genre,
        "cover_url": album.cover_url,
        "date_added": album.date_added,
        "date_modified": album.date_modified,
        "album_artist": {
            "id": album.album_artist.id,
            "name": album.album_artist.name,
            # autres champs artiste si nécessaire
        } if album.album_artist else None,
        "tracks": [{
            "id": track.id,
            "title": track.title,
            # autres champs track si nécessaire
        } for track in album.tracks] if album.tracks else [],
        "genres": [{
            "id": genre.id,
            "name": genre.name
        } for genre in album.genres] if album.genres else []
    }
    
    return result

@router.put("/{album_id}", response_model=Album)
def update_album(album_id: int, album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    db_album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    for key, value in album.dict().items():
        setattr(db_album, key, value)

    db.commit()
    db.refresh(db_album)
    return db_album

@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    db.delete(album)
    db.commit()
    return {"ok": True}

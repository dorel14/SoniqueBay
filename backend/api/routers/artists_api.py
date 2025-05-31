from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from typing import List, Optional
from backend.database import get_db
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from backend.api.models.artists_model import Artist as ArtistModel
from helpers.logging import logger


router = APIRouter(prefix="/api/artists", tags=["artists"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Artist])
async def search_artists(
    name: Optional[str] = Query(None),
    musicbrainz_artistid: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des artistes par nom, genre ou ID MusicBrainz."""
    query = db.query(ArtistModel)

    if name:
        query = query.filter(func.lower(ArtistModel.name).like(f"%{name.lower()}%"))
    if musicbrainz_artistid:
        query = query.filter(ArtistModel.musicbrainz_artistid == musicbrainz_artistid)
    if genre:
        query = query.filter(func.lower(ArtistModel.genre).like(f"%{genre.lower()}%"))

    return query.all()

@router.post("/", response_model=Artist)
def create_artist(artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    """Crée un nouvel artiste."""
    try:
        # Vérifier si l'artiste existe déjà
        if artist.musicbrainz_artistid:
            existing = db.query(ArtistModel).filter(
                ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
            ).first()
            if existing:
                return existing

        existing_artist = db.query(ArtistModel).filter(
            func.lower(ArtistModel.name) == func.lower(artist.name)
        ).first()

        if existing_artist:
            return existing_artist

        db_artist = ArtistModel(
            **artist.model_dump(exclude_unset=True),
            date_added=func.now(),
            date_modified=func.now()
        )
        db.add(db_artist)
        db.commit()
        db.refresh(db_artist)
        return db_artist
    except IntegrityError as e:
        db.rollback()
        # Double vérification en cas de race condition
        if "UNIQUE constraint failed: artists.musicbrainz_artistid" in str(e):
            existing = db.query(ArtistModel).filter(
                ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
            ).first()
            if existing:
                return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un artiste avec cet identifiant existe déjà"
        )

@router.get("/", response_model=List[Artist])
def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    artists = db.query(ArtistModel).offset(skip).limit(limit).all()
    return artists

@router.get("/{artist_id}", response_model=Artist)
async def read_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    try:
        artist = (
            db.query(ArtistModel)
            .options(
                joinedload(ArtistModel.covers),  # Charger explicitement les covers
                joinedload(ArtistModel.albums),
                joinedload(ArtistModel.tracks)
            )
            .filter(ArtistModel.id == artist_id)
            .first()
        )
        
        if artist is None:
            raise HTTPException(status_code=404, detail="Artist not found")

        # Convertir en dictionnaire avec les covers
        return {
            "id": artist.id,
            "name": artist.name,
            "musicbrainz_artistid": artist.musicbrainz_artistid,
            "date_added": artist.date_added,
            "date_modified": artist.date_modified,
            "covers": [
                {
                    "id": cover.id,
                    "entity_type": cover.entity_type,
                    "entity_id": cover.entity_id,
                    "cover_data": cover.cover_data,
                    "mime_type": cover.mime_type,
                    "url": cover.url,
                    "date_added": cover.date_added,
                    "date_modified": cover.date_modified
                }
                for cover in artist.covers
            ] if artist.covers else []
        }

    except Exception as e:
        logger.error(f"Error reading artist: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{artist_id}", response_model=Artist)
def update_artist(artist_id: int, artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    db_artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if db_artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    for key, value in artist.model_dump(exclude_unset=True).items():
        setattr(db_artist, key, value)
    db_artist.date_modified = func.now()  # Mise à jour compatible cross-DB
    
    db.commit()
    db.refresh(db_artist)
    return db_artist

@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    db.delete(artist)
    db.commit()
    return {"ok": True}

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from backend.api.models.genres_model import Genre
from backend.api.models.albums_model import Album
from backend.api.models.covers_model import Cover

from typing import List, Optional
from backend.utils.database import get_db
from backend.api.schemas.tracks_schema import TrackCreate, Track, TrackWithRelations
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.models.tags_model import GenreTag, MoodTag
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
    try:
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
            for tag in genre_tags:
                query = query.join(TrackModel.genre_tags).filter(GenreTag.name == tag)
        if mood_tags:
            for tag in mood_tags:
                query = query.join(TrackModel.mood_tags).filter(MoodTag.name == tag)

        tracks = query.all()
        
        # Convert to response format
        result = []
        for track in tracks:
            track_dict = {
                "id": track.id,
                "title": track.title,
                "path": track.path,
                "track_artist_id": track.track_artist_id,
                "album_id": track.album_id,
                "duration": track.duration,
                "track_number": track.track_number,
                "disc_number": track.disc_number,
                "year": track.year,
                "genre": track.genre,
                "file_type": track.file_type,
                "bitrate": track.bitrate,
                "featured_artists": track.featured_artists,
                "bpm": track.bpm,
                "key": track.key,
                "scale": track.scale,
                "danceability": track.danceability,
                "mood_happy": track.mood_happy,
                "mood_aggressive": track.mood_aggressive,
                "mood_party": track.mood_party,
                "mood_relaxed": track.mood_relaxed,
                "instrumental": track.instrumental,
                "acoustic": track.acoustic,
                "tonal": track.tonal,
                "musicbrainz_id": track.musicbrainz_id,
                "musicbrainz_albumid": track.musicbrainz_albumid,
                "musicbrainz_artistid": track.musicbrainz_artistid,
                "musicbrainz_albumartistid": track.musicbrainz_albumartistid,
                "acoustid_fingerprint": track.acoustid_fingerprint,
                "date_added": track.date_added,
                "date_modified": track.date_modified,
                "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],
                "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else []
            }
            result.append(track_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur recherche pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[Track])
async def create_or_update_tracks_batch(tracks_data: List[TrackCreate], db: SQLAlchemySession = Depends(get_db)):
    """Crée ou met à jour plusieurs pistes en une seule fois (batch)."""
    try:
        paths = [t.path for t in tracks_data if t.path]
        
        # 1. Récupérer les pistes existantes
        existing_tracks = db.query(TrackModel).filter(TrackModel.path.in_(paths)).options(joinedload('*')).all()
        existing_tracks_map = {t.path: t for t in existing_tracks}

        # 2. Pré-charger tous les tags nécessaires
        all_genre_tags_names = {tag for t in tracks_data for tag in t.genre_tags or []}
        all_mood_tags_names = {tag for t in tracks_data for tag in t.mood_tags or []}
        
        genre_tag_map = {tag.name: tag for tag in db.query(GenreTag).filter(GenreTag.name.in_(all_genre_tags_names)).all()}
        mood_tag_map = {tag.name: tag for tag in db.query(MoodTag).filter(MoodTag.name.in_(all_mood_tags_names)).all()}

        tracks_to_process = []
        new_tracks_to_create = []

        for track_data in tracks_data:
            db_track = existing_tracks_map.get(track_data.path)
            if db_track:
                # Mise à jour
                update_data = track_data.model_dump(exclude_unset=True, exclude={'genre_tags', 'mood_tags'})
                for key, value in update_data.items():
                    setattr(db_track, key, value)
                db_track.date_modified = func.now()
            else:
                # Création
                db_track = TrackModel(**track_data.model_dump(exclude={'genre_tags', 'mood_tags'}))
                new_tracks_to_create.append(db_track)

            # Gestion des tags pour la création et la mise à jour
            if track_data.genre_tags is not None:
                db_track.genre_tags = []
                for tag_name in track_data.genre_tags:
                    tag = genre_tag_map.get(tag_name)
                    if not tag:
                        tag = GenreTag(name=tag_name)
                        db.add(tag)
                        genre_tag_map[tag_name] = tag
                    db_track.genre_tags.append(tag)

            if track_data.mood_tags is not None:
                db_track.mood_tags = []
                for tag_name in track_data.mood_tags:
                    tag = mood_tag_map.get(tag_name)
                    if not tag:
                        tag = MoodTag(name=tag_name)
                        db.add(tag)
                        mood_tag_map[tag_name] = tag
                    db_track.mood_tags.append(tag)
            
            if not db_track in new_tracks_to_create:
                 tracks_to_process.append(db_track)

        if new_tracks_to_create:
            db.add_all(new_tracks_to_create)
            tracks_to_process.extend(new_tracks_to_create)

        db.commit()

        # Rafraîchir les objets pour obtenir les données complètes
        for track in tracks_to_process:
            db.refresh(track)

        return tracks_to_process

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Erreur d'intégrité lors du traitement en batch des pistes: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit de données lors du traitement en batch.")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur inattendue lors du traitement en batch des pistes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@router.post("/", response_model=Track)
async def create_track(track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    """Création d'une nouvelle piste avec gestion des tags."""
    try:
        # Vérifier si la piste existe
        existing_track = db.query(TrackModel).filter(TrackModel.path == track.path).first()
        if existing_track:
            # Extraire les tags
            genre_tags = track.genre_tags if track.genre_tags else []
            mood_tags = track.mood_tags if track.mood_tags else []
            
            # Mettre à jour les infos de base
            track_data = track.model_dump(exclude={'genre_tags', 'mood_tags'})
            for key, value in track_data.items():
                if value is not None and hasattr(existing_track, key):
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
            
            # Return formatted response
            return {
                **{k: v for k, v in existing_track.__dict__.items() if not k.startswith('_')},
                "genre_tags": [tag.name for tag in existing_track.genre_tags],
                "mood_tags": [tag.name for tag in existing_track.mood_tags]
            }

        # Créer une nouvelle piste
        genre_tags = track.genre_tags if track.genre_tags else []
        mood_tags = track.mood_tags if track.mood_tags else []
        
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
        
        # Return formatted response
        return {
            **{k: v for k, v in db_track.__dict__.items() if not k.startswith('_')},
            "genre_tags": [tag.name for tag in db_track.genre_tags],
            "mood_tags": [tag.name for tag in db_track.mood_tags]
        }

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
        # Load tracks with proper relationships
        tracks = (
            db.query(TrackModel)
            .options(
                joinedload(TrackModel.genre_tags),
                joinedload(TrackModel.mood_tags),
                joinedload(TrackModel.album),
                joinedload(TrackModel.genres),
                joinedload(TrackModel.covers)  # Ajouter le chargement des covers
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        result = []
        for track in tracks:
            # Build track dictionary safely
            track_dict = {
                "id": track.id,
                "title": track.title,
                "path": track.path,
                "track_artist_id": track.track_artist_id,
                "album_id": track.album_id,
                "duration": track.duration,
                "track_number": track.track_number,
                "disc_number": track.disc_number,
                "year": track.year,
                "genre": track.genre,
                "file_type": track.file_type,
                "bitrate": track.bitrate,
                "featured_artists": track.featured_artists,
                "bpm": track.bpm,
                "key": track.key,
                "scale": track.scale,
                "danceability": track.danceability,
                "mood_happy": track.mood_happy,
                "mood_aggressive": track.mood_aggressive,
                "mood_party": track.mood_party,
                "mood_relaxed": track.mood_relaxed,
                "instrumental": track.instrumental,
                "acoustic": track.acoustic,
                "tonal": track.tonal,
                "musicbrainz_id": track.musicbrainz_id,
                "musicbrainz_albumid": track.musicbrainz_albumid,
                "musicbrainz_artistid": track.musicbrainz_artistid,
                "musicbrainz_albumartistid": track.musicbrainz_albumartistid,
                "acoustid_fingerprint": track.acoustid_fingerprint,
                "date_added": track.date_added,
                "date_modified": track.date_modified,
                "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],
                "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else [],
                "covers": [{
                    "id": cover.id,
                    "entity_type": cover.entity_type,
                    "entity_id": cover.entity_id,
                    "cover_data": cover.cover_data,
                    "mime_type": cover.mime_type,
                    "url": cover.url,
                    "date_added": cover.date_added,
                    "date_modified": cover.date_modified
                } for cover in track.covers] if track.covers else []
            }
            
            # Add genres if available
            if hasattr(track, 'genres') and track.genres:
                track_dict["genres"] = [{"id": g.id, "name": g.name} for g in track.genres]
            
            result.append(track_dict)
            
        return result
    except Exception as e:
        logger.error(f"Erreur lecture pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{track_id}", response_model=TrackWithRelations)
async def read_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère une piste avec ses relations."""
    try:
        track = (
            db.query(TrackModel)
            .options(
                joinedload(TrackModel.genre_tags),
                joinedload(TrackModel.mood_tags),
                joinedload(TrackModel.covers),  # S'assurer que covers est chargé
                joinedload(TrackModel.album),
                joinedload(TrackModel.genres)
            )
            .filter(TrackModel.id == track_id)
            .first()
        )
        
        if track is None:
            raise HTTPException(status_code=404, detail="Piste non trouvée")
        
        # Convertir en dict pour la sérialisation
        track_dict = {
            "id": track.id,
            "title": track.title,
            "path": track.path,
            "track_artist_id": track.track_artist_id,
            "album_id": track.album_id,
            "duration": track.duration,
            "track_number": track.track_number,
            "disc_number": track.disc_number,
            "year": track.year,
            "genre": track.genre,
            "file_type": track.file_type,
            "bitrate": track.bitrate,
            "featured_artists": track.featured_artists,
            "bpm": track.bpm,
            "key": track.key,
            "scale": track.scale,
            "danceability": track.danceability,
            "mood_happy": track.mood_happy,
            "mood_aggressive": track.mood_aggressive,
            "mood_party": track.mood_party,
            "mood_relaxed": track.mood_relaxed,
            "instrumental": track.instrumental,
            "acoustic": track.acoustic,
            "tonal": track.tonal,
            "musicbrainz_id": track.musicbrainz_id,
            "musicbrainz_albumid": track.musicbrainz_albumid,
            "musicbrainz_artistid": track.musicbrainz_artistid,
            "musicbrainz_albumartistid": track.musicbrainz_albumartistid,
            "acoustid_fingerprint": track.acoustid_fingerprint,
            "date_added": track.date_added,
            "date_modified": track.date_modified,
            "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],
            "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else [],
            "covers": [{
                "id": cover.id,
                "entity_type": cover.entity_type,
                "entity_id": cover.entity_id,
                "cover_data": cover.cover_data,
                "mime_type": cover.mime_type,
                "url": cover.url,
                "date_added": cover.date_added,
                "date_modified": cover.date_modified
            } for cover in track.covers] if track.covers else []
        }
        
        # Add related data
        if track.track_artist:
            track_dict["track_artist"] = {
                "id": track.track_artist.id,
                "name": track.track_artist.name,
                "musicbrainz_artistid": track.track_artist.musicbrainz_artistid
            }
        
        if track.album:
            track_dict["album"] = {
                "id": track.album.id,
                "title": track.album.title,
                "musicbrainz_albumid": track.album.musicbrainz_albumid
            }
            
        return track_dict
            
    except Exception as e:
        logger.error(f"Erreur lecture piste: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackCreate, request: Request, db: SQLAlchemySession = Depends(get_db)):
    """Mise à jour d'une piste."""
    try:
        db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
        if db_track is None:
            raise HTTPException(status_code=404, detail="Piste non trouvée")
        
        # Extraire et nettoyer les données
        track_data = track.model_dump(
            exclude={'genre_tags', 'mood_tags', 'genres', 'date_added', 'date_modified'},
            exclude_unset=True,
            exclude_none=True
        )
        
        # Mise à jour des attributs simples
        for key, value in track_data.items():
            if hasattr(db_track, key) and not isinstance(value, (dict, list)):
                setattr(db_track, key, value)
        
        # Mise à jour des genres
        if hasattr(track, 'genres') and isinstance(track.genres, list):
            genres = []
            for genre_id in track.genres:
                genre = db.query(Genre).get(genre_id)
                if genre:
                    genres.append(genre)
            db_track.genres = genres
        
        # Mise à jour des tags de manière asynchrone
        if hasattr(track, 'genre_tags'):
            await update_track_tags(
                db_track.id,  # Envoyer directement l'objet track
                genre_tags=track.genre_tags,
                mood_tags=track.mood_tags,
                db=db
            )
        
        # Mise à jour de la date de modification
        db_track.date_modified = func.now()
        
        # Commit et refresh
        try:
            db.commit()
            db.refresh(db_track)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du commit: {str(e)}")
            raise
            
        # Conversion et retour
        return Track.model_validate(db_track)

    except Exception as e:
        logger.error(f"Erreur inattendue pour track {track_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def update_track_tags(db_track: TrackModel, genre_tags: List[str], mood_tags: List[str], db: SQLAlchemySession):
    """Fonction utilitaire pour mettre à jour les tags."""
    try:
        if genre_tags is not None:
            db_track.genre_tags = []
            for tag_name in genre_tags:
                tag = db.query(GenreTag).filter_by(name=tag_name).first()
                if not tag:
                    tag = GenreTag(name=tag_name)
                    db.add(tag)
                db_track.genre_tags.append(tag)
        
        if mood_tags is not None:
            db_track.mood_tags = []
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
    except Exception as e:
        logger.error(f"Erreur mise à jour tags: {str(e)}")
        raise

@router.put("/{track_id}/tags", response_model=Track)
async def update_track_tags(
    track_id: int,
    genre_tags: Optional[List[str]] = None,
    mood_tags: Optional[List[str]] = None,
    db: SQLAlchemySession = Depends(get_db)
) -> Track:
    """Mise à jour des tags d'une piste."""
    db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if db_track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    try:
        # Mise à jour des genre tags
        if genre_tags is not None:
            db_track.genre_tags = []
            for tag_name in genre_tags:
                tag = db.query(GenreTag).filter_by(name=tag_name).first()
                if not tag:
                    tag = GenreTag(name=tag_name)
                    db.add(tag)
                db_track.genre_tags.append(tag)
        
        # Mise à jour des mood tags
        if mood_tags is not None:
            db_track.mood_tags = []
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
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur mise à jour tags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    db.delete(track)
    db.commit()
    return {"ok": True}



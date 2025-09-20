from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from backend.api.models.genres_model import Genre
from backend.api.models.albums_model import Album
from backend.api.models.covers_model import Cover

from typing import List, Optional
from backend.utils.database import get_db
from backend.api.schemas.tracks_schema import TrackCreate, TrackUpdate, Track, TrackWithRelations
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.utils.logging import logger
from backend.services.track_service import TrackService

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
    service = TrackService(db)
    try:
        tracks = service.search_tracks(title, artist, album, genre, year, path, musicbrainz_id, genre_tags, mood_tags)
        return [Track.model_validate(t) for t in tracks]
    except Exception as e:
        logger.error(f"Erreur recherche pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[Track])
async def create_or_update_tracks_batch(tracks_data: List[TrackCreate], db: SQLAlchemySession = Depends(get_db)):
    service = TrackService(db)
    try:
        result = service.create_or_update_tracks_batch(tracks_data)
        return [Track.model_validate(t) for t in result]
    except Exception as e:
        logger.error(f"Erreur batch pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Track)
async def create_track(track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    service = TrackService(db)
    try:
        created = service.create_track(track)
        return Track.model_validate(created)
    except Exception as e:
        logger.error(f"Erreur création piste: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TrackWithRelations])
async def read_tracks(
    skip: int = 0,
    limit: int = 100,
    db: SQLAlchemySession = Depends(get_db)
):
    service = TrackService(db)
    try:
        tracks = service.read_tracks(skip, limit)
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
                "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else [],
                "covers": [{
                    "id": cover.id,
                    "entity_type": "track",
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
    service = TrackService(db)
    try:
        track = service.read_track(track_id)

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
                "entity_type": "track",
                "entity_id": cover.entity_id,
                "cover_data": cover.cover_data,
                "mime_type": cover.mime_type,
                "url": cover.url,
                "date_added": cover.date_added,
                "date_modified": cover.date_modified
            } for cover in track.covers] if track.covers else []
        }

        # Add related data
        if track.artist:
            track_dict["track_artist"] = {
                "id": track.artist.id,
                "name": track.artist.name,
                "musicbrainz_artistid": track.artist.musicbrainz_artistid
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


@router.get("/artists/{artist_id}/albums/{album_id}", response_model=List[TrackWithRelations])
async def read_artist_tracks_by_album(artist_id: int, album_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère les pistes d'un artiste pour un album spécifique."""
    service = TrackService(db)
    tracks = service.get_artist_tracks(artist_id, album_id)
    return [TrackWithRelations.model_validate(t).model_dump() for t in tracks]

@router.get("/artists/{artist_id}", response_model=List[TrackWithRelations])
async def read_artist_tracks(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère toutes les pistes d'un artiste."""
    service = TrackService(db)
    tracks = service.get_artist_tracks(artist_id)
    return [TrackWithRelations.model_validate(t).model_dump() for t in tracks]


@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackUpdate, request: Request, db: SQLAlchemySession = Depends(get_db)):
    """Mise à jour d'une piste."""
    service = TrackService(db)
    try:
        updated_track = service.update_track(track_id, track)
        if not updated_track:
            raise HTTPException(status_code=404, detail="Piste non trouvée")

        # Conversion et retour
        return Track.model_validate(updated_track)

    except Exception as e:
        logger.error(f"Erreur inattendue pour track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{track_id}/tags", response_model=Track)
async def update_track_tags(
    track_id: int,
    genre_tags: Optional[List[str]] = None,
    mood_tags: Optional[List[str]] = None,
    db: SQLAlchemySession = Depends(get_db)
) -> Track:
    """Mise à jour des tags d'une piste."""
    service = TrackService(db)
    try:
        updated_track = service.update_track_tags(track_id, genre_tags, mood_tags)
        if not updated_track:
            raise HTTPException(status_code=404, detail="Piste non trouvée")
        return Track.model_validate(updated_track)

    except Exception as e:
        logger.error(f"Erreur mise à jour tags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = TrackService(db)
    success = service.delete_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    return {"ok": True}



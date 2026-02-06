from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache import FastAPICache

from typing import List, Optional
import json
from backend.api.utils.database import get_async_session
from backend.api.schemas.tracks_schema import TrackCreate, TrackUpdate, Track, TrackWithRelations
from backend.api.utils.logging import logger
from backend.api.utils.validation_logger import log_validation_error
from backend.api.services.track_service import TrackService

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/count")
async def get_tracks_count(db: AsyncSession = Depends(get_async_session)):
    """Get the total number of tracks in the database."""
    service = TrackService(db)
    count = await service.get_tracks_count()
    return {"count": count}


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
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session)
):
    """Recherche avancée de pistes."""
    service = TrackService(db)
    try:
        # Create cache key
        cache_key = f"tracks_search:{title or ''}:{artist or ''}:{album or ''}:{genre or ''}:{year or ''}:{path or ''}:{musicbrainz_id or ''}:{','.join(sorted(genre_tags or []))}:{','.join(sorted(mood_tags or []))}:{skip}:{limit or 'none'}"

        # Try to get from cache
        cached_result = await FastAPICache.get_backend().get(cache_key)
        if cached_result:
            logger.info("Cache hit for tracks search")
            tracks_data = json.loads(cached_result.decode('utf-8'))
            return [Track.model_validate(t) for t in tracks_data]

        tracks = await service.search_tracks(title, artist, album, genre, year, path, musicbrainz_id, genre_tags, mood_tags, skip, limit)
        tracks_data = [Track.model_validate(t).model_dump() for t in tracks]

        # Convert datetime objects to strings for JSON serialization
        def serialize_for_json(obj):
            if isinstance(obj, dict):
                return {k: serialize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_for_json(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            else:
                return obj

        serializable_tracks_data = serialize_for_json(tracks_data)

        # Cache the result
        await FastAPICache.get_backend().set(cache_key, json.dumps(serializable_tracks_data).encode('utf-8'), expire=300)
        logger.info("Cached tracks search result")

        return tracks_data
    except Exception as e:
        logger.error(f"Erreur recherche pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[Track])
async def create_or_update_tracks_batch(tracks_data: List[TrackCreate], request: Request = None, db: AsyncSession = Depends(get_async_session)):
    """Crée ou met à jour un lot de pistes.
    
    Note: Les caractéristiques audio doivent être gérées via l'endpoint /api/tracks/audio-features
    après la création des pistes.
    """
    service = TrackService(db)
    try:
        result = await service.create_or_update_tracks_batch(tracks_data)
        return [Track.model_validate(t) for t in result]
    except ValidationError as e:
        log_validation_error(
            endpoint="/api/tracks/batch",
            method="POST",
            request_data=[track.model_dump() for track in tracks_data] if tracks_data else [],
            validation_error=e,
            request=request
        )
        raise HTTPException(status_code=422, detail=f"Erreur de validation des données: {e}")
    except Exception as e:
        logger.error(f"Erreur batch pistes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Track)
async def create_track(track: TrackCreate, request: Request = None, db: AsyncSession = Depends(get_async_session)):
    """Crée une nouvelle piste.
    
    Note: Les caractéristiques audio doivent être gérées via l'endpoint /api/tracks/audio-features
    après la création de la piste.
    """
    service = TrackService(db)
    try:
        created = await service.create_track(track)
        return Track.model_validate(created)
    except ValidationError as e:
        log_validation_error(
            endpoint="/api/tracks",
            method="POST",
            request_data=track.model_dump() if track else {},
            validation_error=e,
            request=request
        )
        raise HTTPException(status_code=422, detail=f"Erreur de validation des données: {e}")
    except Exception as e:
        logger.error(f"Erreur création piste: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TrackWithRelations])
async def read_tracks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """Récupère une liste de pistes avec leurs relations."""
    service = TrackService(db)
    try:
        tracks = await service.read_tracks(skip, limit)
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
async def read_track(track_id: int, db: AsyncSession = Depends(get_async_session)):
    """Récupère une piste avec ses relations."""
    service = TrackService(db)
    try:
        track = await service.read_track(track_id)

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
async def read_artist_tracks_by_album(artist_id: int, album_id: int, db: AsyncSession = Depends(get_async_session)):
    """Récupère les pistes d'un artiste pour un album spécifique."""
    service = TrackService(db)
    tracks = await service.get_artist_tracks(artist_id, album_id)
    return [TrackWithRelations.model_validate(t).model_dump() for t in tracks]


@router.get("/artists/{artist_id}", response_model=List[TrackWithRelations])
async def read_artist_tracks(artist_id: int, db: AsyncSession = Depends(get_async_session)):
    """Récupère toutes les pistes d'un artiste."""
    service = TrackService(db)
    tracks = await service.get_artist_tracks(artist_id)
    return [TrackWithRelations.model_validate(t).model_dump() for t in tracks]


@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackUpdate, request: Request, db: AsyncSession = Depends(get_async_session)):
    """Mise à jour d'une piste."""
    service = TrackService(db)
    try:
        updated_track = await service.update_track(track_id, track)
        if not updated_track:
            raise HTTPException(status_code=404, detail="Piste non trouvée")
        return Track.model_validate(updated_track)
    except Exception as e:
        logger.error(f"Erreur inattendue pour track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{track_id}/tags", response_model=Track)
async def update_track_tags(
    track_id: int,
    genre_tags: Optional[List[str]] = None,
    mood_tags: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_async_session)
) -> Track:
    """Mise à jour des tags d'une piste."""
    service = TrackService(db)
    try:
        updated_track = await service.update_track_tags(track_id, genre_tags, mood_tags)
        if not updated_track:
            raise HTTPException(status_code=404, detail="Piste non trouvée")
        return Track.model_validate(updated_track)
    except Exception as e:
        logger.error(f"Erreur mise à jour tags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: int, db: AsyncSession = Depends(get_async_session)):
    """Supprime une piste."""
    service = TrackService(db)
    success = await service.delete_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    return {"ok": True}


# NOTE: Les endpoints pour les caractéristiques audio ont été migrés vers:
# - POST /api/tracks/audio-features/analyze pour l'analyse audio
# - PUT /api/tracks/audio-features/{track_id} pour la mise à jour
# - GET /api/tracks/audio-features/{track_id} pour la récupération
# Voir backend/api/routers/track_audio_features_api.py

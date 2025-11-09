from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session as SQLAlchemySession

from typing import List, Optional
import json
import asyncio
import redis.asyncio as redis
from backend.library_api.utils.database import get_db
from backend.library_api.api.schemas.tracks_schema import TrackCreate, TrackUpdate, Track, TrackWithRelations
from backend.library_api.api.models.tracks_model import Track as TrackModel
from backend.library_api.utils.logging import logger
from backend.library_api.utils.validation_logger import log_validation_error
from backend.library_api.services.track_service import TrackService

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
async def create_or_update_tracks_batch(tracks_data: List[TrackCreate], request: Request = None, db: SQLAlchemySession = Depends(get_db)):
    service = TrackService(db)
    try:
        result = service.create_or_update_tracks_batch(tracks_data)

        # Publier les événements via Redis pour déclencher la vectorisation
        # Note: La communication se fait maintenant via Redis PubSub au lieu d'appels HTTP directs
        # pour respecter la séparation des conteneurs
        try:
            import asyncio
            import redis.asyncio as redis

            async def publish_vectorization_events():
                try:
                    # Connexion Redis pour publier les événements
                    redis_client = redis.Redis(
                        host='redis',
                        port=6379,
                        db=0,
                        decode_responses=True
                    )

                    for track in result:
                        # Préparer les métadonnées pour la vectorisation (champs directs uniquement)
                        event_data = {
                            "track_id": str(track.id),
                            "title": track.title,
                            "genre": track.genre or "",
                            "year": track.year,
                            "duration": track.duration,
                            "bitrate": track.bitrate,
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
                            "genre_main": getattr(track, 'genre_main', None),
                            "camelot_key": getattr(track, 'camelot_key', None),
                            # Utiliser les tags directs si disponibles, sinon liste vide
                            "genre_tags": getattr(track, 'genre_tags', []) or [],
                            "mood_tags": getattr(track, 'mood_tags', []) or []
                        }

                        await redis_client.publish("tracks.to_vectorize", json.dumps({
                            "type": "track_created",
                            "timestamp": asyncio.get_event_loop().time(),
                            **event_data
                        }))

                    await redis_client.close()

                except Exception as e:
                    logger.warning(f"Erreur publication événements vectorisation batch: {e}")

            # Lancer la publication de manière asynchrone (non-bloquante)
            asyncio.create_task(publish_vectorization_events())

        except Exception as e:
            logger.warning(f"Erreur initialisation publication vectorisation batch: {e}")
            # Ne pas échouer la création de tracks pour autant

        return [Track.model_validate(t) for t in result]
    except ValidationError as e:
        # Gestion spécifique des erreurs de validation Pydantic
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
async def create_track(track: TrackCreate, request: Request = None, db: SQLAlchemySession = Depends(get_db)):
    service = TrackService(db)
    try:
        created = service.create_track(track)

        # Publier l'événement via Redis pour déclencher la vectorisation
        try:
            async def publish_vectorization_event():
                try:
                    # Connexion Redis pour publier l'événement
                    redis_client = redis.Redis(
                        host='redis',
                        port=6379,
                        db=0,
                        decode_responses=True
                    )

                    # Préparer les métadonnées pour la vectorisation (champs directs uniquement)
                    event_data = {
                        "track_id": str(created.id),
                        "title": created.title,
                        "genre": created.genre or "",
                        "year": created.year,
                        "duration": created.duration,
                        "bitrate": created.bitrate,
                        "bpm": created.bpm,
                        "key": created.key,
                        "scale": created.scale,
                        "danceability": created.danceability,
                        "mood_happy": created.mood_happy,
                        "mood_aggressive": created.mood_aggressive,
                        "mood_party": created.mood_party,
                        "mood_relaxed": created.mood_relaxed,
                        "instrumental": created.instrumental,
                        "acoustic": created.acoustic,
                        "tonal": created.tonal,
                        "genre_main": getattr(created, 'genre_main', None),
                        "camelot_key": getattr(created, 'camelot_key', None),
                        # Utiliser les tags directs si disponibles, sinon liste vide
                        "genre_tags": getattr(created, 'genre_tags', []) or [],
                        "mood_tags": getattr(created, 'mood_tags', []) or []
                    }

                    await redis_client.publish("tracks.to_vectorize", json.dumps({
                        "type": "track_created",
                        "timestamp": asyncio.get_event_loop().time(),
                        **event_data
                    }))

                    await redis_client.close()

                except Exception as e:
                    logger.warning(f"Erreur publication événement vectorisation: {e}")

            # Lancer la publication de manière asynchrone (non-bloquante)
            asyncio.create_task(publish_vectorization_event())

        except Exception as e:
            logger.warning(f"Erreur initialisation publication vectorisation: {e}")
            # Ne pas échouer la création de track pour autant

        return Track.model_validate(created)
    except ValidationError as e:
        # Gestion spécifique des erreurs de validation Pydantic
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

        # Publier l'événement via Redis pour déclencher la vectorisation si des métadonnées importantes ont changé
        try:
            # Vérifier si des champs impactant la vectorisation ont été modifiés
            important_fields = ['title', 'artist_id', 'album_id', 'genre', 'year', 'duration', 'bitrate', 'bpm', 'key', 'scale']
            if any(getattr(track, field, None) is not None for field in important_fields):

                async def publish_vectorization_event():
                    try:
                        # Connexion Redis pour publier l'événement
                        redis_client = redis.Redis(
                            host='redis',
                            port=6379,
                            db=0,
                            decode_responses=True
                        )

                        # Préparer les métadonnées pour la vectorisation (champs directs uniquement)
                        event_data = {
                            "track_id": str(updated_track.id),
                            "title": updated_track.title,
                            "genre": updated_track.genre or "",
                            "year": updated_track.year,
                            "duration": updated_track.duration,
                            "bitrate": updated_track.bitrate,
                            "bpm": updated_track.bpm,
                            "key": updated_track.key,
                            "scale": updated_track.scale,
                            "danceability": updated_track.danceability,
                            "mood_happy": updated_track.mood_happy,
                            "mood_aggressive": updated_track.mood_aggressive,
                            "mood_party": updated_track.mood_party,
                            "mood_relaxed": updated_track.mood_relaxed,
                            "instrumental": updated_track.instrumental,
                            "acoustic": updated_track.acoustic,
                            "tonal": updated_track.tonal,
                            "genre_main": getattr(updated_track, 'genre_main', None),
                            "camelot_key": getattr(updated_track, 'camelot_key', None),
                            # Utiliser les tags directs si disponibles, sinon liste vide
                            "genre_tags": getattr(updated_track, 'genre_tags', []) or [],
                            "mood_tags": getattr(updated_track, 'mood_tags', []) or []
                        }

                        await redis_client.publish("tracks.to_vectorize", json.dumps({
                            "type": "track_updated",
                            "timestamp": asyncio.get_event_loop().time(),
                            **event_data
                        }))

                        await redis_client.close()

                    except Exception as e:
                        logger.warning(f"Erreur publication événement vectorisation update: {e}")

                # Lancer la publication de manière asynchrone (non-bloquante)
                asyncio.create_task(publish_vectorization_event())

        except Exception as e:
            logger.warning(f"Erreur initialisation publication vectorisation update: {e}")
            # Ne pas échouer la mise à jour de track pour autant

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

@router.post("/analyze-audio", status_code=status.HTTP_202_ACCEPTED)
async def analyze_audio_tracks(
    track_ids: Optional[List[int]] = None,
    limit: int = 100,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Déclenche l'analyse audio des pistes.

    Args:
        track_ids: Liste spécifique d'IDs de tracks, ou None pour analyser toutes les tracks sans features
        limit: Nombre maximum de tracks à analyser
        db: Session de base de données

    Returns:
        Informations sur la tâche lancée
    """
    try:
        from backend.library_api.utils.celery_app import celery

        if track_ids:
            # Analyser les tracks spécifiques
            logger.info(f"Analyse audio demandée pour {len(track_ids)} tracks spécifiques")
            # Récupérer les chemins des fichiers
            tracks = db.query(TrackModel).filter(TrackModel.id.in_(track_ids)).all()
            track_data_list = [(track.id, track.path) for track in tracks if track.path]
        else:
            # Analyser les tracks sans caractéristiques audio
            logger.info(f"Analyse audio demandée pour tracks sans features (limit: {limit})")
            tracks = db.query(TrackModel).filter(
                TrackModel.bpm.is_(None) | TrackModel.key.is_(None)
            ).limit(limit).all()
            track_data_list = [(track.id, track.path) for track in tracks if track.path]

        if not track_data_list:
            return {"message": "Aucune track à analyser", "count": 0}

        # Lancer la tâche Celery
        result = celery.send_task("analyze_audio_batch_task", args=[track_data_list])

        logger.info(f"Tâche d'analyse audio lancée: {result.id} pour {len(track_data_list)} tracks")

        return {
            "task_id": result.id,
            "message": f"Analyse audio lancée pour {len(track_data_list)} tracks",
            "count": len(track_data_list)
        }

    except Exception as e:
        logger.error(f"Erreur lancement analyse audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement de l'analyse: {str(e)}")

@router.put("/{track_id}/features", status_code=status.HTTP_200_OK)
async def update_track_features(
    track_id: int,
    features: dict,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Met à jour les caractéristiques audio d'une track.

    Args:
        track_id: ID de la track
        features: Dictionnaire des caractéristiques audio
        db: Session de base de données

    Returns:
        Confirmation de mise à jour
    """
    try:
        service = TrackService(db)
        track = service.read_track(track_id)

        if not track:
            raise HTTPException(status_code=404, detail="Track non trouvée")

        # Mise à jour des champs audio
        update_data = {}
        audio_fields = [
            'bpm', 'key', 'scale', 'danceability', 'mood_happy', 'mood_aggressive',
            'mood_party', 'mood_relaxed', 'instrumental', 'acoustic', 'tonal',
            'camelot_key', 'genre_main'
        ]

        for field in audio_fields:
            if field in features:
                update_data[field] = features[field]

        if update_data:
            updated_track = service.update_track(track_id, update_data)
            if not updated_track:
                raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")

        return {"message": f"Caractéristiques audio mises à jour pour track {track_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour features track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")



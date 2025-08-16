from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from backend.utils.database import get_db
from typing import List, Optional
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.schemas.tracks_schema import Track, TrackWithRelations
from backend.api.schemas.covers_schema import Cover
from backend.utils.logging import logger



async def get_artist_tracks(artist_id: int, album_id: int = None, db: SQLAlchemySession = Depends(get_db)):
    """Récupère les pistes d'un artiste depuis l'API."""
    try:
        query = db.query(TrackModel).filter(TrackModel.track_artist_id == artist_id)
        if album_id:
            query = query.filter(TrackModel.album_id == album_id)
        tracks = query.all()

        track_list = []
        for track in tracks:
            track_data = {
                **track.__dict__,
                "covers": [Cover.model_validate(c) for c in track.covers],
                "album_title": track.album.title if track.album else None # Access the album title from the relationship
            }
            track_model = TrackWithRelations(**track_data) # Create a TrackWithRelations object
            track_list.append(track_model)

        return track_list

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des pistes de l'artiste {artist_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des pistes de l'artiste")
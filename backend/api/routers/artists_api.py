from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi_cache.decorator import cache
from backend.api.schemas.pagination_schema import PaginatedArtists
from backend.api.schemas.artist_similar_schema import ArtistSimilarCreate, ArtistSimilarUpdate, ArtistSimilarWithDetails, ArtistSimilarListResponse
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.api.utils.database import get_db
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from backend.api.services.artist_service import ArtistService
from backend.api.services.artist_similar_service import ArtistSimilarService
from backend.api.models.artists_model import Artist as ArtistModel
from backend.api.utils.logging import logger


router = APIRouter(prefix="/artists", tags=["artists"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Artist])
@cache(expire=300)  # Cache for 5 minutes
async def search_artists(
    name: Optional[str] = Query(None),
    musicbrainz_artistid: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: SQLAlchemySession = Depends(get_db)
):
    service = ArtistService(db)
    artists = service.search_artists(name, musicbrainz_artistid, genre, skip, limit)
    return [Artist.model_validate(a) for a in artists]

@router.post("/batch", response_model=List[Artist])
def create_artists_batch(artists: List[ArtistCreate], db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    try:
        result = service.create_artists_batch(artists)
        return [Artist.model_validate(a) for a in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Artist)
def create_artist(artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    try:
        created = service.create_artist(artist)
        return Artist.model_validate(created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

""" @router.get("/", response_model=PaginatedResponse[Artist])
async def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    artists = db.query(ArtistModel).order_by('name').offset(skip).limit(limit)
    return paginate_query(artists, skip, limit) """


@router.get("/count")
@cache(expire=300)  # Cache for 5 minutes
def get_artists_count(db: SQLAlchemySession = Depends(get_db)):
    """Get the total number of artists in the database."""
    service = ArtistService(db)
    count = service.get_artists_count()
    return {"count": count}

@router.get("/", response_model=PaginatedArtists)
def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    artists, total_count = service.get_artists_paginated(skip, limit)
    return {
        "count": total_count,
        "results": [Artist.model_validate(a) for a in artists]
    }

@router.get("/{artist_id}", response_model=ArtistWithRelations)
async def read_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    artist = service.read_artist(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return ArtistWithRelations.model_validate(artist).model_dump()

@router.put("/{artist_id}", response_model=Artist)
def update_artist(artist_id: int, artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    updated = service.update_artist(artist_id, artist)
    if not updated:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return Artist.model_validate(updated)

@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    success = service.delete_artist(artist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return {"ok": True}

# Artist Similar Endpoints
@router.get("/{artist_id}/similar", response_model=List[ArtistSimilarWithDetails])
async def get_similar_artists(
    artist_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Get similar artists for a specific artist.

    Args:
        artist_id: ID of the artist to find similar artists for
        limit: Maximum number of similar artists to return (1-50)

    Returns:
        List of similar artists with details
    """
    service = ArtistSimilarService(db)
    try:
        similar_artists = service.get_similar_artists_with_details(artist_id, limit)
        return similar_artists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{artist_id}/similar", response_model=ArtistSimilarWithDetails)
def create_similar_relationship(
    artist_id: int,
    similar_data: ArtistSimilarCreate,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Create a new artist similarity relationship.

    Args:
        artist_id: ID of the source artist
        similar_data: Data for the similar artist relationship

    Returns:
        Created similarity relationship with details
    """
    service = ArtistSimilarService(db)
    try:
        # Create the relationship
        relationship = service.create_similar_relationship(
            artist_id=artist_id,
            similar_artist_id=similar_data.similar_artist_id,
            weight=similar_data.weight,
            source=similar_data.source
        )

        # Return with artist names
        similar_with_details = service.get_similar_artists_with_details(artist_id, 1)
        if similar_with_details:
            return similar_with_details[0]

        # Fallback to basic relationship data
        return {
            "id": relationship.id,
            "artist_id": relationship.artist_id,
            "similar_artist_id": relationship.similar_artist_id,
            "weight": relationship.weight,
            "source": relationship.source,
            "created_at": relationship.date_added.isoformat() if relationship.date_added else None,
            "updated_at": relationship.date_modified.isoformat() if relationship.date_modified else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/similar/{relationship_id}", response_model=ArtistSimilarWithDetails)
def update_similar_relationship(
    relationship_id: int,
    update_data: ArtistSimilarUpdate,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Update an existing artist similarity relationship.

    Args:
        relationship_id: ID of the relationship to update
        update_data: Data to update

    Returns:
        Updated similarity relationship with details
    """
    service = ArtistSimilarService(db)
    try:
        # Update the relationship
        relationship = service.update_similar_relationship(
            relationship_id=relationship_id,
            weight=update_data.weight,
            source=update_data.source
        )

        # Get the artist ID from the relationship
        artist_id = relationship.artist_id

        # Return with artist names
        similar_with_details = service.get_similar_artists_with_details(artist_id, 1)
        if similar_with_details:
            return similar_with_details[0]

        # Fallback to basic relationship data
        return {
            "id": relationship.id,
            "artist_id": relationship.artist_id,
            "similar_artist_id": relationship.similar_artist_id,
            "weight": relationship.weight,
            "source": relationship.source,
            "created_at": relationship.date_added.isoformat() if relationship.date_added else None,
            "updated_at": relationship.date_modified.isoformat() if relationship.date_modified else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/similar/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_similar_relationship(
    relationship_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Delete an artist similarity relationship.

    Args:
        relationship_id: ID of the relationship to delete

    Returns:
        Empty response with 204 status on success
    """
    service = ArtistSimilarService(db)
    try:
        success = service.delete_similar_relationship(relationship_id)
        if not success:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/similar", response_model=ArtistSimilarListResponse)
def get_all_similar_relationships(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Get all artist similarity relationships with pagination.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        Paginated list of all similarity relationships
    """
    service = ArtistSimilarService(db)
    try:
        relationships, total_count = service.get_all_relationships_paginated(skip, limit)

        # Convert to detailed format
        detailed_relationships = []
        for rel in relationships:
            artist = service.db.query(ArtistModel).filter(ArtistModel.id == rel.artist_id).first()
            similar_artist = service.db.query(ArtistModel).filter(ArtistModel.id == rel.similar_artist_id).first()

            detailed_relationships.append({
                "id": rel.id,
                "artist_id": rel.artist_id,
                "artist_name": artist.name if artist else "Unknown",
                "similar_artist_id": rel.similar_artist_id,
                "similar_artist_name": similar_artist.name if similar_artist else "Unknown",
                "weight": rel.weight,
                "source": rel.source,
                "created_at": rel.date_added.isoformat() if rel.date_added else None,
                "updated_at": rel.date_modified.isoformat() if rel.date_modified else None
            })

        return {
            "count": total_count,
            "results": detailed_relationships
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{artist_id}/lastfm-info")
def fetch_artist_lastfm_info(
    artist_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Trigger Last.fm information fetch for an artist via worker.

    Args:
        artist_id: ID of the artist

    Returns:
        Task ID
    """
    from backend.api.utils.celery_app import celery_app
    try:
        # Trigger the worker task
        task = celery_app.send_task(
            'lastfm.fetch_artist_info',
            args=[artist_id],
            queue='deferred'
        )
        return {"task_id": task.id, "message": "Last.fm info fetch triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{artist_id}/lastfm-info")
def update_artist_lastfm_info(
    artist_id: int,
    info: dict,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Update artist with Last.fm information.

    Args:
        artist_id: ID of the artist
        info: Last.fm info dict

    Returns:
        Success message
    """
    from backend.api.models.artists_model import Artist
    import json
    from datetime import datetime

    try:
        artist = db.query(Artist).filter(Artist.id == artist_id).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        logger.info(f"[API] Updating Last.fm info for artist {artist_id} ({artist.name})")
        logger.debug(f"[API] Last.fm info data: {info}")

        # Update artist with Last.fm info
        artist.lastfm_url = info.get("url")
        artist.lastfm_listeners = info.get("listeners")
        artist.lastfm_playcount = info.get("playcount")
        artist.lastfm_tags = json.dumps(info.get("tags", [])) if info.get("tags") else None
        artist.lastfm_bio = info.get("bio")
        artist.lastfm_images = json.dumps(info.get("images", [])) if info.get("images") else None
        artist.lastfm_musicbrainz_id = info.get("musicbrainz_id")
        artist.lastfm_info_fetched_at = datetime.utcnow()

        db.commit()
        db.refresh(artist)
        
        logger.info(f"[API] Successfully updated Last.fm info for {artist.name}")
        logger.debug(f"[API] Updated fields - URL: {artist.lastfm_url}, Listeners: {artist.lastfm_listeners}, Playcount: {artist.lastfm_playcount}")
        
        return {"success": True, "message": f"Last.fm info updated for {artist.name}"}
    except Exception as e:
        db.rollback()
        logger.error(f"[API] Error updating Last.fm info for artist {artist_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{artist_id}/fetch-similar")
def fetch_similar_artists(
    artist_id: int,
    limit: int = 10,
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Trigger similar artists fetch from Last.fm for an artist via worker.

    Args:
        artist_id: ID of the artist
        limit: Maximum number of similar artists to fetch

    Returns:
        Task ID
    """
    from backend.api.utils.celery_app import celery_app
    try:
        # Trigger the worker task
        task = celery_app.send_task(
            'lastfm.fetch_similar_artists',
            args=[artist_id, limit],
            queue='deferred'
        )
        return {"task_id": task.id, "message": "Similar artists fetch triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{artist_id}/similar")
def update_artist_similar(
    artist_id: int,
    similar_data: List[dict],
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Update artist with similar artists data.

    Args:
        artist_id: ID of the artist
        similar_data: List of similar artists data

    Returns:
        Success message
    """
    from backend.api.models.artist_similar_model import ArtistSimilar
    from backend.api.models.artists_model import Artist
    from datetime import datetime

    try:
        # Mark that similar artists have been fetched
        artist = db.query(Artist).filter(Artist.id == artist_id).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        stored_count = 0
        for similar in similar_data:
            similar_name = similar.get("name")
            weight = similar.get("weight")

            # Find or create similar artist
            similar_artist = db.query(Artist).filter(Artist.name.ilike(similar_name)).first()
            if not similar_artist:
                similar_artist = Artist(
                    name=similar_name,
                    date_added=datetime.utcnow()
                )
                db.add(similar_artist)
                db.flush()

            # Check if relationship exists
            existing = db.query(ArtistSimilar).filter(
                ArtistSimilar.artist_id == artist_id,
                ArtistSimilar.similar_artist_id == similar_artist.id
            ).first()

            if existing:
                existing.weight = weight
            else:
                relation = ArtistSimilar(
                    artist_id=artist_id,
                    similar_artist_id=similar_artist.id,
                    weight=weight
                )
                db.add(relation)

            stored_count += 1

        artist.lastfm_similar_artists_fetched = True
        db.commit()
        return {"success": True, "message": f"Stored {stored_count} similar artists"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/similar/search", response_model=List[ArtistSimilarWithDetails])
def search_similar_artists_by_name(
    artist_name: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: SQLAlchemySession = Depends(get_db)
):
    """
    Search for similar artists by artist name.

    Args:
        artist_name: Name of the artist to find similar artists for
        limit: Maximum number of similar artists to return

    Returns:
        List of similar artists with details
    """
    service = ArtistSimilarService(db)
    try:
        return service.find_similar_artists_by_name(artist_name, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

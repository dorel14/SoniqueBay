from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from backend.api.schemas.pagination_schema import PaginatedArtists
from backend.api.schemas.artist_similar_schema import (
    ArtistSimilarCreate,
    ArtistSimilarUpdate,
    ArtistSimilarWithDetails,
    ArtistSimilarListResponse
)
from backend.api.utils.database import get_async_session
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from backend.api.schemas.tracks_schema import TrackWithRelations
from backend.api.services.artist_service import ArtistService
from backend.api.services.artist_similar_service import ArtistSimilarService
from backend.api.models.artists_model import Artist as ArtistModel
from backend.api.models.artist_similar_model import ArtistSimilar
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
    db: AsyncSession = Depends(get_async_session)
):
    service = ArtistService(db)
    artists = await service.search_artists(name, musicbrainz_artistid, genre, skip, limit)
    return [Artist.model_validate(a) for a in artists]


@router.post("/batch", response_model=List[Artist])
async def create_artists_batch(artists: List[ArtistCreate], db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    try:
        result = await service.bulk_create_artists(artists)
        return [Artist.model_validate(a) for a in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Artist)
async def create_artist(artist: ArtistCreate, db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    try:
        created = await service.create_artist(artist)
        return Artist.model_validate(created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


""" @router.get("/", response_model=PaginatedResponse[Artist])
async def read_artists(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)):
    artists = db.query(ArtistModel).order_by('name').offset(skip).limit(limit)
    return paginate_query(artists, skip, limit) """


@router.get("/count")
@cache(expire=300)  # Cache for 5 minutes
async def get_artists_count(db: AsyncSession = Depends(get_async_session)):
    """Get the total number of artists in the database."""
    service = ArtistService(db)
    count = await service.get_artists_count()
    return {"count": count}


@router.get("/", response_model=PaginatedArtists)
async def read_artists(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    artists, total_count = await service.get_artists_paginated(skip, limit)
    return {
        "count": total_count,
        "results": [Artist.model_validate(a) for a in artists]
    }


@router.get("/{artist_id}", response_model=ArtistWithRelations)
async def read_artist(artist_id: int, db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    artist = await service.read_artist(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return ArtistWithRelations.model_validate(artist).model_dump()


@router.put("/{artist_id}", response_model=Artist)
async def update_artist(artist_id: int, artist: ArtistCreate, db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    updated = await service.update_artist(artist_id, artist)
    if not updated:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return Artist.model_validate(updated)


@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artist(artist_id: int, db: AsyncSession = Depends(get_async_session)):
    service = ArtistService(db)
    success = await service.delete_artist(artist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return {"ok": True}


@router.get("/{artist_id}/tracks", response_model=List[TrackWithRelations])
async def read_artist_tracks(artist_id: int, db: AsyncSession = Depends(get_async_session)):
    """Récupère toutes les pistes d'un artiste."""
    from backend.api.services.track_service import TrackService
    from backend.api.schemas.tracks_schema import TrackWithRelations
    service = TrackService(db)
    tracks = await service.get_artist_tracks(artist_id)
    return [TrackWithRelations.model_validate(t).model_dump() for t in tracks]


# Artist Similar Endpoints
@router.get("/{artist_id}/similar", response_model=List[ArtistSimilarWithDetails])
async def get_similar_artists(
    artist_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session)
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
        similar_artists = await service.get_similar_artists_with_details(artist_id, limit)
        return similar_artists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{artist_id}/similar", response_model=ArtistSimilarWithDetails)
async def create_similar_relationship(
    artist_id: int,
    similar_data: ArtistSimilarCreate,
    db: AsyncSession = Depends(get_async_session)
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
        relationship = await service.create_similar_relationship(
            artist_id=artist_id,
            similar_artist_id=similar_data.similar_artist_id,
            weight=similar_data.weight,
            source=similar_data.source
        )

        # Return with artist names
        similar_with_details = await service.get_similar_artists_with_details(artist_id, 1)
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
async def update_similar_relationship(
    relationship_id: int,
    update_data: ArtistSimilarUpdate,
    db: AsyncSession = Depends(get_async_session)
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
        relationship = await service.update_similar_relationship(
            relationship_id=relationship_id,
            weight=update_data.weight,
            source=update_data.source
        )

        # Get the artist ID from the relationship
        artist_id = relationship.artist_id

        # Return with artist names
        similar_with_details = await service.get_similar_artists_with_details(artist_id, 1)
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
async def delete_similar_relationship(
    relationship_id: int,
    db: AsyncSession = Depends(get_async_session)
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
        success = await service.delete_similar_relationship(relationship_id)
        if not success:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar", response_model=ArtistSimilarListResponse)
async def get_all_similar_relationships(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session)
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
        relationships, total_count = await service.get_all_relationships_paginated(skip, limit)

        # Convert to detailed format
        detailed_relationships = []
        for rel in relationships:
            # Query artist and similar_artist using async SQLAlchemy
            artist_result = await db.execute(
                select(ArtistModel).where(ArtistModel.id == rel.artist_id)
            )
            artist = artist_result.scalar_one_or_none()

            similar_artist_result = await db.execute(
                select(ArtistModel).where(ArtistModel.id == rel.similar_artist_id)
            )
            similar_artist = similar_artist_result.scalar_one_or_none()

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
async def fetch_artist_lastfm_info(
    artist_id: int,
    db: AsyncSession = Depends(get_async_session)
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
async def update_artist_lastfm_info(
    artist_id: int,
    info: dict,
    db: AsyncSession = Depends(get_async_session)
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
        # Query artist using async SQLAlchemy
        result = await db.execute(select(Artist).where(Artist.id == artist_id))
        artist = result.scalar_one_or_none()

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

        await db.commit()
        await db.refresh(artist)

        logger.info(f"[API] Successfully updated Last.fm info for {artist.name}")
        logger.debug(
            f"[API] Updated fields - URL: {artist.lastfm_url}, "
            f"Listeners: {artist.lastfm_listeners}, Playcount: {artist.lastfm_playcount}"
        )

        return {"success": True, "message": f"Last.fm info updated for {artist.name}"}
    except Exception as e:
        await db.rollback()
        logger.error(f"[API] Error updating Last.fm info for artist {artist_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{artist_id}/fetch-similar")
async def fetch_similar_artists(
    artist_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session)
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
async def update_artist_similar(
    artist_id: int,
    similar_data: List[dict],
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update artist with similar artists data.

    Args:
        artist_id: ID of the artist
        similar_data: List of similar artists data

    Returns:
        Success message
    """
    from backend.api.models.artists_model import Artist
    from datetime import datetime

    try:
        # Mark that similar artists have been fetched
        result = await db.execute(select(Artist).where(Artist.id == artist_id))
        artist = result.scalar_one_or_none()

        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        stored_count = 0
        for similar in similar_data:
            similar_name = similar.get("name")
            weight = similar.get("weight")

            # Find or create similar artist
            similar_result = await db.execute(
                select(Artist).where(Artist.name.ilike(similar_name))
            )
            similar_artist = similar_result.scalar_one_or_none()

            if not similar_artist:
                similar_artist = Artist(
                    name=similar_name,
                    date_added=datetime.utcnow()
                )
                db.add(similar_artist)
                await db.flush()

            # Check if relationship exists
            existing_result = await db.execute(
                select(ArtistSimilar).where(
                    ArtistSimilar.artist_id == artist_id,
                    ArtistSimilar.similar_artist_id == similar_artist.id
                )
            )
            existing = existing_result.scalar_one_or_none()

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
        await db.commit()
        return {"success": True, "message": f"Stored {stored_count} similar artists"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/search", response_model=List[ArtistSimilarWithDetails])
async def search_similar_artists_by_name(
    artist_name: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session)
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
        return await service.find_similar_artists_by_name(artist_name, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

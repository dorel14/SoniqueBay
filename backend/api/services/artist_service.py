
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from typing import List, Optional
from datetime import datetime
from api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from api.models.artists_model import Artist as ArtistModel
from api.schemas.covers_schema import Cover, CoverType
from utils.logging import logger
from utils.session import transactional

class ArtistService:
    @transactional
    async def search_artists(
        self,
        session: SQLAlchemySession,
        name: Optional[str] = None,
        musicbrainz_artistid: Optional[str] = None,
        genre: Optional[str] = None
    ) -> List[Artist]:
        """Recherche des artistes par nom, genre ou ID MusicBrainz."""
        query = session.query(ArtistModel)

        if name:
            query = query.filter(func.lower(ArtistModel.name).like(f"%{name.lower()}%"))
        if musicbrainz_artistid:
            query = query.filter(ArtistModel.musicbrainz_artistid == musicbrainz_artistid)
        if genre:
            query = query.filter(func.lower(ArtistModel.genre).like(f"%{genre.lower()}%"))

        artists = query.all()
        return [Artist.model_validate(artist) for artist in artists]

    @transactional
    async def create_artists_batch(self, session: SQLAlchemySession, artists: List[ArtistCreate]) -> List[Artist]:
        try:
            artist_names = {a.name for a in artists if a.name}
            mbids = {a.musicbrainz_artistid for a in artists if a.musicbrainz_artistid}

            existing_artists_query = session.query(ArtistModel).filter(
                or_(
                    ArtistModel.name.in_(artist_names),
                    ArtistModel.musicbrainz_artistid.in_(mbids)
                )
            )
            existing_artists = existing_artists_query.all()

            existing_by_name = {a.name.lower(): a for a in existing_artists}
            existing_by_mbid = {a.musicbrainz_artistid: a for a in existing_artists if a.musicbrainz_artistid}

            new_artists_to_create = []
            final_artist_map = {}

            for artist_data in artists:
                artist_key = artist_data.musicbrainz_artistid or artist_data.name.lower()
                if artist_key in final_artist_map:
                    continue

                existing = None
                if artist_data.musicbrainz_artistid:
                    existing = existing_by_mbid.get(artist_data.musicbrainz_artistid)
                if not existing and artist_data.name:
                    existing = existing_by_name.get(artist_data.name.lower())

                if existing:
                    final_artist_map[artist_key] = existing
                else:
                    if artist_key not in [a.musicbrainz_artistid or a.name.lower() for a in new_artists_to_create]:
                        new_artists_to_create.append(artist_data)

            if new_artists_to_create:
                new_db_artists = [
                    ArtistModel(**artist.model_dump(exclude_unset=True), date_added=func.now(), date_modified=func.now())
                    for artist in new_artists_to_create
                ]
                session.add_all(new_db_artists)
                session.flush()
                for db_artist in new_db_artists:
                    key = db_artist.musicbrainz_artistid or db_artist.name.lower()
                    final_artist_map[key] = db_artist
            
            return list(final_artist_map.values())

        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la création en batch d'artistes: {e}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit de données lors de la création en batch.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la création en batch d'artistes: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    @transactional
    async def create_artist(self, session: SQLAlchemySession, artist: ArtistCreate) -> Artist:
        """Crée un nouvel artiste."""
        try:
            if artist.musicbrainz_artistid:
                existing = session.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
                ).first()
                if existing:
                    return existing

            existing_artist = session.query(ArtistModel).filter(
                func.lower(ArtistModel.name) == func.lower(artist.name)
            ).first()

            if existing_artist:
                return existing_artist

            db_artist = ArtistModel(
                **artist.model_dump(exclude_unset=True),
                date_added=func.now(),
                date_modified=func.now()
            )
            session.add(db_artist)
            session.flush()
            session.refresh(db_artist)
            return db_artist
        except IntegrityError as e:
            if "UNIQUE constraint failed: artists.musicbrainz_artistid" in str(e):
                existing = session.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
                ).first()
                if existing:
                    return existing
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un artiste avec cet identifiant existe déjà"
            )
    @transactional
    async def read_artists(session: SQLAlchemySession, skip: int = 0, limit: int = 100) -> List[dict]:
        try:
            artists = session.query(ArtistModel).offset(skip).limit(limit).all()
            if not artists:
                return []

            return [
                Artist.model_validate({
                    **artist.__dict__,
                    "date_added": artist.date_added or datetime.utcnow(),
                    "date_modified": artist.date_modified or datetime.utcnow()
                }).model_dump()
                for artist in artists
            ]
        except Exception as e:
            # Log and re-raise or handle
            raise RuntimeError(f"Erreur lors de la récupération des artistes: {str(e)}")

    @transactional
    async def read_artist(self, session: SQLAlchemySession, artist_id: int) -> ArtistWithRelations:
        try:
            artist = session.query(ArtistModel)\
                    .options(joinedload(ArtistModel.covers))\
                    .filter(ArtistModel.id == artist_id)\
                    .first()

            if not artist:
                raise HTTPException(status_code=404, detail=f"Artiste {artist_id} non trouvé")

            logger.debug(f"Covers trouvées pour l'artiste {artist_id}: {artist.covers}")

            artist_covers = []
            if hasattr(artist, 'covers') and artist.covers:
                for cover in artist.covers:
                    try:
                        cover_data = {
                            "id": cover.id,
                            "entity_type": CoverType.ARTIST,
                            "entity_id": artist.id,
                            "url": cover.url,
                            "cover_data": cover.cover_data,
                            "created_at": cover.date_added,
                            "updated_at": cover.date_modified
                        }
                        artist_covers.append(Cover(**cover_data))
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement de la cover {cover.id}: {str(e)}")
                        continue

            response_data = {
                "id": artist.id,
                "name": artist.name,
                "musicbrainz_artistid": artist.musicbrainz_artistid,
                "date_added": artist.date_added,
                "date_modified": artist.date_modified,
                "covers": artist_covers
            }
            
            logger.debug(f"Réponse pour l'artiste {artist_id}: {response_data}")
            
            return response_data

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'artiste {artist_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la récupération de l'artiste: {str(e)}"
            )

    @transactional
    async def update_artist(self, session: SQLAlchemySession, artist_id: int, artist: ArtistCreate) -> Artist:
        db_artist = session.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
        if db_artist is None:
            raise HTTPException(status_code=404, detail="Artiste non trouvé")
        
        for key, value in artist.model_dump(exclude_unset=True).items():
            setattr(db_artist, key, value)
        db_artist.date_modified = func.now()
        
        session.flush()
        session.refresh(db_artist)
        return db_artist

    @transactional
    async def delete_artist(self, session: SQLAlchemySession, artist_id: int):
        artist = session.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
        if artist is None:
            raise HTTPException(status_code=404, detail="Artiste non trouvé")
        
        session.delete(artist)
        return {"ok": True}
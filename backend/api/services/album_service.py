from fastapi import HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession
from api.schemas.albums_schema import AlbumCreate, Album, AlbumWithRelations
from api.models.albums_model import Album as AlbumModel
from api.schemas.covers_schema import Cover, CoverType
from sqlalchemy import func, or_
from datetime import datetime
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from utils.logging import logger
from sqlalchemy.orm import joinedload
from utils.session import transactional

class AlbumService:
    @transactional
    async def search_albums(
        self,
        session: SQLAlchemySession,
        title: Optional[str] = None,
        artist_id: Optional[int] = None,
        musicbrainz_albumid: Optional[str] = None,
        musicbrainz_albumartistid: Optional[str] = None
    ) -> List[Album]:
        query = session.query(AlbumModel)

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

    @transactional
    async def create_albums_batch(self, session: SQLAlchemySession, albums: List[AlbumCreate]) -> List[AlbumWithRelations]:
        try:
            keys_to_find = set()
            mbids_to_find = set()
            for album_data in albums:
                if album_data.musicbrainz_albumid:
                    mbids_to_find.add(album_data.musicbrainz_albumid)
                elif album_data.title and album_data.album_artist_id:
                    keys_to_find.add((album_data.title.lower(), album_data.album_artist_id))

            existing_albums_query = session.query(AlbumModel)
            if mbids_to_find:
                existing_albums_query = existing_albums_query.filter(AlbumModel.musicbrainz_albumid.in_(mbids_to_find))
            
            if keys_to_find:
                or_conditions = []
                for title, artist_id in keys_to_find:
                    or_conditions.append(
                        (func.lower(AlbumModel.title) == title) & (AlbumModel.album_artist_id == artist_id)
                    )
                existing_albums_query = existing_albums_query.filter(or_(*or_conditions))

            existing_albums = existing_albums_query.options(joinedload(AlbumModel.covers)).all()

            existing_by_mbid = {a.musicbrainz_albumid: a for a in existing_albums if a.musicbrainz_albumid}
            existing_by_key = {(a.title.lower(), a.album_artist_id): a for a in existing_albums}

            new_albums_to_create = []
            final_album_map = {}

            for album_data in albums:
                key = album_data.musicbrainz_albumid or (album_data.title.lower(), album_data.album_artist_id)
                if key in final_album_map:
                    continue

                existing = None
                if album_data.musicbrainz_albumid:
                    existing = existing_by_mbid.get(album_data.musicbrainz_albumid)
                if not existing and album_data.title and album_data.album_artist_id:
                    existing = existing_by_key.get((album_data.title.lower(), album_data.album_artist_id))

                if existing:
                    final_album_map[key] = existing
                else:
                    if key not in [a.musicbrainz_albumid or (a.title.lower(), a.album_artist_id) for a in new_albums_to_create]:
                        new_albums_to_create.append(album_data)

            if new_albums_to_create:
                new_db_albums = [
                    AlbumModel(**album.model_dump(exclude_unset=True), date_added=func.now(), date_modified=func.now())
                    for album in new_albums_to_create
                ]
                session.add_all(new_db_albums)
                session.flush() # Use flush instead of commit here to get IDs for refresh
                for db_album in new_db_albums:
                    session.refresh(db_album, ["covers"])
                    key = db_album.musicbrainz_albumid or (db_album.title.lower(), db_album.album_artist_id)
                    final_album_map[key] = db_album

            result = []
            for album_in in albums:
                key = album_in.musicbrainz_albumid or (album_in.title.lower(), album_in.album_artist_id)
                album = final_album_map[key]
                covers = []
                if hasattr(album, "covers"):
                    covers = [Cover.model_validate(c) for c in album.covers]
                album_data = {
                    **album.__dict__,
                    "covers": covers,
                    "date_added": album.date_added or datetime.utcnow(),
                    "date_modified": album.date_modified or datetime.utcnow(),
                }
                result.append(AlbumWithRelations.model_validate(album_data).model_dump())
            return result

        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la création en batch d'albums: {e}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit de données lors de la création en batch.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la création en batch d'albums: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

    @transactional
    async def create_album(self, session: SQLAlchemySession, album: AlbumCreate) -> Album:
        try:
            if album.musicbrainz_albumid:
                existing_album = session.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
                ).first()
                if existing_album:
                    return Album.model_validate(existing_album)

            existing_album = session.query(AlbumModel).filter(
                AlbumModel.title == album.title,
                AlbumModel.album_artist_id == album.album_artist_id
            ).first()
            if existing_album:
                return Album.model_validate(existing_album)

            db_album = AlbumModel(
                **album.model_dump(exclude={"date_added", "date_modified"}),
                date_added=func.now(),
                date_modified=func.now()
            )
            session.add(db_album)
            session.flush()
            session.refresh(db_album)
            return Album.model_validate(db_album)

        except IntegrityError as e:
            if "UNIQUE constraint failed: albums.musicbrainz_albumid" in str(e):
                existing = session.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
                ).first()
                if existing:
                    return Album.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un album avec cet identifiant existe déjà"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @transactional
    async def read_albums(self, session: SQLAlchemySession, skip: int = 0, limit: int = 100) -> List[AlbumWithRelations]:
        albums = session.query(AlbumModel).offset(skip).limit(limit).all()
        return [AlbumWithRelations.model_validate(
            {**album.__dict__,
             "date_added": album.date_added or datetime.utcnow(),
             "date_modified": album.date_modified or datetime.utcnow()
            }
        ).model_dump() for album in albums]

    @transactional
    async def read_album(self, session: SQLAlchemySession, album_id: int) -> AlbumWithRelations:
        try:
            album = session.query(AlbumModel) \
                .options(joinedload(AlbumModel.covers)) \
                .filter(AlbumModel.id == album_id).first()
            if not album:
                raise HTTPException(status_code=404, detail="Album non trouvé")
            logger.debug(f"Covers trouvées pour l'album {album_id}: {album.covers}")

            album_covers = []
            if hasattr(album, 'covers') and album.covers:
                for cover in album.covers:
                    try:
                        cover_data = {
                            "id": cover.id,
                            "entity_type": CoverType.ALBUM,
                            "entity_id": album.id,
                            "url": cover.url,
                            "cover_data": cover.cover_data,
                            "date_added": cover.date_added,
                            "date_modified": cover.date_modified,
                            "mime_type": cover.mime_type
                        }
                        album_covers.append(Cover(**cover_data))
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement de la cover {cover.id}: {str(e)}")
                        continue

            album_data = {
                **album.__dict__,
                "covers": album_covers,
                "cover_url": album_covers[0].url if album_covers else None,
                "date_added": album.date_added or datetime.utcnow(),
                "date_modified": album.date_modified or datetime.utcnow(),
            }

            return AlbumWithRelations.model_validate(album_data).model_dump()

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des albums: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la récupération des albums"
            )

    @transactional
    async def update_album(self, session: SQLAlchemySession, album_id: int, album: AlbumCreate) -> Album:
        db_album = session.query(AlbumModel).filter(AlbumModel.id == album_id).first()
        if db_album is None:
            raise HTTPException(status_code=404, detail="Album non trouvé")

        for key, value in album.model_dump(exclude_unset=True).items():
            setattr(db_album, key, value)

        session.flush()
        session.refresh(db_album)
        return db_album

    @transactional
    async def delete_album(self, session: SQLAlchemySession, album_id: int):
        album = session.query(AlbumModel).filter(AlbumModel.id == album_id).first()
        if album is None:
            raise HTTPException(status_code=404, detail="Album non trouvé")

        session.delete(album)
        return {"ok": True}

    @transactional
    async def get_albums_by_artist_id(self, session: SQLAlchemySession, artist_id: int) -> List[AlbumWithRelations]:
        albums = session.query(AlbumModel).filter(AlbumModel.album_artist_id == artist_id).all()
        return [AlbumWithRelations.model_validate(
            {**album.__dict__,
             "date_added": album.date_added or datetime.utcnow(),
             "date_modified": album.date_modified or datetime.utcnow()
            }
        ).model_dump() for album in albums]
from backend.api.models.albums_model import Album as AlbumModel
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.schemas.covers_schema import Cover
from backend.api.schemas.albums_schema import AlbumCreate, AlbumUpdate, AlbumWithRelations
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

class AlbumService:
    def __init__(self, db):
        self.db = db

    def search_albums(self, title, artist_id, musicbrainz_albumid, musicbrainz_albumartistid):
        query = self.db.query(AlbumModel)
        if title:
            query = query.filter(func.lower(AlbumModel.title).like(f"%{title.lower()}%"))
        if artist_id:
            query = query.filter(AlbumModel.album_artist_id == artist_id)
        if musicbrainz_albumid:
            query = query.filter(AlbumModel.musicbrainz_albumid == musicbrainz_albumid)
        if musicbrainz_albumartistid:
            query = query.filter(AlbumModel.musicbrainz_albumartistid == musicbrainz_albumartistid)
        return query.all()

    def create_albums_batch(self, albums):
        """Crée ou récupère plusieurs albums en une seule fois (batch)."""
        try:
            keys_to_find = set()
            mbids_to_find = set()
            for album_data in albums:
                if album_data.musicbrainz_albumid:
                    mbids_to_find.add(album_data.musicbrainz_albumid)
                elif album_data.title and album_data.album_artist_id:
                    keys_to_find.add((album_data.title.lower(), album_data.album_artist_id))

            existing_albums_query = self.db.query(AlbumModel)
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
                self.db.add_all(new_db_albums)
                self.db.commit()
                for db_album in new_db_albums:
                    self.db.refresh(db_album, ["covers"])
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
                    "date_added": album.date_added or datetime.now(timezone.utc),
                    "date_modified": album.date_modified or datetime.now(timezone.utc),
                }
                result.append(AlbumWithRelations.model_validate(album_data).model_dump())
            return result

        except IntegrityError:
            self.db.rollback()
            raise Exception("Conflit de données lors de la création en batch.")
        except Exception:
            self.db.rollback()
            raise Exception("Erreur interne du serveur.")

    def create_album(self, album_data: AlbumCreate):
        """Crée un album ou retourne l'existant (doublon MBID ou titre+artiste)."""
        try:
            if album_data.musicbrainz_albumid:
                existing_album = self.db.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album_data.musicbrainz_albumid
                ).first()
                if existing_album:
                    return existing_album

            existing_album = self.db.query(AlbumModel).filter(
                AlbumModel.title == album_data.title,
                AlbumModel.album_artist_id == album_data.album_artist_id
            ).first()
            if existing_album:
                return existing_album

            db_album = AlbumModel(
                **album_data.model_dump(exclude={"date_added", "date_modified"}),
                date_added=func.now(),
                date_modified=func.now()
            )
            self.db.add(db_album)
            self.db.commit()
            self.db.refresh(db_album)
            return db_album

        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed: albums.musicbrainz_albumid" in str(e):
                existing = self.db.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album_data.musicbrainz_albumid
                ).first()
                if existing:
                    return existing
            raise Exception("Un album avec cet identifiant existe déjà")
        except Exception as e:
            self.db.rollback()
            raise Exception(str(e))

    def read_albums(self, skip=0, limit=100):
        albums = self.db.query(AlbumModel).offset(skip).limit(limit).all()
        # Precompute current time for missing dates to avoid repeated system calls
        now = datetime.now(timezone.utc)
        results = []
        append = results.append
        for album in albums:
            date_added = album.date_added if album.date_added is not None else now
            date_modified = album.date_modified if album.date_modified is not None else now
            # Build dict directly rather than using {**album.__dict__, ...} for memory and perf
            d = album.__dict__.copy()
            d.update({
                "covers": [],
                "cover_url": None,
                "date_added": date_added,
                "date_modified": date_modified,
            })
            append(d)
        return results

    def read_album(self, album_id):
        album = self.db.query(AlbumModel).options(joinedload(AlbumModel.covers)).filter(AlbumModel.id == album_id).first()
        if not album:
            return None
        album_covers = []
        if hasattr(album, 'covers') and album.covers:
            for cover in album.covers:
                cover_data = {
                    "id": cover.id,
                    "entity_type": "album",
                    "entity_id": album.id,
                    "url": cover.url,
                    "cover_data": cover.cover_data,
                    "date_added": cover.date_added,
                    "date_modified": cover.date_modified,
                    "mime_type": cover.mime_type
                }
                album_covers.append(Cover(**cover_data))
        album_data = {
            **album.__dict__,
            "covers": album_covers,
            "cover_url": album_covers[0].url if album_covers else None,
            "date_added": album.date_added or datetime.now(timezone.utc),
            "date_modified": album.date_modified or datetime.now(timezone.utc),
        }
        return album_data

    def read_artist_albums(self, artist_id):
        albums = self.db.query(AlbumModel).options(joinedload(AlbumModel.covers)).filter(AlbumModel.album_artist_id == artist_id).all()
        return [
            {
                **album.__dict__,
                "covers": [Cover.model_validate(c) for c in album.covers],
                "date_added": album.date_added or datetime.now(timezone.utc),
                "date_modified": album.date_modified or datetime.now(timezone.utc)
            }
            for album in albums
        ]

    def update_album(self, album_id, album_update: AlbumUpdate):
        db_album = self.db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
        if db_album is None:
            return None
        update_data = album_update.model_dump(exclude_unset=True, exclude={"date_added", "date_modified"})
        for key, value in update_data.items():
            if hasattr(db_album, key):
                setattr(db_album, key, value)
        db_album.date_modified = func.now()
        self.db.commit()
        self.db.refresh(db_album)
        return db_album

    def read_album_tracks(self, album_id):
        tracks = self.db.query(TrackModel).filter(TrackModel.album_id == album_id).all()
        return [
            {
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
            for track in tracks
        ]

    def delete_album(self, album_id):
        album = self.db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
        if album is None:
            return False
        self.db.delete(album)
        self.db.commit()
        return True

    def upsert_album(self, album_data):
        """Upsert an album (create if not exists, update if exists)."""
        try:
            # Try to find existing album by musicbrainz_albumid first
            existing_album = None
            if hasattr(album_data, 'musicbrainz_albumid') and album_data.musicbrainz_albumid:
                existing_album = self.db.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album_data.musicbrainz_albumid
                ).first()

            # If not found by MBID, try by title and artist
            if not existing_album and hasattr(album_data, 'title') and hasattr(album_data, 'album_artist_id'):
                existing_album = self.db.query(AlbumModel).filter(
                    AlbumModel.title == album_data.title,
                    AlbumModel.album_artist_id == album_data.album_artist_id
                ).first()

            if existing_album:
                # Update existing album
                # Handle both Pydantic models and Strawberry objects
                if hasattr(album_data, 'model_dump'):
                    update_dict = album_data.model_dump(exclude_unset=True, exclude_none=True)
                else:
                    # Strawberry object - convert manually
                    update_dict = {}
                    for attr in ['title', 'album_artist_id', 'release_year', 'musicbrainz_albumid']:
                        if hasattr(album_data, attr):
                            value = getattr(album_data, attr)
                            if value is not None:
                                update_dict[attr] = value

                for key, value in update_dict.items():
                    if hasattr(existing_album, key) and value is not None:
                        setattr(existing_album, key, value)
                existing_album.date_modified = func.now()
                self.db.commit()
                self.db.refresh(existing_album)
                return existing_album
            else:
                # Create new album
                # Handle both Pydantic models and Strawberry objects
                if hasattr(album_data, 'model_dump'):
                    album_dict = album_data.model_dump(exclude_unset=True)
                else:
                    # Strawberry object - convert manually
                    album_dict = {}
                    for attr in ['title', 'album_artist_id', 'release_year', 'musicbrainz_albumid']:
                        if hasattr(album_data, attr):
                            value = getattr(album_data, attr)
                            album_dict[attr] = value

                db_album = AlbumModel(
                    **album_dict,
                    date_added=func.now(),
                    date_modified=func.now()
                )
                self.db.add(db_album)
                self.db.commit()
                self.db.refresh(db_album)
                return db_album

        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed: albums.musicbrainz_albumid" in str(e):
                existing = self.db.query(AlbumModel).filter(
                    AlbumModel.musicbrainz_albumid == album_data.musicbrainz_albumid
                ).first()
                if existing:
                    return existing
            raise Exception("Erreur lors de l'upsert de l'album")
        except Exception as e:
            self.db.rollback()
            raise Exception(str(e))

    def update_albums_by_filter(self, filter_data, update_data):
        """Update multiple albums by filter."""
        try:
            query = self.db.query(AlbumModel)

            # Apply filters
            if 'title' in filter_data:
                if 'icontains' in filter_data['title']:
                    query = query.filter(
                        func.lower(AlbumModel.title).like(f"%{filter_data['title']['icontains'].lower()}%")
                    )
                elif isinstance(filter_data['title'], str):
                    query = query.filter(AlbumModel.title == filter_data['title'])

            if 'musicbrainz_albumid' in filter_data:
                query = query.filter(AlbumModel.musicbrainz_albumid == filter_data['musicbrainz_albumid'])

            # Get albums to update
            albums_to_update = query.all()

            if not albums_to_update:
                return []

            # Update each album
            updated_albums = []
            for album in albums_to_update:
                for key, value in update_data.items():
                    if hasattr(album, key) and value is not None:
                        setattr(album, key, value)
                album.date_modified = func.now()
                updated_albums.append(album)

            self.db.commit()

            # Refresh all updated albums
            for album in updated_albums:
                self.db.refresh(album)

            return updated_albums

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erreur lors de la mise à jour par filtre: {str(e)}")

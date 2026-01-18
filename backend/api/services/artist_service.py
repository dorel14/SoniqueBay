from sqlalchemy import func, or_
from backend.api.models.artists_model import Artist as ArtistModel
from sqlalchemy.exc import IntegrityError

class ArtistService:
    def __init__(self, db):
        self.db = db

    def search_artists(self, name=None, musicbrainz_artistid=None, genre=None, skip=0, limit=None):
        query = self.db.query(ArtistModel)
        if name:
            query = query.filter(func.lower(ArtistModel.name).like(f"%{name.lower()}%"))
        if musicbrainz_artistid:
            query = query.filter(ArtistModel.musicbrainz_artistid == musicbrainz_artistid)
        if genre:
            query = query.filter(func.lower(ArtistModel.genre).like(f"%{genre.lower()}%"))

        # Appliquer la pagination
        if limit is not None:
            query = query.offset(skip).limit(limit)

        artists = query.all()

        return artists

    def create_artists_batch(self, artists):
        artist_names = {a.name for a in artists if a.name}
        mbids = {a.musicbrainz_artistid for a in artists if a.musicbrainz_artistid}
        existing_artists_query = self.db.query(ArtistModel).filter(
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
                ArtistModel(**artist.model_dump())
                for artist in new_artists_to_create
            ]
            self.db.add_all(new_db_artists)
            self.db.commit()
            for db_artist in new_db_artists:
                key = db_artist.musicbrainz_artistid or db_artist.name.lower()
                final_artist_map[key] = db_artist
        return list(final_artist_map.values())

    def create_artist(self, artist):
        try:
            if artist.musicbrainz_artistid:
                existing = self.db.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
                ).first()
                if existing:
                    return existing
            existing_artist = self.db.query(ArtistModel).filter(
                func.lower(ArtistModel.name) == func.lower(artist.name)
            ).first()
            if existing_artist:
                return existing_artist
            db_artist = ArtistModel(
                **artist.model_dump()
            )
            self.db.add(db_artist)
            self.db.commit()
            self.db.refresh(db_artist)
            return db_artist
        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed: artists.musicbrainz_artistid" in str(e):
                existing = self.db.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
                ).first()
                if existing:
                    return existing
            raise Exception("Un artiste avec cet identifiant existe déjà")
        except Exception as e:
            self.db.rollback()
            raise Exception(str(e))

    def get_artists_paginated(self, skip=0, limit=100):
        query = self.db.query(ArtistModel)
        total_count = query.count()
        artists = query.order_by(ArtistModel.name).offset(skip).limit(limit).all()
        return artists, total_count

    def get_artists_count(self):
        """Get the total number of artists in the database."""
        return self.db.query(ArtistModel).count()

    def read_artist(self, artist_id):
        artist = self.db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
        if not artist:
            return None
        # covers, etc. à enrichir si besoin
        return artist

    def update_artist(self, artist_id, artist_update):
        db_artist = self.db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
        if db_artist is None:
            return None
        update_data = artist_update.model_dump()
        for key, value in update_data.items():
            if hasattr(db_artist, key) and value is not None:
                setattr(db_artist, key, value)
        db_artist.date_modified = func.now()
        self.db.commit()
        self.db.refresh(db_artist)
        return db_artist

    def delete_artist(self, artist_id):
        artist = self.db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
        if artist is None:
            return False
        self.db.delete(artist)
        self.db.commit()
        return True

    def upsert_artist(self, artist_data):
        """Upsert an artist (create if not exists, update if exists)."""
        try:
            # Try to find existing artist by musicbrainz_artistid first
            existing_artist = None
            if hasattr(artist_data, 'musicbrainz_artistid') and artist_data.musicbrainz_artistid:
                existing_artist = self.db.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist_data.musicbrainz_artistid
                ).first()

            # If not found by MBID, try by name
            if not existing_artist and hasattr(artist_data, 'name') and artist_data.name:
                existing_artist = self.db.query(ArtistModel).filter(
                    func.lower(ArtistModel.name) == func.lower(artist_data.name)
                ).first()

            if existing_artist:
                # Update existing artist
                update_dict = artist_data.model_dump()
                for key, value in update_dict.items():
                    if hasattr(existing_artist, key) and value is not None:
                        setattr(existing_artist, key, value)
                existing_artist.date_modified = func.now()
                self.db.commit()
                self.db.refresh(existing_artist)
                return existing_artist
            else:
                # Create new artist
                db_artist = ArtistModel(
                    **artist_data.model_dump()
                )
                self.db.add(db_artist)
                self.db.commit()
                self.db.refresh(db_artist)
                return db_artist

        except IntegrityError as e:
            self.db.rollback()
            if "UNIQUE constraint failed: artists.musicbrainz_artistid" in str(e):
                existing = self.db.query(ArtistModel).filter(
                    ArtistModel.musicbrainz_artistid == artist_data.musicbrainz_artistid
                ).first()
                if existing:
                    return existing
            raise Exception("Erreur lors de l'upsert de l'artiste")
        except Exception as e:
            self.db.rollback()
            raise Exception(str(e))

    def update_artists_by_filter(self, filter_data, update_data):
        """Update multiple artists by filter."""
        try:
            query = self.db.query(ArtistModel)

            # Apply filters
            if 'name' in filter_data:
                if 'icontains' in filter_data['name']:
                    query = query.filter(
                        func.lower(ArtistModel.name).like(f"%{filter_data['name']['icontains'].lower()}%")
                    )
                elif isinstance(filter_data['name'], str):
                    query = query.filter(ArtistModel.name == filter_data['name'])

            if 'musicbrainz_artistid' in filter_data:
                query = query.filter(ArtistModel.musicbrainz_artistid == filter_data['musicbrainz_artistid'])

            # Get artists to update
            artists_to_update = query.all()

            if not artists_to_update:
                return []

            # Update each artist
            updated_artists = []
            for artist in artists_to_update:
                for key, value in update_data.items():
                    if hasattr(artist, key) and value is not None:
                        setattr(artist, key, value)
                artist.date_modified = func.now()
                updated_artists.append(artist)

            self.db.commit()

            # Refresh all updated artists
            for artist in updated_artists:
                self.db.refresh(artist)

            return updated_artists

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Erreur lors de la mise à jour par filtre: {str(e)}")

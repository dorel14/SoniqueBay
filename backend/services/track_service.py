from sqlalchemy.orm import joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.models.genres_model import Genre
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.api.schemas.tracks_schema import TrackCreate
from backend.utils.logging import logger
from typing import List, Optional

class TrackService:
    """
    Service métier pour la gestion des pistes musicales.

    Ce service fournit toutes les opérations CRUD pour les tracks,
    ainsi que les fonctionnalités de recherche et de mise à jour.

    Auteur : Kilo Code
    Dépendances : backend.api.models.tracks_model, backend.utils.database
    """

    def get_artist_tracks(self, artist_id: int, album_id: Optional[int] = None):
        """
        Retourne les pistes d'un artiste, optionnellement filtrées par album.

        Args:
            artist_id: ID de l'artiste
            album_id: ID de l'album (optionnel)

        Returns:
            Liste des pistes de l'artiste
        """
        query = self.session.query(TrackModel).filter(TrackModel.track_artist_id == artist_id)
        if album_id:
            query = query.filter(TrackModel.album_id == album_id)
        query = query.options(
            joinedload(TrackModel.genre_tags),
            joinedload(TrackModel.mood_tags),
            joinedload(TrackModel.album),
            joinedload(TrackModel.genres),
            joinedload(TrackModel.covers)
        )
        return query.all()
    def __init__(self, session):
        """
        Initialise le service avec une session de base de données.

        Args:
            session: Session SQLAlchemy
        """
        self.session = session

    def create_track(self, data: TrackCreate):
        """
        Crée une nouvelle piste dans la base de données.

        Args:
            data: Données de la piste à créer

        Returns:
            La piste créée

        Raises:
            IntegrityError: En cas de violation de contrainte
        """
        track = TrackModel(
            title=data.title,
            path=data.path,
            track_artist_id=data.track_artist_id,
            album_id=data.album_id,
            genre=data.genre,
            bpm=data.bpm,
            key=data.key,
            scale=data.scale,
            duration=data.duration,
            track_number=data.track_number,
            disc_number=data.disc_number,
            musicbrainz_id=data.musicbrainz_id,
            year=data.year,
            featured_artists=data.featured_artists,
            file_type=data.file_type,
            bitrate=data.bitrate
        )
        self.session.add(track)
        self.session.commit()
        self.session.refresh(track)
        return track

    def create_or_update_tracks_batch(self, tracks_data: List[TrackCreate]):
        result = []
        for data in tracks_data:
            existing = self.session.query(TrackModel).filter(TrackModel.path == data.path).first()
            if existing:
                # Check if file has changed
                if hasattr(data, 'file_mtime') and hasattr(data, 'file_size'):
                    if (existing.file_mtime == data.file_mtime and
                        existing.file_size == data.file_size):
                        # File unchanged, skip update
                        result.append(existing)
                        continue

                # Update existing track
                update_data = data.model_dump(exclude_unset=True, exclude_none=True)
                for field, value in update_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.date_modified = func.now()
                self.session.commit()
                self.session.refresh(existing)
                result.append(existing)
            else:
                created = self.create_track(data)
                result.append(created)
        return result

    def search_tracks(self,
        title: Optional[str], artist: Optional[str], album: Optional[str], genre: Optional[str], year: Optional[str],
        path: Optional[str], musicbrainz_id: Optional[str], genre_tags: Optional[List[str]], mood_tags: Optional[List[str]]
    ):
        query = self.session.query(TrackModel)
        if title:
            query = query.filter(TrackModel.title.ilike(f"%{title}%"))
        if artist:
            query = query.join(TrackModel.artist).filter_by(name=artist)
        if album:
            query = query.join(TrackModel.album).filter_by(title=album)
        if genre:
            query = query.filter(TrackModel.genre.ilike(f"%{genre}%"))
        if year:
            query = query.filter(TrackModel.year == year)
        if path:
            query = query.filter(TrackModel.path == path)
        if musicbrainz_id:
            query = query.filter(TrackModel.musicbrainz_id == musicbrainz_id)
        if genre_tags:
            query = query.join(TrackModel.genre_tags).filter(GenreTag.name.in_(genre_tags))
        if mood_tags:
            query = query.join(TrackModel.mood_tags).filter(MoodTag.name.in_(mood_tags))
        
        options = []
        if genre_tags:
            options.append(joinedload(TrackModel.genre_tags))
        if mood_tags:
            options.append(joinedload(TrackModel.mood_tags))
        options.extend([
            joinedload(TrackModel.album),
            joinedload(TrackModel.genres),
            joinedload(TrackModel.covers)
        ])
        query = query.options(*options)
        return query.all()

    def read_tracks(self, skip: int = 0, limit: int = 100):
        tracks = (
            self.session.query(TrackModel)
            .options(
                joinedload(TrackModel.genre_tags),
                joinedload(TrackModel.mood_tags),
                joinedload(TrackModel.album),
                joinedload(TrackModel.genres),
                joinedload(TrackModel.covers)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return tracks

    def read_track(self, track_id: int):
        track = (
            self.session.query(TrackModel)
            .options(
                joinedload(TrackModel.genre_tags),
                joinedload(TrackModel.mood_tags),
                joinedload(TrackModel.covers),
                joinedload(TrackModel.album),
                joinedload(TrackModel.genres)
            )
            .filter(TrackModel.id == track_id)
            .first()
        )
        return track

    def update_track(self, track_id: int, track_data):
        from sqlalchemy import func

        db_track = self.session.query(TrackModel).filter(TrackModel.id == track_id).first()
        if not db_track:
            return None

        # Extraire et nettoyer les données
        if hasattr(track_data, 'model_dump'):
            # C'est un objet Pydantic
            data = track_data.model_dump(
                exclude={'genre_tags', 'mood_tags', 'genres', 'date_added', 'date_modified'},
                exclude_unset=True,
                exclude_none=True
            )
        else:
            # C'est un dictionnaire
            data = {k: v for k, v in track_data.items()
                   if k not in {'genre_tags', 'mood_tags', 'genres', 'date_added', 'date_modified'} and v is not None}

        # Mise à jour des attributs simples
        for key, value in data.items():
            if hasattr(db_track, key) and not isinstance(value, (dict, list)):
                setattr(db_track, key, value)

        # Mise à jour des genres
        if hasattr(track_data, 'genres') and isinstance(track_data.genres, list):
            genres = []
            for genre_id in track_data.genres:
                genre = self.session.query(Genre).get(genre_id)
                if genre:
                    genres.append(genre)
            db_track.genres = genres

        # Mise à jour des tags
        if hasattr(track_data, 'genre_tags'):
            self.update_track_tags(track_id, genre_tags=track_data.genre_tags)
        if hasattr(track_data, 'mood_tags'):
            self.update_track_tags(track_id, mood_tags=track_data.mood_tags)

        # Mise à jour de la date de modification
        db_track.date_modified = func.now()

        # Commit et refresh
        try:
            self.session.commit()
            self.session.refresh(db_track)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Erreur lors du commit update_track: {str(e)}")
            raise

        return db_track

    def update_track_tags(self, track_id: int, genre_tags: Optional[List[str]] = None, mood_tags: Optional[List[str]] = None):
        from sqlalchemy import func

        db_track = self.session.query(TrackModel).filter(TrackModel.id == track_id).first()
        if not db_track:
            return None

        try:
            # Mise à jour des genre tags
            if genre_tags is not None:
                db_track.genre_tags = []
                for tag_name in genre_tags:
                    tag = self.session.query(GenreTag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = GenreTag(name=tag_name)
                        self.session.add(tag)
                    db_track.genre_tags.append(tag)

            # Mise à jour des mood tags
            if mood_tags is not None:
                db_track.mood_tags = []
                for tag_name in mood_tags:
                    tag = self.session.query(MoodTag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = MoodTag(name=tag_name)
                        self.session.add(tag)
                    db_track.mood_tags.append(tag)

            db_track.date_modified = func.now()
            self.session.commit()
            self.session.refresh(db_track)
            return db_track

        except Exception as e:
            self.session.rollback()
            logger.error(f"Erreur mise à jour tags: {str(e)}")
            raise

    def delete_track(self, track_id: int):
        track = self.session.query(TrackModel).filter(TrackModel.id == track_id).first()
        if not track:
            return False

        self.session.delete(track)
        self.session.commit()
        return True

    def upsert_track(self, track_data):
        """Upsert a track (create if not exists, update if exists)."""
        try:
            # Try to find existing track by musicbrainz_id first
            existing_track = None
            if hasattr(track_data, 'musicbrainz_id') and track_data.musicbrainz_id:
                existing_track = self.session.query(TrackModel).filter(
                    TrackModel.musicbrainz_id == track_data.musicbrainz_id
                ).first()

            # If not found by MBID, try by path
            if not existing_track and hasattr(track_data, 'path') and track_data.path:
                existing_track = self.session.query(TrackModel).filter(
                    TrackModel.path == track_data.path
                ).first()

            if existing_track:
                # Update existing track
                # Handle both Pydantic models and Strawberry objects
                if hasattr(track_data, 'model_dump'):
                    update_data = track_data.model_dump(
                        exclude={'genre_tags', 'mood_tags', 'genres', 'date_added', 'date_modified'},
                        exclude_unset=True,
                        exclude_none=True
                    )
                else:
                    # Strawberry object - convert manually
                    update_data = {}
                    track_attrs = ['title', 'path', 'track_artist_id', 'album_id', 'duration', 'track_number',
                                 'disc_number', 'year', 'genre', 'file_type', 'bitrate', 'featured_artists',
                                 'bpm', 'key', 'scale', 'danceability', 'mood_happy', 'mood_aggressive',
                                 'mood_party', 'mood_relaxed', 'instrumental', 'acoustic', 'tonal',
                                 'camelot_key', 'genre_main', 'musicbrainz_id', 'musicbrainz_albumid',
                                 'musicbrainz_artistid', 'musicbrainz_albumartistid', 'acoustid_fingerprint']
                    for attr in track_attrs:
                        if hasattr(track_data, attr):
                            value = getattr(track_data, attr)
                            if value is not None:
                                update_data[attr] = value

                # Mise à jour des attributs simples
                for key, value in update_data.items():
                    if hasattr(existing_track, key) and not isinstance(value, (dict, list)):
                        setattr(existing_track, key, value)

                existing_track.date_modified = func.now()
                self.session.commit()
                self.session.refresh(existing_track)
                return existing_track
            else:
                # Create new track
                # Handle both Pydantic models and Strawberry objects
                if hasattr(track_data, 'model_dump'):
                    track_dict = track_data.model_dump(exclude_unset=True)
                else:
                    # Strawberry object - convert manually
                    track_dict = {}
                    track_attrs = ['title', 'path', 'track_artist_id', 'album_id', 'duration', 'track_number',
                                 'disc_number', 'year', 'genre', 'file_type', 'bitrate', 'featured_artists',
                                 'bpm', 'key', 'scale', 'danceability', 'mood_happy', 'mood_aggressive',
                                 'mood_party', 'mood_relaxed', 'instrumental', 'acoustic', 'tonal',
                                 'camelot_key', 'genre_main', 'musicbrainz_id', 'musicbrainz_albumid',
                                 'musicbrainz_artistid', 'musicbrainz_albumartistid', 'acoustid_fingerprint']
                    for attr in track_attrs:
                        if hasattr(track_data, attr):
                            value = getattr(track_data, attr)
                            track_dict[attr] = value

                db_track = TrackModel(**track_dict)
                self.session.add(db_track)
                self.session.commit()
                self.session.refresh(db_track)
                return db_track

        except IntegrityError as e:
            self.session.rollback()
            if "UNIQUE constraint failed: tracks.musicbrainz_id" in str(e):
                existing = self.session.query(TrackModel).filter(
                    TrackModel.musicbrainz_id == track_data.musicbrainz_id
                ).first()
                if existing:
                    return existing
            raise Exception("Erreur lors de l'upsert de la piste")
        except Exception as e:
            self.session.rollback()
            raise Exception(str(e))

    def update_tracks_by_filter(self, filter_data, update_data):
        """Update multiple tracks by filter."""
        try:
            query = self.session.query(TrackModel)

            # Apply filters
            if 'title' in filter_data:
                if 'icontains' in filter_data['title']:
                    query = query.filter(
                        func.lower(TrackModel.title).like(f"%{filter_data['title']['icontains'].lower()}%")
                    )
                elif isinstance(filter_data['title'], str):
                    query = query.filter(TrackModel.title == filter_data['title'])

            if 'musicbrainz_id' in filter_data:
                query = query.filter(TrackModel.musicbrainz_id == filter_data['musicbrainz_id'])

            # Get tracks to update
            tracks_to_update = query.all()

            if not tracks_to_update:
                return []

            # Update each track
            updated_tracks = []
            for track in tracks_to_update:
                for key, value in update_data.items():
                    if hasattr(track, key) and value is not None:
                        setattr(track, key, value)
                track.date_modified = func.now()
                updated_tracks.append(track)

            self.session.commit()

            # Refresh all updated tracks
            for track in updated_tracks:
                self.session.refresh(track)

            return updated_tracks

        except Exception as e:
            self.session.rollback()
            raise Exception(f"Erreur lors de la mise à jour par filtre: {str(e)}")

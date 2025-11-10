from sqlalchemy.orm import joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from backend.library_api.api.models.tracks_model import Track as TrackModel
from backend.library_api.api.models.genres_model import Genre
from backend.library_api.api.models.tags_model import GenreTag, MoodTag
from backend.library_api.api.schemas.tracks_schema import TrackCreate
from backend.library_api.utils.logging import logger
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
        """
        Crée ou met à jour des pistes en batch de manière optimisée.

        Gère correctement les contraintes d'unicité sur path et musicbrainz_id.

        Args:
            tracks_data: Liste des données de pistes à traiter

        Returns:
            Liste des pistes créées ou mises à jour
        """
        if not tracks_data:
            return []

        logger.info(f"[TRACK_BATCH] Traitement de {len(tracks_data)} pistes en batch")

        # Étape 1: Récupérer tous les paths et musicbrainz_id existants
        paths = [data.path for data in tracks_data if data.path]
        mbid_values = [data.musicbrainz_id for data in tracks_data if data.musicbrainz_id]
        
        existing_tracks_by_path = {}
        existing_tracks_by_mbid = {}

        # Requête pour récupérer les tracks existantes par path
        if paths:
            existing_tracks = self.session.query(TrackModel).filter(TrackModel.path.in_(paths)).all()
            existing_tracks_by_path = {track.path: track for track in existing_tracks}

        # Requête pour récupérer les tracks existantes par musicbrainz_id
        if mbid_values:
            existing_mbid_tracks = self.session.query(TrackModel).filter(
                TrackModel.musicbrainz_id.in_(mbid_values)
            ).all()
            existing_tracks_by_mbid = {track.musicbrainz_id: track for track in existing_mbid_tracks}

        # Étape 2: Séparer les tracks en évitant les doublons de musicbrainz_id
        tracks_to_create = []
        tracks_to_update = []
        tracks_to_return_unchanged = []
        processed_mbids = set()  # Pour éviter les doublons de musicbrainz_id

        for data in tracks_data:
            existing = None

            # Recherche prioritaire par musicbrainz_id (contrainte d'unicité)
            if data.musicbrainz_id and data.musicbrainz_id in existing_tracks_by_mbid:
                existing = existing_tracks_by_mbid[data.musicbrainz_id]
                processed_mbids.add(data.musicbrainz_id)
            # Sinon recherche par path
            elif data.path and data.path in existing_tracks_by_path:
                existing = existing_tracks_by_path[data.path]

            if existing:
                # Vérifier si le fichier a changé
                file_changed = True
                if hasattr(data, 'file_mtime') and hasattr(data, 'file_size'):
                    try:
                        if (existing.file_mtime == data.file_mtime and
                            existing.file_size == data.file_size):
                            file_changed = False
                    except AttributeError:
                        # Si les colonnes n'existent pas, considérer que le fichier a changé
                        pass

                if file_changed:
                    tracks_to_update.append((existing, data))
                else:
                    # Track inchangée, la retourner directement
                    tracks_to_return_unchanged.append(existing)
            else:
                tracks_to_create.append(data)

        logger.info(f"[TRACK_BATCH] {len(tracks_to_create)} à créer, {len(tracks_to_update)} à mettre à jour, {len(tracks_to_return_unchanged)} inchangées, {len(processed_mbids)} MBIDs ignorés (doublons)")

        result = []

        # Étape 3: Création en batch avec gestion d'erreur améliorée
        if tracks_to_create:
            created_tracks = self._create_tracks_batch_optimized(tracks_to_create)
            result.extend(created_tracks)

        # Étape 4: Mise à jour en batch
        if tracks_to_update:
            updated_tracks = self._update_tracks_batch_optimized(tracks_to_update)
            result.extend(updated_tracks)

        # Étape 5: Ajouter les pistes inchangées directement (pas besoin de requête DB)
        result.extend(tracks_to_return_unchanged)

        logger.info(f"[TRACK_BATCH] Batch terminé: {len(result)} pistes traitées")
        return result

    def _create_tracks_batch_optimized(self, tracks_data: List[TrackCreate]):
        """Crée plusieurs pistes en une seule transaction avec gestion robuste des contraintes d'unicité."""
        try:
            # Préparer les objets TrackModel avec dédoublonnage préalable
            tracks_to_insert = []
            seen_paths = set()
            seen_mbids = set()
            
            for data in tracks_data:
                # Éviter les doublons par path
                if data.path and data.path in seen_paths:
                    logger.warning(f"[TRACK_BATCH] Path déjà présent dans le batch: {data.path}")
                    continue
                    
                # Éviter les doublons par musicbrainz_id
                if data.musicbrainz_id and data.musicbrainz_id in seen_mbids:
                    logger.warning(f"[TRACK_BATCH] MBID déjà présent dans le batch: {data.musicbrainz_id}")
                    continue
                
                # Vérifier si la track existe déjà en base (path ou MBID)
                existing = None
                if data.musicbrainz_id:
                    existing = self.session.query(TrackModel).filter(
                        TrackModel.musicbrainz_id == data.musicbrainz_id
                    ).first()
                    
                if not existing and data.path:
                    existing = self.session.query(TrackModel).filter(
                        TrackModel.path == data.path
                    ).first()
                
                if existing:
                    logger.warning(f"[TRACK_BATCH] Track déjà existante ignorée: {data.title} (ID: {existing.id})")
                    continue
                    
                # Créer la nouvelle track
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
                    bitrate=data.bitrate,
                    file_mtime=data.file_mtime,
                    file_size=data.file_size
                )
                tracks_to_insert.append(track)
                
                # Marquer comme vu
                if data.path:
                    seen_paths.add(data.path)
                if data.musicbrainz_id:
                    seen_mbids.add(data.musicbrainz_id)

            if not tracks_to_insert:
                logger.warning("[TRACK_BATCH] Aucune track valide à insérer")
                return []

            # Insertion en batch avec gestion d'erreur spécifique
            try:
                self.session.add_all(tracks_to_insert)
                self.session.commit()
            except IntegrityError as e:
                self.session.rollback()
                
                # Gestion spécifique des violations de contrainte
                if "UNIQUE constraint failed: tracks.musicbrainz_id" in str(e):
                    logger.error("[TRACK_BATCH] Violation contrainte musicbrainz_id. Vérification des doublons...")
                    # Vérifier quels MBIDs causent problème
                    for track_data in tracks_data:
                        if track_data.musicbrainz_id:
                            existing = self.session.query(TrackModel).filter(
                                TrackModel.musicbrainz_id == track_data.musicbrainz_id
                            ).first()
                            if existing:
                                logger.warning(f"[TRACK_BATCH] MBID existant: {track_data.musicbrainz_id} → Track ID: {existing.id}")
                    
                    # Réessayer l'insertion sans les MBIDs problématiques
                    tracks_without_mbid = []
                    for track in tracks_to_insert:
                        if not track.musicbrainz_id:
                            tracks_without_mbid.append(track)
                    
                    if tracks_without_mbid:
                        logger.info(f"[TRACK_BATCH] Réinsertion sans MBIDs: {len(tracks_without_mbid)} tracks")
                        try:
                            self.session.add_all(tracks_without_mbid)
                            self.session.commit()
                            tracks_to_insert = tracks_without_mbid
                        except Exception as retry_e:
                            self.session.rollback()
                            logger.error(f"[TRACK_BATCH] Erreur lors de la réinsertion: {retry_e}")
                            raise retry_e
                    else:
                        raise e
                        
                elif "UNIQUE constraint failed: tracks.path" in str(e):
                    logger.error("[TRACK_BATCH] Violation contrainte path. Vérification des doublons...")
                    raise Exception("Conflit de chemin détecté - certaines tracks existent déjà")
                else:
                    logger.error(f"[TRACK_BATCH] Violation de contrainte non gérée: {e}")
                    raise e
            except Exception as e:
                self.session.rollback()
                logger.error(f"[TRACK_BATCH] Erreur création batch: {e}")
                raise

            # Refresh pour récupérer les IDs générés
            for track in tracks_to_insert:
                self.session.refresh(track)

            logger.info(f"[TRACK_BATCH] {len(tracks_to_insert)} pistes créées en batch")
            return tracks_to_insert

        except Exception as e:
            if self.session.is_active:
                self.session.rollback()
            logger.error(f"[TRACK_BATCH] Erreur création batch: {e}")
            raise

    def _update_tracks_batch_optimized(self, tracks_to_update: List[tuple]):
        """Met à jour plusieurs pistes en une seule transaction."""
        try:
            updated_tracks = []

            for existing, data in tracks_to_update:
                # Mise à jour des champs
                update_data = data.model_dump(exclude_unset=True, exclude_none=True)
                for field, value in update_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)

                existing.date_modified = func.now()
                updated_tracks.append(existing)

            # Commit unique pour toutes les mises à jour
            self.session.commit()

            # Refresh pour s'assurer que les données sont à jour
            for track in updated_tracks:
                self.session.refresh(track)

            logger.info(f"[TRACK_BATCH] {len(updated_tracks)} pistes mises à jour en batch")
            return updated_tracks

        except Exception as e:
            self.session.rollback()
            logger.error(f"[TRACK_BATCH] Erreur mise à jour batch: {e}")
            raise

    def search_tracks(self,
        title: Optional[str], artist: Optional[str], album: Optional[str], genre: Optional[str], year: Optional[str],
        path: Optional[str], musicbrainz_id: Optional[str], genre_tags: Optional[List[str]], mood_tags: Optional[List[str]],
        skip: int = 0, limit: Optional[int] = None
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

        # Appliquer la pagination
        if limit is not None:
            query = query.offset(skip).limit(limit)

        tracks = query.all()

        return tracks

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

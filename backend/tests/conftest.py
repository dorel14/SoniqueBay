# backend/tests/conftest.py
import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ajouter le répertoire racine au sys.path si nécessaire
root_dir = os.getcwd()
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.utils.database import Base, get_db
from backend.api_app import create_api
import tempfile
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track
from backend.api.models.genres_model import Genre
from backend.api.models.covers_model import Cover
from backend.api.models.tags_model import GenreTag, MoodTag

# Base de données SQLite temporaire pour les tests
@pytest.fixture(scope="session")
def test_db_engine():
    import tempfile
    import os
    # Créer un fichier temporaire pour la base de données
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_url = f"sqlite:///{temp_db.name}"
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    # Properly dispose of all connections before cleanup
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    # Supprimer le fichier temporaire avec gestion d'erreur
    try:
        os.unlink(temp_db.name)
    except (OSError, PermissionError):
        # Sur Windows, le fichier peut encore être verrouillé
        # On peut essayer de le supprimer plus tard ou l'ignorer
        pass

@pytest.fixture
def db_session(test_db_engine):
    """Session de base de données pour les tests."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(db_session):
    """Client de test FastAPI avec une base de données de test."""
    app = create_api()

    # Override de la dépendance get_db pour utiliser notre session de test
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

# Fixtures pour créer des données de test

@pytest.fixture
def create_test_artist(db_session):
    """Crée un artiste de test."""
    def _create_artist(name="Test Artist", musicbrainz_artistid=None):
        artist = Artist(name=name, musicbrainz_artistid=musicbrainz_artistid)
        db_session.add(artist)
        db_session.flush()  # Make it available in session
        return artist
    return _create_artist

@pytest.fixture
def create_test_artists(db_session):
    """Crée plusieurs artistes de test."""
    def _create_artists(count=3):
        artists = []
        for i in range(count):
            artist = Artist(name=f"Test Artist {i}", musicbrainz_artistid=f"test-mb-id-{i}")
            db_session.add(artist)
            artists.append(artist)
        db_session.flush()
        return artists
    return _create_artists

@pytest.fixture
def create_test_album(db_session, create_test_artist):
    """Crée un album de test."""
    def _create_album(title="Test Album", artist_id=None, musicbrainz_albumid=None):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id
        album = Album(title=title, album_artist_id=artist_id, musicbrainz_albumid=musicbrainz_albumid)
        db_session.add(album)
        db_session.flush()
        return album
    return _create_album

@pytest.fixture
def create_test_albums(db_session, create_test_artist):
    """Crée plusieurs albums de test."""
    def _create_albums(count=3, artist_id=None):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id
        albums = []
        for i in range(count):
            album = Album(title=f"Test Album {i}", album_artist_id=artist_id, musicbrainz_albumid=f"test-mb-album-id-{i}")
            db_session.add(album)
            albums.append(album)
        db_session.flush()
        return albums
    return _create_albums

@pytest.fixture
def create_test_track(db_session, create_test_artist):
    """Crée une piste de test."""
    def _create_track(title="Test Track", path="/path/to/test.mp3", artist_id=None, album_id=None, **kwargs):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id

        track_data = {
            "title": title,
            "path": path,
            "track_artist_id": artist_id,
            "album_id": album_id,
            **kwargs
        }

        track = Track(**track_data)
        db_session.add(track)
        db_session.commit()
        return track
    return _create_track

@pytest.fixture
def create_test_tracks(db_session, create_test_artist):
    """Crée plusieurs pistes de test."""
    def _create_tracks(count=3, artist_id=None, album_id=None):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id

        tracks = []
        for i in range(count):
            track = Track(
                title=f"Test Track {i}",
                path=f"/path/to/test{i}.mp3",
                track_artist_id=artist_id,
                album_id=album_id
            )
            db_session.add(track)
            tracks.append(track)

        db_session.commit()
        return tracks
    return _create_tracks

@pytest.fixture
def create_test_album_with_artist(db_session, create_test_artist):
    """Crée un album avec son artiste."""
    def _create_album_with_artist():
        artist = create_test_artist()
        album = Album(title="Test Album", album_artist_id=artist.id)
        db_session.add(album)
        db_session.commit()
        return album, artist
    return _create_album_with_artist

@pytest.fixture
def create_test_track_with_relations(db_session, create_test_artist, create_test_album):
    """Crée une piste avec artiste et album."""
    def _create_track_with_relations():
        artist = create_test_artist()
        album = create_test_album(album_artist_id=artist.id)

        track = Track(
            title="Test Track with Relations",
            path="/path/to/relations_test.mp3",
            track_artist_id=artist.id,
            album_id=album.id
        )
        db_session.add(track)
        db_session.commit()

        return track, artist, album
    return _create_track_with_relations

@pytest.fixture
def create_test_artist_with_tracks(db_session, create_test_artist, create_test_tracks):
    """Crée un artiste avec plusieurs pistes."""
    def _create_artist_with_tracks(track_count=3):
        artist = create_test_artist()
        tracks = create_test_tracks(count=track_count, artist_id=artist.id)
        return artist, tracks
    return _create_artist_with_tracks

@pytest.fixture
def create_test_artist_album_tracks(db_session, create_test_artist, create_test_album, create_test_tracks):
    """Crée un artiste, un album et des pistes associées."""
    def _create_artist_album_tracks(track_count=3):
        artist = create_test_artist()
        album = create_test_album(artist_id=artist.id)
        tracks = create_test_tracks(count=track_count, artist_id=artist.id, album_id=album.id)
        return artist, album, tracks
    return _create_artist_album_tracks

@pytest.fixture
def create_test_tracks_with_metadata(db_session, create_test_artist, create_test_album):
    """Crée des pistes avec des métadonnées variées."""
    def _create_tracks_with_metadata():
        artist = create_test_artist()
        album = create_test_album(album_artist_id=artist.id)

        tracks = []
        # Piste Rock
        track1 = Track(
            title="Test Rock Track",
            path="/path/to/rock.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Rock",
            year="2023",
            bpm=120.5,
            key="C",
            scale="major"
        )
        db_session.add(track1)
        tracks.append(track1)

        # Piste Jazz
        track2 = Track(
            title="Test Jazz Track",
            path="/path/to/jazz.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Jazz",
            year="2022",
            bpm=90.0,
            key="D",
            scale="minor"
        )
        db_session.add(track2)
        tracks.append(track2)

        # Piste Electronic
        track3 = Track(
            title="Test Electronic Track",
            path="/path/to/electronic.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Electronic",
            year="2023",
            bpm=128.0,
            key="A",
            scale="minor"
        )
        db_session.add(track3)
        tracks.append(track3)

        db_session.commit()
        return tracks
    return _create_tracks_with_metadata

@pytest.fixture
def create_test_track_with_tags(db_session, create_test_track):
    """Crée une piste avec des tags."""
    def _create_track_with_tags():
        track = create_test_track()

        # Ajouter des genre_tags
        genre_tags = [
            GenreTag(name="rock"),
            GenreTag(name="indie"),
            GenreTag(name="alternative")
        ]
        for tag in genre_tags:
            db_session.add(tag)

        # Ajouter des mood_tags
        mood_tags = [
            MoodTag(name="happy"),
            MoodTag(name="energetic"),
            MoodTag(name="upbeat")
        ]
        for tag in mood_tags:
            db_session.add(tag)

        db_session.commit()

        # Associer les tags à la piste
        track.genre_tags = genre_tags
        track.mood_tags = mood_tags
        db_session.commit()

        return track
    return _create_track_with_tags
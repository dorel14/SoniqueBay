# tests/conftest.py
import pytest
import sys
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import backend.library_api.utils.search
from backend.library_api.utils.database import Base, get_db, get_session
from backend.library_api.api_app import create_api
from backend.library_api.api.models.artists_model import Artist
from backend.library_api.api.models.albums_model import Album
from backend.library_api.api.models.tracks_model import Track
from backend.library_api.api.models.genres_model import Genre
from backend.library_api.api.models.covers_model import Cover
from backend.library_api.api.models.tags_model import GenreTag, MoodTag

# Ajouter le répertoire racine au sys.path
root_dir = os.getcwd()
sys.path.insert(0, root_dir)
os.environ['PYTHONPATH'] = root_dir

# Fixture pour nettoyer le dossier search_indexes après chaque test
@pytest.fixture(autouse=True)
def cleanup_search_indexes():
    """Nettoie le dossier search_indexes après chaque test."""
    yield
    # Nettoyage après le test
    search_indexes_dir = os.path.join(root_dir, "tests", "search_indexes")
    if os.path.exists(search_indexes_dir):
        import shutil
        shutil.rmtree(search_indexes_dir, ignore_errors=True)

# Base de données SQLite temporaire pour les tests
@pytest.fixture(scope="function")
def test_db_engine():
    import os
    # Créer un fichier marqueur pour indiquer qu'on est en mode test
    test_marker_file = os.path.join(os.getcwd(), '.test_mode')
    with open(test_marker_file, 'w') as f:
        f.write('1')

    backend.library_api.utils.search.BASE_SEARCH_DIR = Path(tempfile.mkdtemp())

    # Créer un fichier temporaire pour la base de données
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_url = f"sqlite:///{temp_db.name}"
    os.environ['DATABASE_URL'] = db_url
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)

    # Create FTS tables for testing
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
            title, artist_name, album_title, genre, genre_tags, mood_tags,
            content=tracks,
            content_rowid=id
        );
        """))
        conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS artists_fts USING fts5(
            name, genre,
            content=artists,
            content_rowid=id
        );
        """))
        conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS albums_fts USING fts5(
            title, artist_name, genre,
            content=albums,
            content_rowid=id
        );
        """))
        conn.execute(text("CREATE TABLE IF NOT EXISTS function_calls (id INTEGER PRIMARY KEY AUTOINCREMENT, function_name TEXT, args TEXT, kwargs TEXT, result TEXT, timestamp TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS scan_sessions (id TEXT PRIMARY KEY, directory TEXT, status TEXT, last_processed_file TEXT, processed_files INTEGER, total_files INTEGER, task_id TEXT, started_at TEXT, updated_at TEXT)"))
        conn.commit()
    yield engine
    # Properly dispose of all connections before cleanup
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    # Supprimer le fichier temporaire avec gestion d'erreur
    import time
    time.sleep(0.1)  # Petit délai pour permettre la libération du fichier
    try:
        os.unlink(temp_db.name)
    except (OSError, PermissionError):
        # Sur Windows, le fichier peut encore être verrouillé
        # On peut essayer de le supprimer plus tard ou l'ignorer
        pass

    # Supprimer le fichier marqueur
    try:
        os.unlink(test_marker_file)
    except (OSError, PermissionError):
        pass


@pytest.fixture(scope="function")
def encryption_key():
    """Fixture qui définit une clé de cryptage fixe pour les tests."""
    import os

    # Utiliser une clé fixe valide pour les tests
    test_key = b'PJMY7VW4nm_gUJ8UO43EgbKrJm9gJ0F-WxqK-NSIoh0='

    # Sauvegarder la clé existante si elle existe
    original_key = os.environ.get('ENCRYPTION_KEY')

    # Définir la clé de test
    os.environ['ENCRYPTION_KEY'] = test_key.decode()

    yield test_key

    # Restaurer la clé originale
    if original_key is not None:
        os.environ['ENCRYPTION_KEY'] = original_key
    else:
        os.environ.pop('ENCRYPTION_KEY', None)

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

    # Override de la dépendance get_session pour utiliser notre session de test
    def override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def recommender_client(db_session):
    """Client de test FastAPI pour recommender_api avec une base de données de test."""
    from backend.recommender_api.api_app import create_api as create_recommender_api
    app = create_recommender_api()

    # Override de la dépendance get_db pour utiliser notre session de test
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override de la dépendance get_session pour utiliser notre session de test
    def override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

# Fixtures pour créer des données de test

@pytest.fixture
def create_test_artist(db_session):
    """Crée un artiste de test."""
    def _create_artist(name=None, musicbrainz_artistid=None):
        import uuid
        if name is None:
            name = f"Test Artist {str(uuid.uuid4())[:8]}"
        if musicbrainz_artistid is None:
            musicbrainz_artistid = "test-mb-id-93cb930b"  # Fixed value for snapshot tests
        artist = Artist(name=name, musicbrainz_artistid=musicbrainz_artistid)
        db_session.add(artist)
        db_session.flush()  # Make it available in session
        return artist
    return _create_artist

@pytest.fixture
def create_test_artists(db_session):
    """Crée plusieurs artistes de test."""
    def _create_artists(count=3, names=None):
        artists = []
        for i in range(count):
            name = names[i] if names and i < len(names) else f"Test Artist {i}"
            artist = Artist(name=name, musicbrainz_artistid=f"test-mb-id-{i}")
            db_session.add(artist)
            artists.append(artist)
        db_session.flush()
        return artists
    return _create_artists

@pytest.fixture
def create_test_album(db_session, create_test_artist):
    """Crée un album de test."""
    def _create_album(title="Test Album", artist_id=None, musicbrainz_albumid="test-mb-album-id", release_year=2023):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id
        album = Album(title=title, album_artist_id=artist_id, musicbrainz_albumid=musicbrainz_albumid, release_year=release_year)
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
    def _create_track(title="Test Track", path="/path/to/test.mp3", artist_id=None, album_id=None, genre="Rock", bpm=120.0, key="C", scale="major", **kwargs):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id

        if album_id is None:
            album = Album(title="Test Album", album_artist_id=artist_id)
            db_session.add(album)
            db_session.flush()
            album_id = album.id

        track_data = {
            "title": title,
            "path": path,
            "track_artist_id": artist_id,
            "album_id": album_id,
            "genre": genre,
            "bpm": bpm,
            "key": key,
            "scale": scale,
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

@pytest.fixture
def create_test_genre(db_session):
    """Crée un genre de test."""
    def _create_genre(name="Test Genre"):
        genre = Genre(name=name)
        db_session.add(genre)
        db_session.flush()
        return genre
    return _create_genre

@pytest.fixture
def create_test_genres(db_session):
    """Crée plusieurs genres de test."""
    def _create_genres(count=3):
        genres = []
        for i in range(count):
            genre = Genre(name=f"Test Genre {i}")
            db_session.add(genre)
            genres.append(genre)
        db_session.flush()
        return genres
    return _create_genres

@pytest.fixture
def create_test_cover(db_session):
    """Crée une cover de test."""
    def _create_cover(entity_type="album", entity_id=1, cover_data="base64data", mime_type="image/jpeg"):
        cover = Cover(
            entity_type=entity_type,
            entity_id=entity_id,
            cover_data=cover_data,
            mime_type=mime_type
        )
        db_session.add(cover)
        db_session.flush()
        return cover
    return _create_cover

@pytest.fixture
def create_test_covers(db_session):
    """Crée plusieurs covers de test."""
    def _create_covers(count=3, entity_type="album", entity_id=1):
        covers = []
        for i in range(count):
            cover = Cover(
                entity_type=entity_type,
                entity_id=entity_id,
                cover_data=f"base64data{i}",
                mime_type="image/jpeg"
            )
            db_session.add(cover)
            covers.append(cover)
        db_session.flush()
        return covers
    return _create_covers

@pytest.fixture
def create_test_genre_tag(db_session):
    """Crée un genre tag de test."""
    def _create_genre_tag(name="Test Genre Tag"):
        genre_tag = GenreTag(name=name)
        db_session.add(genre_tag)
        db_session.flush()
        return genre_tag
    return _create_genre_tag

@pytest.fixture
def create_test_genre_tags(db_session):
    """Crée plusieurs genre tags de test."""
    def _create_genre_tags(count=3):
        genre_tags = []
        for i in range(count):
            genre_tag = GenreTag(name=f"Test Genre Tag {i}")
            db_session.add(genre_tag)
            genre_tags.append(genre_tag)
        db_session.flush()
        return genre_tags
    return _create_genre_tags

@pytest.fixture
def create_test_mood_tag(db_session):
    """Crée un mood tag de test."""
    def _create_mood_tag(name="Test Mood Tag"):
        mood_tag = MoodTag(name=name)
        db_session.add(mood_tag)
        db_session.flush()
        return mood_tag
    return _create_mood_tag

@pytest.fixture
def create_test_mood_tags(db_session):
    """Crée plusieurs mood tags de test."""
    def _create_mood_tags(count=3):
        mood_tags = []
        for i in range(count):
            mood_tag = MoodTag(name=f"Test Mood Tag {i}")
            db_session.add(mood_tag)
            mood_tags.append(mood_tag)
        db_session.flush()
        return mood_tags
    return _create_mood_tags
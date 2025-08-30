# backend/tests/test_models/test_tracks_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track
# backend/tests/test_models/test_tracks_model.py
from sqlalchemy.exc import IntegrityError

def test_create_track(db_session):
    """Test de création d'une piste en BDD."""
    # Créer d'abord un artiste et un album
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer une piste
    track = Track(
        title="Test Track",
        path="/path/to/test.mp3",
        track_artist_id=artist.id,
        album_id=album.id,
        duration=180,
        track_number="1",
        disc_number="1",
        year="2023",
        genre="Rock"
    )
    db_session.add(track)
    db_session.commit()

    # Vérifier que la piste a été créée
    assert track.id is not None

    # Récupérer la piste depuis la BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track is not None
    assert db_track.title == "Test Track"
    assert db_track.path == "/path/to/test.mp3"
    assert db_track.track_artist_id == artist.id
    assert db_track.album_id == album.id

def test_track_unique_path_constraint(db_session):
    """Test de la contrainte d'unicité sur le chemin de la piste."""
    # Créer un artiste
    artist = Artist(name="Test Artist 2")
    db_session.add(artist)
    db_session.flush()

    # Créer une première piste
    track1 = Track(
        title="Track 1",
        path="/path/to/duplicate.mp3",
        track_artist_id=artist.id
    )
    db_session.add(track1)
    db_session.commit()

    # Tenter de créer une seconde piste avec le même chemin
    track2 = Track(
        title="Track 2",
        path="/path/to/duplicate.mp3",
        track_artist_id=artist.id
    )
    db_session.add(track2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_track_relationships(db_session):
    """Test des relations entre les modèles."""
# Créer un artiste
    artist = Artist(name="Relationship Test Artist")
    db_session.add(artist)
    db_session.flush()

    # Créer un album
    album = Album(title="Relationship Test Album", artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer une piste
    track = Track(
        title="Relationship Test Track",
        path="/path/to/relationship_test.mp3",
        track_artist_id=artist.id,
        album_id=album.id
    )
    db_session.add(track)
    db_session.commit()

    # Vérifier les relations
    assert track.artist.id == artist.id
    assert track.artist.name == "Relationship Test Artist"
    assert track.album.id == album.id
    assert track.album.title == "Relationship Test Album"

    # Vérifier les relations inverses
    assert track in artist.tracks
    assert track in album.tracks
# backend/tests/test_models/test_artists_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.artists_model import Artist

def test_create_artist(db_session):
    """Test de création d'un artiste en BDD."""
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()

    # Vérifier que l'artiste a été créé
    assert artist.id is not None

    # Récupérer l'artiste depuis la BDD
    db_artist = db_session.query(Artist).filter(Artist.id == artist.id).first()
    assert db_artist is not None
    assert db_artist.name == "Test Artist"

def test_create_artist_with_musicbrainz(db_session):
    """Test de création d'un artiste avec MusicBrainz ID."""
    artist = Artist(
        name="Test Artist with MBID",
        musicbrainz_artistid="test-mb-id-123"
    )
    db_session.add(artist)
    db_session.commit()

    # Vérifier les données
    assert artist.id is not None
    assert artist.name == "Test Artist with MBID"
    assert artist.musicbrainz_artistid == "test-mb-id-123"

def test_artist_unique_name_constraint(db_session):
    """Test de la contrainte d'unicité sur le nom de l'artiste."""
    # Créer un premier artiste
    artist1 = Artist(name="Unique Artist")
    db_session.add(artist1)
    db_session.commit()

    # Tenter de créer un second artiste avec le même nom
    artist2 = Artist(name="Unique Artist")
    db_session.add(artist2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_artist_relationships_with_tracks(db_session):
    """Test des relations entre artiste et pistes."""
    # Créer un artiste
    artist = Artist(name="Artist with Tracks")
    db_session.add(artist)
    db_session.flush()

    # Créer des pistes pour cet artiste
    from backend.api.models.tracks_model import Track
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.commit()

    # Vérifier les relations
    assert len(artist.tracks) == 2
    assert track1 in artist.tracks
    assert track2 in artist.tracks
    assert track1.artist.id == artist.id
    assert track2.artist.id == artist.id

def test_artist_relationships_with_albums(db_session):
    """Test des relations entre artiste et albums."""
    # Créer un artiste
    artist = Artist(name="Artist with Albums")
    db_session.add(artist)
    db_session.flush()

    # Créer des albums pour cet artiste
    from backend.api.models.albums_model import Album
    album1 = Album(title="Album 1", album_artist_id=artist.id)
    album2 = Album(title="Album 2", album_artist_id=artist.id)
    db_session.add(album1)
    db_session.add(album2)
    db_session.commit()

    # Vérifier les relations
    assert len(artist.albums) == 2
    assert album1 in artist.albums
    assert album2 in artist.albums
    assert album1.artist.id == artist.id
    assert album2.artist.id == artist.id
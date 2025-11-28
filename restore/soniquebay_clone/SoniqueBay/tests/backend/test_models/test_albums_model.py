# backend/tests/test_models/test_albums_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.albums_model import Album
from backend.api.models.artists_model import Artist
from backend.api.models.tracks_model import Track
from backend.api.models.genres_model import Genre

def test_create_album(db_session):
    """Test de création d'un album en BDD."""
    # Créer d'abord un artiste
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.flush()

    # Créer un album
    album = Album(
        title="Test Album",
        album_artist_id=artist.id,
        release_year="2023",
        musicbrainz_albumid="test-mb-album-id"
    )
    db_session.add(album)
    db_session.commit()

    # Vérifier que l'album a été créé
    assert album.id is not None

    # Récupérer l'album depuis la BDD
    db_album = db_session.query(Album).filter(Album.id == album.id).first()
    assert db_album is not None
    assert db_album.title == "Test Album"
    assert db_album.album_artist_id == artist.id
    assert db_album.release_year == "2023"
    assert db_album.musicbrainz_albumid == "test-mb-album-id"

def test_album_title_not_null_constraint(db_session):
    """Test de la contrainte NOT NULL sur le titre de l'album."""
    # Créer un artiste
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.flush()

    # Tenter de créer un album sans titre
    album = Album(album_artist_id=artist.id)
    db_session.add(album)

    # Vérifier que la contrainte est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_album_artist_id_not_null_constraint(db_session):
    """Test de la contrainte NOT NULL sur album_artist_id."""
    # Tenter de créer un album sans artiste
    album = Album(title="Test Album")
    db_session.add(album)

    # Vérifier que la contrainte est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_album_relationships_with_artist(db_session):
    """Test des relations entre album et artiste."""
    # Créer un artiste
    artist = Artist(name="Artist with Albums")
    db_session.add(artist)
    db_session.flush()

    # Créer des albums pour cet artiste
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

def test_album_relationships_with_tracks(db_session):
    """Test des relations entre album et pistes."""
    # Créer un artiste
    artist = Artist(name="Artist for Album Tracks")
    db_session.add(artist)
    db_session.flush()

    # Créer un album
    album = Album(title="Album with Tracks", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer des pistes pour cet album
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id, album_id=album.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.commit()

    # Vérifier les relations
    assert len(album.tracks) == 2
    assert track1 in album.tracks
    assert track2 in album.tracks
    assert track1.album.id == album.id
    assert track2.album.id == album.id

def test_album_relationships_with_genres(db_session):
    """Test des relations entre album et genres."""
    # Créer un artiste
    artist = Artist(name="Artist for Album Genres")
    db_session.add(artist)
    db_session.flush()

    # Créer un album
    album = Album(title="Album with Genres", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer des genres
    genre1 = Genre(name="Rock")
    genre2 = Genre(name="Pop")
    db_session.add(genre1)
    db_session.add(genre2)
    db_session.flush()

    # Associer les genres à l'album
    album.genres.append(genre1)
    album.genres.append(genre2)
    db_session.commit()

    # Vérifier les relations
    assert len(album.genres) == 2
    assert genre1 in album.genres
    assert genre2 in album.genres
    assert album in genre1.albums
    assert album in genre2.albums

def test_album_same_title_different_artists(db_session):
    """Test que des albums peuvent avoir le même titre avec des artistes différents."""
    # Créer deux artistes
    artist1 = Artist(name="Artist 1")
    artist2 = Artist(name="Artist 2")
    db_session.add(artist1)
    db_session.add(artist2)
    db_session.flush()

    # Créer des albums avec le même titre pour des artistes différents
    album1 = Album(title="Same Title", album_artist_id=artist1.id)
    album2 = Album(title="Same Title", album_artist_id=artist2.id)
    db_session.add(album1)
    db_session.add(album2)
    db_session.commit()

    # Vérifier que les deux albums existent
    assert album1.id is not None
    assert album2.id is not None
    assert album1.title == album2.title
    assert album1.album_artist_id != album2.album_artist_id
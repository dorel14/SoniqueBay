# backend/tests/test_models/test_genres_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.genres_model import Genre
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track

def test_create_genre(db_session):
    """Test de création d'un genre en BDD."""
    genre = Genre(name="Rock")
    db_session.add(genre)
    db_session.commit()

    # Vérifier que le genre a été créé
    assert genre.id is not None

    # Récupérer le genre depuis la BDD
    db_genre = db_session.query(Genre).filter(Genre.id == genre.id).first()
    assert db_genre is not None
    assert db_genre.name == "Rock"

def test_genre_name_not_null_constraint(db_session):
    """Test de la contrainte NOT NULL sur le nom du genre."""
    # Tenter de créer un genre sans nom
    genre = Genre()
    db_session.add(genre)

    # Vérifier que la contrainte est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_genre_unique_name_constraint(db_session):
    """Test de la contrainte d'unicité sur le nom du genre."""
    # Créer un premier genre
    genre1 = Genre(name="Unique Genre")
    db_session.add(genre1)
    db_session.commit()

    # Tenter de créer un second genre avec le même nom
    genre2 = Genre(name="Unique Genre")
    db_session.add(genre2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_genre_relationships_with_artists(db_session):
    """Test des relations entre genre et artistes."""
    # Créer un genre
    genre = Genre(name="Jazz")
    db_session.add(genre)
    db_session.flush()

    # Créer des artistes
    artist1 = Artist(name="Artist 1")
    artist2 = Artist(name="Artist 2")
    db_session.add(artist1)
    db_session.add(artist2)
    db_session.flush()

    # Associer le genre aux artistes
    genre.artists.append(artist1)
    genre.artists.append(artist2)
    db_session.commit()

    # Vérifier les relations
    assert len(genre.artists) == 2
    assert artist1 in genre.artists
    assert artist2 in genre.artists
    assert genre in artist1.genres
    assert genre in artist2.genres

def test_genre_relationships_with_albums(db_session):
    """Test des relations entre genre et albums."""
    # Créer un artiste
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.flush()

    # Créer un genre
    genre = Genre(name="Pop")
    db_session.add(genre)
    db_session.flush()

    # Créer des albums
    album1 = Album(title="Album 1", album_artist_id=artist.id)
    album2 = Album(title="Album 2", album_artist_id=artist.id)
    db_session.add(album1)
    db_session.add(album2)
    db_session.flush()

    # Associer le genre aux albums
    genre.albums.append(album1)
    genre.albums.append(album2)
    db_session.commit()

    # Vérifier les relations
    assert len(genre.albums) == 2
    assert album1 in genre.albums
    assert album2 in genre.albums
    assert genre in album1.genres
    assert genre in album2.genres

def test_genre_relationships_with_tracks(db_session):
    """Test des relations entre genre et pistes."""
    # Créer un artiste et un album
    artist = Artist(name="Track Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Track Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer un genre
    genre = Genre(name="Electronic")
    db_session.add(genre)
    db_session.flush()

    # Créer des pistes
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id, album_id=album.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.flush()

    # Associer le genre aux pistes
    genre.tracks.append(track1)
    genre.tracks.append(track2)
    db_session.commit()

    # Vérifier les relations
    assert len(genre.tracks) == 2
    assert track1 in genre.tracks
    assert track2 in genre.tracks
    assert genre in track1.genres
    assert genre in track2.genres
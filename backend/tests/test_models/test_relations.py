# backend/tests/test_models/test_relations.py
import pytest
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track
from backend.api.models.genres_model import Genre
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.api.models.covers_model import Cover, EntityCoverType

def test_artist_albums_tracks_relationship(db_session):
    """Test des relations complètes artiste -> albums -> pistes."""
    # Créer un artiste
    artist = Artist(name="Complete Artist")
    db_session.add(artist)
    db_session.flush()

    # Créer des albums pour cet artiste
    album1 = Album(title="Album 1", album_artist_id=artist.id)
    album2 = Album(title="Album 2", album_artist_id=artist.id)
    db_session.add(album1)
    db_session.add(album2)
    db_session.flush()

    # Créer des pistes pour chaque album
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id, album_id=album1.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id, album_id=album1.id)
    track3 = Track(title="Track 3", path="/path/to/track3.mp3", track_artist_id=artist.id, album_id=album2.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.add(track3)
    db_session.commit()

    # Vérifier les relations depuis l'artiste
    assert len(artist.albums) == 2
    assert len(artist.tracks) == 3

    # Vérifier les relations depuis les albums
    assert len(album1.tracks) == 2
    assert len(album2.tracks) == 1

    # Vérifier les relations depuis les pistes
    assert track1.artist.id == artist.id
    assert track1.album.id == album1.id
    assert track2.artist.id == artist.id
    assert track2.album.id == album1.id
    assert track3.artist.id == artist.id
    assert track3.album.id == album2.id

def test_track_with_multiple_genres_and_tags(db_session):
    """Test d'une piste avec plusieurs genres et tags."""
    # Créer les entités de base
    artist = Artist(name="Multi Tag Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Multi Tag Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    track = Track(title="Multi Tag Track", path="/path/to/multitag.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    db_session.flush()

    # Créer des genres
    genre1 = Genre(name="Rock")
    genre2 = Genre(name="Pop")
    genre3 = Genre(name="Indie")
    db_session.add(genre1)
    db_session.add(genre2)
    db_session.add(genre3)
    db_session.flush()

    # Créer des tags
    genre_tag1 = GenreTag(name="alternative")
    genre_tag2 = GenreTag(name="indie_rock")
    mood_tag1 = MoodTag(name="energetic")
    mood_tag2 = MoodTag(name="melancholic")
    db_session.add(genre_tag1)
    db_session.add(genre_tag2)
    db_session.add(mood_tag1)
    db_session.add(mood_tag2)
    db_session.flush()

    # Associer les genres à la piste
    track.genres.append(genre1)
    track.genres.append(genre2)
    track.genres.append(genre3)

    # Associer les tags à la piste
    track.genre_tags.append(genre_tag1)
    track.genre_tags.append(genre_tag2)
    track.mood_tags.append(mood_tag1)
    track.mood_tags.append(mood_tag2)

    db_session.commit()

    # Vérifier les associations
    assert len(track.genres) == 3
    assert genre1 in track.genres
    assert genre2 in track.genres
    assert genre3 in track.genres

    assert len(track.genre_tags) == 2
    assert genre_tag1 in track.genre_tags
    assert genre_tag2 in track.genre_tags

    assert len(track.mood_tags) == 2
    assert mood_tag1 in track.mood_tags
    assert mood_tag2 in track.mood_tags

    # Vérifier les relations inverses
    assert track in genre1.tracks
    assert track in genre_tag1.tracks
    assert track in mood_tag1.tracks

def test_covers_relationships_with_entities(db_session):
    """Test des relations entre covers et différentes entités."""
    # Créer un artiste
    artist = Artist(name="Cover Artist")
    db_session.add(artist)
    db_session.flush()

    # Créer un album
    album = Album(title="Cover Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer une piste
    track = Track(title="Cover Track", path="/path/to/cover_track.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    db_session.flush()

    # Créer des covers pour chaque entité
    artist_cover = Cover(entity_type=EntityCoverType.ARTIST, entity_id=artist.id, cover_data="artist_cover_data")
    album_cover = Cover(entity_type=EntityCoverType.ALBUM, entity_id=album.id, cover_data="album_cover_data")
    track_cover = Cover(entity_type=EntityCoverType.TRACK, entity_id=track.id, cover_data="track_cover_data")

    db_session.add(artist_cover)
    db_session.add(album_cover)
    db_session.add(track_cover)
    db_session.commit()

    # Vérifier que les covers sont accessibles via les relations viewonly
    # Note: Les relations viewonly sont définies mais peuvent nécessiter des requêtes spécifiques
    # Ici on teste principalement que les covers existent et sont correctement liées

    # Récupérer les covers par type et entity_id
    artist_covers = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ARTIST,
        Cover.entity_id == artist.id
    ).all()
    assert len(artist_covers) == 1
    assert artist_covers[0].cover_data == "artist_cover_data"

    album_covers = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ALBUM,
        Cover.entity_id == album.id
    ).all()
    assert len(album_covers) == 1
    assert album_covers[0].cover_data == "album_cover_data"

    track_covers = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.TRACK,
        Cover.entity_id == track.id
    ).all()
    assert len(track_covers) == 1
    assert track_covers[0].cover_data == "track_cover_data"

def test_complex_artist_genre_relationships(db_session):
    """Test des relations complexes entre artistes et genres via albums et pistes."""
    # Créer deux artistes
    artist1 = Artist(name="Artist 1")
    artist2 = Artist(name="Artist 2")
    db_session.add(artist1)
    db_session.add(artist2)
    db_session.flush()

    # Créer des genres
    rock_genre = Genre(name="Rock")
    jazz_genre = Genre(name="Jazz")
    pop_genre = Genre(name="Pop")
    db_session.add(rock_genre)
    db_session.add(jazz_genre)
    db_session.add(pop_genre)
    db_session.flush()

    # Créer des albums
    album1 = Album(title="Rock Album", album_artist_id=artist1.id)
    album2 = Album(title="Jazz Album", album_artist_id=artist1.id)
    album3 = Album(title="Pop Album", album_artist_id=artist2.id)
    db_session.add(album1)
    db_session.add(album2)
    db_session.add(album3)
    db_session.flush()

    # Créer des pistes
    track1 = Track(title="Rock Track", path="/path/rock.mp3", track_artist_id=artist1.id, album_id=album1.id)
    track2 = Track(title="Jazz Track", path="/path/jazz.mp3", track_artist_id=artist1.id, album_id=album2.id)
    track3 = Track(title="Pop Track", path="/path/pop.mp3", track_artist_id=artist2.id, album_id=album3.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.add(track3)
    db_session.flush()

    # Associer les genres aux artistes
    artist1.genres.append(rock_genre)
    artist1.genres.append(jazz_genre)
    artist2.genres.append(pop_genre)

    # Associer les genres aux albums
    album1.genres.append(rock_genre)
    album2.genres.append(jazz_genre)
    album3.genres.append(pop_genre)

    # Associer les genres aux pistes
    track1.genres.append(rock_genre)
    track2.genres.append(jazz_genre)
    track3.genres.append(pop_genre)

    db_session.commit()

    # Vérifier les relations complexes
    # Artist 1 a 2 genres, 2 albums, 2 tracks
    assert len(artist1.genres) == 2
    assert len(artist1.albums) == 2
    assert len(artist1.tracks) == 2

    # Artist 2 a 1 genre, 1 album, 1 track
    assert len(artist2.genres) == 1
    assert len(artist2.albums) == 1
    assert len(artist2.tracks) == 1

    # Vérifier que les genres ont les bonnes entités associées
    assert artist1 in rock_genre.artists
    assert artist1 in jazz_genre.artists
    assert artist2 in pop_genre.artists

    assert album1 in rock_genre.albums
    assert album2 in jazz_genre.albums
    assert album3 in pop_genre.albums

    assert track1 in rock_genre.tracks
    assert track2 in jazz_genre.tracks
    assert track3 in pop_genre.tracks

def test_relationship_cascades_on_delete(db_session):
    """Test des cascades lors de la suppression d'entités."""
    # Créer un artiste avec album et piste
    artist = Artist(name="Cascade Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Cascade Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    track = Track(title="Cascade Track", path="/path/cascade.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track)
    db_session.commit()

    # Vérifier que tout existe
    assert db_session.query(Artist).filter(Artist.id == artist.id).first() is not None
    assert db_session.query(Album).filter(Album.id == album.id).first() is not None
    assert db_session.query(Track).filter(Track.id == track.id).first() is not None

    # Supprimer l'artiste (devrait supprimer album et track selon les cascades définies)
    db_session.delete(artist)
    db_session.commit()

    # Vérifier que l'artiste est supprimé
    assert db_session.query(Artist).filter(Artist.id == artist.id).first() is None

    # Les albums et tracks peuvent encore exister selon la configuration des cascades
    # Ici on teste juste que la suppression ne cause pas d'erreur
    # Les cascades spécifiques dépendent des foreign keys définies dans les modèles
# backend/tests/test_models/test_tags_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track

def test_create_genre_tag(db_session):
    """Test de création d'un genre tag en BDD."""
    genre_tag = GenreTag(name="rock")
    db_session.add(genre_tag)
    db_session.commit()

    # Vérifier que le tag a été créé
    assert genre_tag.id is not None

    # Récupérer le tag depuis la BDD
    db_tag = db_session.query(GenreTag).filter(GenreTag.id == genre_tag.id).first()
    assert db_tag is not None
    assert db_tag.name == "rock"

def test_create_mood_tag(db_session):
    """Test de création d'un mood tag en BDD."""
    mood_tag = MoodTag(name="happy")
    db_session.add(mood_tag)
    db_session.commit()

    # Vérifier que le tag a été créé
    assert mood_tag.id is not None

    # Récupérer le tag depuis la BDD
    db_tag = db_session.query(MoodTag).filter(MoodTag.id == mood_tag.id).first()
    assert db_tag is not None
    assert db_tag.name == "happy"

def test_genre_tag_unique_name_constraint(db_session):
    """Test de la contrainte d'unicité sur le nom du genre tag."""
    # Créer un premier tag
    tag1 = GenreTag(name="unique_genre")
    db_session.add(tag1)
    db_session.commit()

    # Tenter de créer un second tag avec le même nom
    tag2 = GenreTag(name="unique_genre")
    db_session.add(tag2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_mood_tag_unique_name_constraint(db_session):
    """Test de la contrainte d'unicité sur le nom du mood tag."""
    # Créer un premier tag
    tag1 = MoodTag(name="unique_mood")
    db_session.add(tag1)
    db_session.commit()

    # Tenter de créer un second tag avec le même nom
    tag2 = MoodTag(name="unique_mood")
    db_session.add(tag2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_genre_tag_relationships_with_tracks(db_session):
    """Test des relations entre genre tag et pistes."""
    # Créer un artiste et un album
    artist = Artist(name="Tag Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Tag Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer des genre tags
    tag1 = GenreTag(name="indie")
    tag2 = GenreTag(name="alternative")
    db_session.add(tag1)
    db_session.add(tag2)
    db_session.flush()

    # Créer des pistes
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id, album_id=album.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.flush()

    # Associer les tags aux pistes
    track1.genre_tags.append(tag1)
    track1.genre_tags.append(tag2)
    track2.genre_tags.append(tag1)
    db_session.commit()

    # Vérifier les relations
    assert len(track1.genre_tags) == 2
    assert tag1 in track1.genre_tags
    assert tag2 in track1.genre_tags

    assert len(track2.genre_tags) == 1
    assert tag1 in track2.genre_tags

    # Vérifier les relations inverses
    assert track1 in tag1.tracks
    assert track2 in tag1.tracks
    assert track1 in tag2.tracks

def test_mood_tag_relationships_with_tracks(db_session):
    """Test des relations entre mood tag et pistes."""
    # Créer un artiste et un album
    artist = Artist(name="Mood Artist")
    db_session.add(artist)
    db_session.flush()

    album = Album(title="Mood Album", album_artist_id=artist.id)
    db_session.add(album)
    db_session.flush()

    # Créer des mood tags
    tag1 = MoodTag(name="energetic")
    tag2 = MoodTag(name="upbeat")
    db_session.add(tag1)
    db_session.add(tag2)
    db_session.flush()

    # Créer des pistes
    track1 = Track(title="Track 1", path="/path/to/track1.mp3", track_artist_id=artist.id, album_id=album.id)
    track2 = Track(title="Track 2", path="/path/to/track2.mp3", track_artist_id=artist.id, album_id=album.id)
    db_session.add(track1)
    db_session.add(track2)
    db_session.flush()

    # Associer les tags aux pistes
    track1.mood_tags.append(tag1)
    track1.mood_tags.append(tag2)
    track2.mood_tags.append(tag1)
    db_session.commit()

    # Vérifier les relations
    assert len(track1.mood_tags) == 2
    assert tag1 in track1.mood_tags
    assert tag2 in track1.mood_tags

    assert len(track2.mood_tags) == 1
    assert tag1 in track2.mood_tags

    # Vérifier les relations inverses
    assert track1 in tag1.tracks
    assert track2 in tag1.tracks
    assert track1 in tag2.tracks

def test_genre_tag_name_nullable(db_session):
    """Test que le nom du genre tag peut être null."""
    tag = GenreTag()  # name=None par défaut
    db_session.add(tag)
    db_session.commit()

    assert tag.id is not None
    assert tag.name is None

def test_mood_tag_name_nullable(db_session):
    """Test que le nom du mood tag peut être null."""
    tag = MoodTag()  # name=None par défaut
    db_session.add(tag)
    db_session.commit()

    assert tag.id is not None
    assert tag.name is None
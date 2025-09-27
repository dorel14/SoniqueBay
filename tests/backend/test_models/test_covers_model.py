# backend/tests/test_models/test_covers_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from backend.api.models.covers_model import Cover, EntityCoverType

def test_create_cover_for_album(db_session):
    """Test de création d'une cover pour un album."""
    cover = Cover(
        entity_type=EntityCoverType.ALBUM,
        entity_id=1,
        cover_data="base64_album_cover_data",
        mime_type="image/jpeg",
        url="https://example.com/album_cover.jpg"
    )
    db_session.add(cover)
    db_session.commit()

    # Vérifier que la cover a été créée
    assert cover.id is not None

    # Récupérer la cover depuis la BDD
    db_cover = db_session.query(Cover).filter(Cover.id == cover.id).first()
    assert db_cover is not None
    assert db_cover.entity_type == EntityCoverType.ALBUM
    assert db_cover.entity_id == 1
    assert db_cover.cover_data == "base64_album_cover_data"
    assert db_cover.mime_type == "image/jpeg"
    assert db_cover.url == "https://example.com/album_cover.jpg"

def test_create_cover_for_artist(db_session):
    """Test de création d'une cover pour un artiste."""
    cover = Cover(
        entity_type=EntityCoverType.ARTIST,
        entity_id=2,
        cover_data="base64_artist_cover_data",
        mime_type="image/png"
    )
    db_session.add(cover)
    db_session.commit()

    assert cover.id is not None
    assert cover.entity_type == EntityCoverType.ARTIST
    assert cover.entity_id == 2

def test_create_cover_for_track(db_session):
    """Test de création d'une cover pour une piste."""
    cover = Cover(
        entity_type=EntityCoverType.TRACK,
        entity_id=3,
        url="https://example.com/track_cover.jpg"
    )
    db_session.add(cover)
    db_session.commit()

    assert cover.id is not None
    assert cover.entity_type == EntityCoverType.TRACK
    assert cover.entity_id == 3
    assert cover.cover_data is None  # Nullable
    assert cover.mime_type is None  # Nullable

def test_cover_unique_entity_constraint(db_session):
    """Test de la contrainte d'unicité sur entity_type + entity_id."""
    # Créer une première cover
    cover1 = Cover(
        entity_type=EntityCoverType.ALBUM,
        entity_id=1,
        cover_data="data1"
    )
    db_session.add(cover1)
    db_session.commit()

    # Tenter de créer une seconde cover pour la même entité
    cover2 = Cover(
        entity_type=EntityCoverType.ALBUM,
        entity_id=1,
        cover_data="data2"
    )
    db_session.add(cover2)

    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()

    # Rollback pour nettoyer la session
    db_session.rollback()

def test_cover_same_entity_id_different_types(db_session):
    """Test que le même entity_id peut avoir des covers pour différents types d'entités."""
    # Créer des covers pour le même entity_id mais différents types
    cover_album = Cover(
        entity_type=EntityCoverType.ALBUM,
        entity_id=5,
        cover_data="album_data"
    )
    cover_artist = Cover(
        entity_type=EntityCoverType.ARTIST,
        entity_id=5,
        cover_data="artist_data"
    )
    cover_track = Cover(
        entity_type=EntityCoverType.TRACK,
        entity_id=5,
        cover_data="track_data"
    )

    db_session.add(cover_album)
    db_session.add(cover_artist)
    db_session.add(cover_track)
    db_session.commit()

    # Vérifier que toutes les covers ont été créées
    assert cover_album.id is not None
    assert cover_artist.id is not None
    assert cover_track.id is not None

    # Vérifier qu'elles ont le même entity_id mais des types différents
    assert cover_album.entity_id == cover_artist.entity_id == cover_track.entity_id == 5
    assert cover_album.entity_type != cover_artist.entity_type
    assert cover_artist.entity_type != cover_track.entity_type
    assert cover_album.entity_type != cover_track.entity_type

def test_cover_nullable_fields(db_session):
    """Test que cover_data, mime_type et url peuvent être null."""
    cover = Cover(
        entity_type=EntityCoverType.ALBUM,
        entity_id=10
        # Tous les champs optionnels sont omis
    )
    db_session.add(cover)
    db_session.commit()

    assert cover.id is not None
    assert cover.cover_data is None
    assert cover.mime_type is None
    assert cover.url is None
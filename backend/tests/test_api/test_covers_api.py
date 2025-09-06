# backend/tests/test_api/test_covers_api.py
import pytest
from backend.api.models.covers_model import Cover, EntityCoverType
from backend.api.schemas.covers_schema import CoverCreate

@pytest.fixture
def create_test_cover(db_session):
    """Crée une cover de test."""
    counter = [0]  # Pour générer des IDs uniques
    def _create_cover(entity_type=EntityCoverType.ARTIST, entity_id=None, url=None, cover_data=None, mime_type=None):
        if entity_id is None:
            counter[0] += 1
            entity_id = counter[0]
        cover = Cover(
            entity_type=entity_type,
            entity_id=entity_id,
            url=url,
            cover_data=cover_data,
            mime_type=mime_type
        )
        db_session.add(cover)
        db_session.flush()
        return cover
    return _create_cover

def test_create_cover(client, db_session):
    """Test de création d'une nouvelle cover."""
    cover_data = {
        "entity_type": "artist",
        "entity_id": 1,
        "url": "/path/to/cover.jpg",
        "mime_type": "image/jpeg"
    }

    response = client.post("/api/covers/", json=cover_data)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "artist"
    assert data["entity_id"] == 1
    assert data["url"] == "C:/path/to/cover.jpg"  # Chemin absolu après validation
    assert data["mime_type"] == "image/jpeg"

    # Vérifier en base de données
    db_cover = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ARTIST,
        Cover.entity_id == 1
    ).first()
    assert db_cover is not None
    assert db_cover.url == "C:/path/to/cover.jpg"

def test_create_cover_duplicate_update(client, db_session, create_test_cover):
    """Test de création d'une cover existante (doit mettre à jour)."""
    # Créer une cover existante
    existing_cover = create_test_cover(entity_type=EntityCoverType.ALBUM, entity_id=2, url="/old/path.jpg")

    # Tenter de créer la même cover
    cover_data = {
        "entity_type": "album",
        "entity_id": 2,
        "url": "/new/path.jpg",
        "mime_type": "image/png"
    }

    response = client.post("/api/covers/", json=cover_data)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "C:/new/path.jpg"  # Chemin absolu

    # Vérifier que c'est la même entrée mise à jour
    db_cover = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ALBUM,
        Cover.entity_id == 2
    ).first()
    assert db_cover.url == "C:/new/path.jpg"

def test_get_cover(client, db_session, create_test_cover):
    """Test de récupération d'une cover existante."""
    cover = create_test_cover(entity_type=EntityCoverType.TRACK, entity_id=3, url="/track/cover.png")

    response = client.get("/api/covers/track/3")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "track"
    assert data["entity_id"] == 3
    assert data["url"] == "C:/track/cover.png"  # Chemin absolu

def test_get_cover_not_found(client, db_session):
    """Test de récupération d'une cover inexistante."""
    response = client.get("/api/covers/artist/999")
    assert response.status_code == 404

def test_get_cover_invalid_type(client, db_session):
    """Test de récupération avec type d'entité invalide."""
    response = client.get("/api/covers/invalid/1")
    assert response.status_code == 400

def test_get_covers_empty(client, db_session):
    """Test de récupération de la liste vide de covers."""
    response = client.get("/api/covers/")
    assert response.status_code == 200
    data = response.json()
    assert data == []

def test_get_covers_with_data(client, db_session, create_test_cover):
    """Test de récupération de la liste de covers avec données."""
    cover1 = create_test_cover(entity_type=EntityCoverType.ARTIST, entity_id=1)
    cover2 = create_test_cover(entity_type=EntityCoverType.ALBUM, entity_id=2)
    cover3 = create_test_cover(entity_type=EntityCoverType.TRACK, entity_id=3)

    response = client.get("/api/covers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

def test_get_covers_filtered(client, db_session, create_test_cover):
    """Test de récupération de covers filtrées par type."""
    cover1 = create_test_cover(entity_type=EntityCoverType.ARTIST, entity_id=1)
    cover2 = create_test_cover(entity_type=EntityCoverType.ALBUM, entity_id=2)
    cover3 = create_test_cover(entity_type=EntityCoverType.ARTIST, entity_id=3)

    response = client.get("/api/covers/?entity_type=artist")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for cover in data:
        assert cover["entity_type"] == "artist"

def test_update_cover_existing(client, db_session, create_test_cover):
    """Test de mise à jour d'une cover existante."""
    cover = create_test_cover(entity_type=EntityCoverType.ALBUM, entity_id=4, url="/old/album.jpg")

    update_data = {
        "entity_type": "album",
        "entity_id": 4,
        "url": "/new/album.jpg",
        "mime_type": "image/jpeg"
    }

    response = client.put("/api/covers/album/4", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "C:/new/album.jpg"  # Chemin absolu

    # Vérifier en DB
    db_cover = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ALBUM,
        Cover.entity_id == 4
    ).first()
    assert db_cover.url == "C:/new/album.jpg"

def test_update_cover_not_existing(client, db_session):
    """Test de mise à jour d'une cover inexistante (doit créer)."""
    update_data = {
        "entity_type": "track",
        "entity_id": 5,
        "url": "/new/track.jpg"
    }

    response = client.put("/api/covers/track/5", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "C:/new/track.jpg"  # Chemin absolu

    # Vérifier création en DB
    db_cover = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.TRACK,
        Cover.entity_id == 5
    ).first()
    assert db_cover is not None

def test_update_cover_invalid_type(client, db_session):
    """Test de mise à jour avec type invalide."""
    update_data = {
        "entity_type": "invalid",
        "entity_id": 1
    }

    response = client.put("/api/covers/invalid/1", json=update_data)
    assert response.status_code == 422  # Pydantic validation error

def test_delete_cover(client, db_session, create_test_cover):
    """Test de suppression d'une cover."""
    cover = create_test_cover(entity_type=EntityCoverType.ARTIST, entity_id=6)

    response = client.delete("/api/covers/artist/6")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Vérifier suppression en DB
    db_cover = db_session.query(Cover).filter(
        Cover.entity_type == EntityCoverType.ARTIST,
        Cover.entity_id == 6
    ).first()
    assert db_cover is None

def test_delete_cover_not_found(client, db_session):
    """Test de suppression d'une cover inexistante."""
    response = client.delete("/api/covers/artist/999")
    assert response.status_code == 404

def test_get_cover_schema(client):
    """Test de récupération du schéma CoverCreate."""
    response = client.get("/api/covers/schema")
    assert response.status_code == 200
    schema = response.json()
    assert "properties" in schema
    assert "entity_type" in schema["properties"]

def test_get_cover_types(client):
    """Test de récupération des types de couverture disponibles."""
    response = client.get("/api/covers/types")
    assert response.status_code == 200
    types = response.json()
    assert "artist" in types
    assert "album" in types
    assert "track" in types
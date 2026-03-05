"""
Tests unitaires pour la méthode create_albums_batch d'AlbumService.

Ce module teste la création d'albums en batch avec la logique get_or_create.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from backend.api.services.album_service import AlbumService
from backend.api.schemas.albums_schema import AlbumCreate


@pytest.fixture
def mock_db():
    """Fixture pour une session DB mockée."""
    return AsyncMock()


@pytest.fixture
def album_service(mock_db):
    """Fixture pour AlbumService avec DB mockée."""
    return AlbumService(mock_db)


@pytest.fixture
def sample_albums_data() -> List[AlbumCreate]:
    """Fixture pour des données d'albums de test."""
    return [
        AlbumCreate(
            title="Test Album 1",
            album_artist_id=1,
            release_year="2023",
            musicbrainz_albumid="mb-123"
        ),
        AlbumCreate(
            title="Test Album 2",
            album_artist_id=1,
            release_year="2024",
            musicbrainz_albumid="mb-456"
        ),
    ]


@pytest.mark.asyncio
async def test_create_albums_batch_success(album_service, sample_albums_data):
    """
    Test que create_albums_batch crée correctement plusieurs albums.
    
    Vérifie que la méthode retourne une liste de dictionnaires
    avec les bonnes données.
    """
    # Arrange
    mock_album_1 = MagicMock()
    mock_album_1.id = 1
    mock_album_1.title = "Test Album 1"
    mock_album_1.album_artist_id = 1
    mock_album_1.release_year = "2023"
    mock_album_1.musicbrainz_albumid = "mb-123"
    
    mock_album_2 = MagicMock()
    mock_album_2.id = 2
    mock_album_2.title = "Test Album 2"
    mock_album_2.album_artist_id = 1
    mock_album_2.release_year = "2024"
    mock_album_2.musicbrainz_albumid = "mb-456"
    
    # Mock get_or_create_album pour retourner les albums simulés
    with patch.object(
        album_service, 
        'get_or_create_album', 
        side_effect=[mock_album_1, mock_album_2]
    ) as mock_get_or_create:
        
        # Act
        results = await album_service.create_albums_batch(sample_albums_data)
        
        # Assert
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["title"] == "Test Album 1"
        assert results[0]["album_artist_id"] == 1
        assert results[0]["release_year"] == "2023"
        assert results[0]["musicbrainz_albumid"] == "mb-123"
        
        assert results[1]["id"] == 2
        assert results[1]["title"] == "Test Album 2"
        
        # Vérifier que get_or_create_album a été appelé pour chaque album
        assert mock_get_or_create.call_count == 2
        mock_get_or_create.assert_any_call(
            title="Test Album 1",
            artist_id=1,
            release_year="2023",
            cover_url=None
        )
        mock_get_or_create.assert_any_call(
            title="Test Album 2",
            artist_id=1,
            release_year="2024",
            cover_url=None
        )


@pytest.mark.asyncio
async def test_create_albums_batch_empty_list(album_service):
    """
    Test que create_albums_batch gère correctement une liste vide.
    """
    # Act
    results = await album_service.create_albums_batch([])
    
    # Assert
    assert results == []
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_create_albums_batch_get_existing(album_service):
    """
    Test que create_albums_batch récupère un album existant si trouvé.
    
    Vérifie la logique get_or_create : si l'album existe déjà,
    il doit être retourné sans création.
    """
    # Arrange
    existing_album = MagicMock()
    existing_album.id = 42
    existing_album.title = "Existing Album"
    existing_album.album_artist_id = 5
    existing_album.release_year = "2020"
    existing_album.musicbrainz_albumid = "existing-mb-id"
    
    albums_data = [
        AlbumCreate(
            title="Existing Album",
            album_artist_id=5,
            release_year="2020",
            musicbrainz_albumid="existing-mb-id"
        )
    ]
    
    with patch.object(
        album_service, 
        'get_or_create_album', 
        return_value=existing_album
    ) as mock_get_or_create:
        
        # Act
        results = await album_service.create_albums_batch(albums_data)
        
        # Assert
        assert len(results) == 1
        assert results[0]["id"] == 42
        assert results[0]["title"] == "Existing Album"
        
        # Vérifier que get_or_create_album a été appelé
        mock_get_or_create.assert_called_once_with(
            title="Existing Album",
            artist_id=5,
            release_year="2020",
            cover_url=None
        )


@pytest.mark.asyncio
async def test_create_albums_batch_without_musicbrainz_id(album_service):
    """
    Test que create_albums_batch fonctionne sans musicbrainz_albumid.
    """
    # Arrange
    album_data = [
        AlbumCreate(
            title="Simple Album",
            album_artist_id=1,
            release_year="2023"
            # Pas de musicbrainz_albumid
        )
    ]
    
    mock_album = MagicMock()
    mock_album.id = 1
    mock_album.title = "Simple Album"
    mock_album.album_artist_id = 1
    mock_album.release_year = "2023"
    # Simuler un album sans musicbrainz_albumid
    del mock_album.musicbrainz_albumid
    
    with patch.object(
        album_service, 
        'get_or_create_album', 
        return_value=mock_album
    ):
        
        # Act
        results = await album_service.create_albums_batch(album_data)
        
        # Assert
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["musicbrainz_albumid"] is None


@pytest.mark.asyncio
async def test_create_albums_batch_preserves_order(album_service):
    """
    Test que create_albums_batch préserve l'ordre des albums en entrée.
    """
    # Arrange
    albums_data = [
        AlbumCreate(title="First", album_artist_id=1),
        AlbumCreate(title="Second", album_artist_id=1),
        AlbumCreate(title="Third", album_artist_id=1),
    ]
    
    mock_albums = [
        MagicMock(id=1, title="First", album_artist_id=1, release_year=None),
        MagicMock(id=2, title="Second", album_artist_id=1, release_year=None),
        MagicMock(id=3, title="Third", album_artist_id=1, release_year=None),
    ]
    
    with patch.object(
        album_service, 
        'get_or_create_album', 
        side_effect=mock_albums
    ):
        
        # Act
        results = await album_service.create_albums_batch(albums_data)
        
        # Assert
        assert len(results) == 3
        assert results[0]["title"] == "First"
        assert results[1]["title"] == "Second"
        assert results[2]["title"] == "Third"

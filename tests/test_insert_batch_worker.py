"""Test pour valider le fix de l'insertion des tracks avec des artistes manquants."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend_worker.workers.insert.insert_batch_worker import _insert_batch_direct_async


@pytest.mark.asyncio
async def test_insert_batch_with_missing_artist():
    """Test que les tracks sont insérées même si l'artiste est manquant."""
    
    # Données de test
    insertion_data = {
        'artists': [],
        'albums': [],
        'tracks': [
            {
                'title': 'Test Track',
                'artist_name': 'foreigner',  # Artiste manquant
                'album_title': 'Test Album',
                'path': '/test/path.mp3'
            }
        ]
    }
    
    # Mock des dépendances
    mock_client = AsyncMock()
    mock_task = MagicMock()
    mock_task.request.id = 'test-task-id'
    
    # Mock de create_or_get_artists_batch pour simuler un artiste manquant
    with patch('backend_worker.workers.insert.insert_batch_worker.create_or_get_artists_batch', new_callable=AsyncMock) as mock_create_artists:
        mock_create_artists.return_value = {}
        
        # Mock de create_or_get_albums_batch
        with patch('backend_worker.workers.insert.insert_batch_worker.create_or_get_albums_batch', new_callable=AsyncMock) as mock_create_albums:
            mock_create_albums.return_value = {}
            
            # Mock de create_or_update_tracks_batch
            with patch('backend_worker.workers.insert.insert_batch_worker.create_or_update_tracks_batch', new_callable=AsyncMock) as mock_create_tracks:
                mock_create_tracks.return_value = [{'id': 1, 'title': 'Test Track', 'path': '/test/path.mp3'}]
                
                # Exécuter la fonction
                result = await _insert_batch_direct_async(mock_task, insertion_data)
                
                # Vérifier que l'artiste a été créé
                assert mock_create_artists.call_count == 1
                
                # Vérifier que la track a été insérée
                assert result['tracks'] == 1
                assert mock_create_tracks.call_count == 1


@pytest.mark.asyncio
async def test_insert_batch_with_unknown_artist():
    """Test que les tracks sont insérées avec un artiste par défaut si la création échoue."""
    
    # Données de test
    insertion_data = {
        'artists': [],
        'albums': [],
        'tracks': [
            {
                'title': 'Test Track',
                'artist_name': 'unknown_artist',  # Artiste inconnu
                'album_title': 'Test Album',
                'path': '/test/path.mp3'
            }
        ]
    }
    
    # Mock des dépendances
    mock_task = MagicMock()
    mock_task.request.id = 'test-task-id'
    
    # Mock de create_or_get_artists_batch pour simuler un échec de création
    with patch('backend_worker.workers.insert.insert_batch_worker.create_or_get_artists_batch', new_callable=AsyncMock) as mock_create_artists:
        mock_create_artists.return_value = {}
        
        # Mock de create_or_get_albums_batch
        with patch('backend_worker.workers.insert.insert_batch_worker.create_or_get_albums_batch', new_callable=AsyncMock) as mock_create_albums:
            mock_create_albums.return_value = {}
            
            # Mock de create_or_update_tracks_batch
            with patch('backend_worker.workers.insert.insert_batch_worker.create_or_update_tracks_batch', new_callable=AsyncMock) as mock_create_tracks:
                mock_create_tracks.return_value = [{'id': 1, 'title': 'Test Track', 'path': '/test/path.mp3'}]
                
                # Exécuter la fonction
                result = await _insert_batch_direct_async(mock_task, insertion_data)
                
                # Vérifier que l'artiste par défaut a été créé
                assert mock_create_artists.call_count == 2  # Une tentative pour l'artiste inconnu, une pour l'artiste par défaut
                
                # Vérifier que la track a été insérée
                assert result['tracks'] == 1
                assert mock_create_tracks.call_count == 1
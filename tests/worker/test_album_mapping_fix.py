"""
Test pour vérifier la correction du bug album_mapping avec types mixtes.
"""
import pytest
import asyncio
from unittest.mock import patch
from backend_worker.background_tasks.worker_metadata import _resolve_albums_references


@pytest.mark.asyncio
async def test_resolve_albums_references_with_mixed_types():
    """
    Test que la fonction _resolve_albums_references gère correctement
    les cas où album_mapping contient des entiers et des strings.
    """
    # Données de test avec artiste et album
    artist_mapping = {
        "test artist": 123  # Entier comme ID d'artiste
    }
    
    albums_data = [
        {
            'title': 'Test Album',
            'album_artist_name': 'Test Artist',
            'release_year': 2023
        }
    ]
    
    # Simuler la réponse de recherche d'albums existants
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search:
        # Simuler un album existant (avec ID entier)
        mock_search.return_value = {
            'test album_123': {
                'id': 456,  # ID entier de l'album existant
                'title': 'Test Album'
            }
        }
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            mock_create.return_value = []
            
            # Tester la fonction
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            # Vérifications
            assert 'album_mapping' in result
            assert 'albums' in result
            
            album_mapping = result['album_mapping']
            result['albums']
            
            # Vérifier que la clé de l'album existe
            expected_key = 'test album_123'
            assert expected_key in album_mapping
            
            # Vérifier que la valeur est l'ID entier (album existant)
            assert album_mapping[expected_key] == 456
            assert isinstance(album_mapping[expected_key], int)
            
            # Vérifier qu'il n'y a pas d'erreur 'int' object has no attribute 'startswith'
            print(f"✓ Test réussi: album_mapping = {album_mapping}")


@pytest.mark.asyncio
async def test_resolve_albums_references_with_new_albums():
    """
    Test que la fonction gère correctement les nouveaux albums à créer.
    """
    artist_mapping = {
        "new artist": 789
    }
    
    albums_data = [
        {
            'title': 'New Album',
            'album_artist_name': 'New Artist',
            'release_year': 2024
        }
    ]
    
    # Simuler aucun album existant
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search:
        mock_search.return_value = {}  # Aucun album existant
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            # Simuler création d'un nouvel album
            mock_create.return_value = [
                {
                    'id': 999,
                    'title': 'New Album'
                }
            ]
            
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            album_mapping = result['album_mapping']
            result['albums']
            
            # Vérifier la clé
            expected_key = 'new album_789'
            assert expected_key in album_mapping
            
            # Après création, l'ID doit être un entier
            final_id = album_mapping[expected_key]
            assert isinstance(final_id, int)
            assert final_id == 999
            
            print(f"✓ Test nouveau album réussi: final_id = {final_id}")


if __name__ == "__main__":
    # Exécution des tests
    asyncio.run(test_resolve_albums_references_with_mixed_types())
    asyncio.run(test_resolve_albums_references_with_new_albums())
    print("✅ Tous les tests de correction ont réussi!")
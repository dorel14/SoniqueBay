"""
Test pour vérifier la correction du bug des IDs temporaires d'albums.

Ce test valide que les IDs temporaires TEMP_ALBUM_X sont correctement remplacés
par les vrais IDs d'albums avant d'être envoyés à l'API, empêchant les erreurs 422.
"""

import pytest
import asyncio
from unittest.mock import patch
from backend_worker.background_tasks.worker_metadata import _resolve_albums_references


class TestAlbumTempIDFix:
    """Tests pour la correction du bug TEMP_ALBUM."""

    @pytest.mark.asyncio
    async def test_album_temp_id_replacement_basic(self):
        """Test basique du remplacement des IDs temporaires d'albums."""
        # Données de test
        albums_data = [
            {
                'title': 'Test Album 1',
                'album_artist_name': 'Test Artist',
                'release_year': '2023',
                'musicbrainz_albumid': 'test-mbid-1'
            },
            {
                'title': 'Test Album 2', 
                'album_artist_name': 'Test Artist',
                'release_year': '2023',
                'musicbrainz_albumid': 'test-mbid-2'
            }
        ]
        
        # Artist mapping simulé
        artist_mapping = {
            'test artist': 1  # ID artiste réel
        }
        
        # Mock des fonctions de recherche et création
        with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search, \
             patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            
            # Configuration des mocks
            mock_search.return_value = {}  # Aucun album existant
            
            # Albums simulés créés par l'API
            created_albums = [
                {'id': 101, 'title': 'Test Album 1'},
                {'id': 102, 'title': 'Test Album 2'}
            ]
            mock_create.return_value = created_albums
            
            # Exécution
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            # Vérifications
            assert 'albums' in result
            assert len(result['albums']) == 2
            
            # Vérifier que les IDs temporaires ont été remplacés
            for album in result['albums']:
                assert 'id' in album
                assert isinstance(album['id'], int)  # ID réel, pas string temporaire
                # Vérifier que l'ID n'est PAS une chaîne temporaire
                if isinstance(album['id'], str):
                    assert not album['id'].startswith('TEMP_ALBUM')  # Pas d'ID temporaire
            
            # Vérifier que les IDs correspondent aux albums créés
            assert result['albums'][0]['id'] == 101
            assert result['albums'][1]['id'] == 102
    
    @pytest.mark.asyncio
    async def test_album_temp_id_with_existing_albums(self):
        """Test du remplacement avec des albums existants."""
        # Données de test
        albums_data = [
            {
                'title': 'Existing Album',
                'album_artist_name': 'Test Artist',
                'release_year': '2023'
            },
            {
                'title': 'New Album',
                'album_artist_name': 'Test Artist', 
                'release_year': '2023'
            }
        ]
        
        artist_mapping = {
            'test artist': 1
        }
        
        with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search, \
             patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            
            # Un album existe déjà
            mock_search.return_value = {
                'existing album_1': {'id': 201, 'title': 'Existing Album'}
            }
            
            # Un seul nouvel album à créer
            created_albums = [
                {'id': 202, 'title': 'New Album'}
            ]
            mock_create.return_value = created_albums
            
            # Exécution
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            # Vérifications
            assert len(result['albums']) == 2
            
            # L'album existant garde son ID
            existing_album = next(a for a in result['albums'] if a['title'] == 'Existing Album')
            assert existing_album['id'] == 201
            
            # Le nouvel album a un ID réel
            new_album = next(a for a in result['albums'] if a['title'] == 'New Album')
            assert new_album['id'] == 202
            assert not str(new_album['id']).startswith('TEMP')
    
    @pytest.mark.asyncio 
    async def test_album_temp_id_error_cases(self):
        """Test des cas d'erreur dans le remplacement des IDs."""
        albums_data = [
            {
                'title': 'Test Album',
                'album_artist_name': 'Unknown Artist',  # Artiste non résolu
                'release_year': '2023'
            }
        ]
        
        artist_mapping = {}  # Aucun artiste résolu
        
        # Doit gérer gracieusement les artistes non résolus
        result = await _resolve_albums_references(albums_data, artist_mapping)
        
        # Aucun album ne devrait être résolu sans artiste
        assert len(result['albums']) == 0
    
    @pytest.mark.asyncio
    async def test_album_mapping_consistency(self):
        """Test de la cohérence du mapping des albums."""
        albums_data = [
            {
                'title': 'Album 1',
                'album_artist_name': 'Artist 1',
                'release_year': '2023'
            },
            {
                'title': 'Album 2', 
                'album_artist_name': 'Artist 1',
                'release_year': '2023'
            }
        ]
        
        artist_mapping = {
            'artist 1': 1
        }
        
        with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search, \
             patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            
            mock_search.return_value = {}
            created_albums = [
                {'id': 301, 'title': 'Album 1'},
                {'id': 302, 'title': 'Album 2'}
            ]
            mock_create.return_value = created_albums
            
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            # Vérifier la cohérence du mapping
            assert result['albums'][0]['album_artist_id'] == 1
            assert result['albums'][1]['album_artist_id'] == 1
            
            # Vérifier qu'il n'y a pas de contamination des IDs
            assert result['albums'][0]['id'] != result['albums'][1]['id']


if __name__ == "__main__":
    # Test simple pour validation rapide
    asyncio.run(TestAlbumTempIDFix().test_album_temp_id_replacement_basic())
    print("✅ Test de base passé")
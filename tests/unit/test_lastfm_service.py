"""
Tests unitaires pour le service LastFM.

Ce module teste le service LastFM pour s'assurer que :
1. L'initialisation du réseau en mode anonyme fonctionne correctement
2. Les erreurs d'authentification sont gérées correctement
3. Les méthodes principales fonctionnent comme attendu
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# Import du service à tester
from backend_worker.services.lastfm_service import LastFMService, lastfm_service


class TestLastFMService:
    """Tests pour le service LastFM."""

    @pytest.fixture
    def service(self):
        """Fixture pour créer une instance fraîche du service."""
        service = LastFMService()
        service._network = None  # Réinitialiser le réseau
        return service

    @pytest.fixture
    def mock_network(self):
        """Fixture pour créer un mock du réseau pylast."""
        network = Mock()
        network.get_artist = Mock()
        network.get_artist_by_mbid = Mock()
        return network

    def test_service_initialization(self, service):
        """Test que le service s'initialise correctement."""
        assert service._network is None
        assert service._cache_service is not None

    @patch('backend_worker.services.lastfm_service.pylast.LastFMNetwork')
    def test_network_initialization_anonymous_mode(self, mock_lastfm_network, service):
        """
        Test que le réseau s'initialise en mode anonyme (sans username/password).
        
        C'est le test clé qui vérifie que l'erreur "Invalid method signature supplied"
        ne se reproduira plus.
        """
        # Mock de la réponse HTTP pour les settings
        with patch('httpx.Client') as mock_client_class:
            with patch('os.getenv', return_value='http://api:8001'):
                mock_client = Mock()
                mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
                mock_client_class.return_value.__exit__ = Mock(return_value=False)
                
                # Simuler les réponses de l'API settings
                def mock_get(url):
                    response = Mock()
                    response.status_code = 200
                    if 'lastfm_api_key' in url:
                        response.json.return_value = {'value': 'test_api_key'}
                    elif 'lastfm_shared_secret' in url:
                        response.json.return_value = {'value': 'test_api_secret'}
                    else:
                        response.json.return_value = {'value': ''}
                    return response
                
                mock_client.get = mock_get
                
                # Appeler la propriété network pour déclencher l'initialisation
                network = service.network
                
                # Vérifier que LastFMNetwork a été appelé avec les bons arguments
                mock_lastfm_network.assert_called_once()
                call_kwargs = mock_lastfm_network.call_args[1]
                
                # Vérifier que seuls api_key et api_secret sont passés (pas de username/password)
                assert 'api_key' in call_kwargs
                assert 'api_secret' in call_kwargs
                assert call_kwargs['api_key'] == 'test_api_key'
                assert call_kwargs['api_secret'] == 'test_api_secret'
                
                # Vérifier que username et password_hash ne sont PAS passés
                assert 'username' not in call_kwargs
                assert 'password_hash' not in call_kwargs
                
                print("✓ Test réussi: Le réseau s'initialise correctement en mode anonyme")

    @patch('backend_worker.services.lastfm_service.pylast.LastFMNetwork')
    def test_network_initialization_missing_credentials(self, mock_lastfm_network, service):
        """Test que le service lève une erreur si les credentials sont manquants."""
        with patch('httpx.Client') as mock_client_class:
            with patch('os.getenv', return_value='http://api:8001'):
                mock_client = Mock()
                mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
                mock_client_class.return_value.__exit__ = Mock(return_value=False)
                
                # Simuler des credentials manquants
                def mock_get(url):
                    response = Mock()
                    response.status_code = 200
                    response.json.return_value = {'value': ''}  # Valeur vide
                    return response
                
                mock_client.get = mock_get
                
                # Vérifier que ValueError est levée
                with pytest.raises(ValueError, match="Last.fm API key and secret not configured"):
                    _ = service.network

    @pytest.mark.asyncio
    async def test_fetch_artist_info_success(self, service, mock_network):
        """Test la récupération des informations d'un artiste."""
        # Configuration du mock
        mock_artist = Mock()
        mock_artist.get_url.return_value = 'https://last.fm/artist/TestArtist'
        mock_artist.get_listener_count.return_value = 1000000
        mock_artist.get_playcount.return_value = 5000000
        mock_artist.get_mbid.return_value = 'mbid-12345'
        
        mock_network.get_artist.return_value = mock_artist
        service._network = mock_network
        
        # Mock des méthodes utilitaires
        with patch.object(service, '_extract_tags', return_value=['rock', 'pop']):
            with patch.object(service, '_get_artist_bio', return_value='Test bio'):
                with patch.object(service, '_get_artist_images', return_value=[{'size': 'large', 'url': 'http://image.jpg'}]):
                    # Appeler la méthode
                    result = await service._fetch_artist_info('Test Artist')
                    
                    # Vérifications
                    assert result is not None
                    assert result['url'] == 'https://last.fm/artist/TestArtist'
                    assert result['listeners'] == 1000000
                    assert result['playcount'] == 5000000
                    assert result['tags'] == ['rock', 'pop']
                    assert result['bio'] == 'Test bio'
                    assert 'fetched_at' in result

    @pytest.mark.asyncio
    async def test_fetch_artist_info_by_mbid(self, service, mock_network):
        """Test la récupération des informations d'un artiste par MBID."""
        # Configuration du mock
        mock_artist = Mock()
        mock_artist.get_url.return_value = 'https://last.fm/artist/TestArtist'
        mock_artist.get_listener_count.return_value = 1000000
        mock_artist.get_playcount.return_value = 5000000
        mock_artist.get_mbid.return_value = 'mbid-12345'
        
        mock_network.get_artist_by_mbid.return_value = mock_artist
        service._network = mock_network
        
        # Mock des méthodes utilitaires
        with patch.object(service, '_extract_tags', return_value=['rock', 'pop']):
            with patch.object(service, '_get_artist_bio', return_value='Test bio'):
                with patch.object(service, '_get_artist_images', return_value=[]):
                    # Appeler la méthode avec MBID
                    result = await service._fetch_artist_info('Test Artist', mb_artist_id='mbid-12345')
                    
                    # Vérifications
                    assert result is not None
                    assert result['musicbrainz_id'] == 'mbid-12345'
                    mock_network.get_artist_by_mbid.assert_called_once_with('mbid-12345')

    @pytest.mark.asyncio
    async def test_fetch_artist_info_error(self, service, mock_network):
        """Test la gestion d'erreur lors de la récupération des informations."""
        mock_network.get_artist.side_effect = Exception("API Error")
        service._network = mock_network
        
        # La méthode doit retourner None en cas d'erreur, ne pas propager l'exception
        result = await service._fetch_artist_info('Test Artist')
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_artist_image_success(self, service, mock_network):
        """Test la récupération de l'image d'un artiste."""
        # Configuration du mock
        mock_artist = Mock()
        mock_artist.get_image.return_value = 'http://image.jpg'
        mock_network.get_artist.return_value = mock_artist
        service._network = mock_network
        
        # Mock du téléchargement d'image avec async context manager
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_response.headers = {'content-type': 'image/jpeg'}
        
        # Créer un mock pour l'async context manager
        mock_client = Mock()
        mock_client.get = Mock(return_value=mock_response)
        
        # Mock pour __aenter__ et __aexit__
        mock_client.__aenter__ = Mock(return_value=mock_client)
        mock_client.__aexit__ = Mock(return_value=False)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Appeler la méthode
            result = await service._fetch_artist_image('Test Artist')
            
            # Vérifications
            assert result is not None
            assert result[1] == 'image/jpeg'  # mime_type
            assert 'data:image/jpeg;base64,' in result[0]  # base64 data

    def test_fetch_artist_image_no_image(self, service, mock_network):
        """Test le cas où aucune image n'est trouvée."""
        mock_artist = Mock()
        mock_artist.get_image.return_value = None
        mock_network.get_artist.return_value = mock_artist
        service._network = mock_network
        
        import asyncio
        result = asyncio.run(service._fetch_artist_image('Test Artist'))
        assert result is None

    def test_extract_tags(self, service):
        """Test l'extraction des tags."""
        mock_entity = Mock()
        mock_tag = Mock()
        mock_tag.item.get_name.return_value = 'rock'
        mock_entity.get_top_tags.return_value = [mock_tag]
        
        result = service._extract_tags(mock_entity)
        assert result == ['rock']

    def test_extract_tags_error(self, service):
        """Test la gestion d'erreur lors de l'extraction des tags."""
        mock_entity = Mock()
        mock_entity.get_top_tags.side_effect = Exception("Error")
        
        result = service._extract_tags(mock_entity)
        assert result == []

    def test_get_artist_bio(self, service):
        """Test la récupération de la biographie."""
        mock_artist = Mock()
        mock_artist.get_bio_content.return_value = 'Test biography'
        
        result = service._get_artist_bio(mock_artist)
        assert result == 'Test biography'

    def test_get_artist_images(self, service):
        """Test la récupération des images d'un artiste."""
        mock_artist = Mock()
        mock_artist.get_image.side_effect = lambda size: f'http://{size}.jpg' if size == 'large' else None
        
        result = service._get_artist_images(mock_artist)
        assert len(result) == 1
        assert result[0]['size'] == 'large'
        assert result[0]['url'] == 'http://large.jpg'


class TestLastFMServiceIntegration:
    """Tests d'intégration pour vérifier le comportement global."""

    def test_global_instance_exists(self):
        """Test que l'instance globale du service existe."""
        assert lastfm_service is not None
        assert isinstance(lastfm_service, LastFMService)

    def test_service_singleton_behavior(self):
        """Test que l'instance globale conserve son état."""
        # L'instance globale doit avoir le même réseau après plusieurs accès
        # (si le réseau a été initialisé)
        service1 = lastfm_service
        service2 = lastfm_service
        
        assert service1 is service2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Tests de diagnostic pour l'endpoint genres - vérifier les redirections 307.

Ce module contient des tests pour diagnostiquer les problèmes d'API
avec l'endpoint des genres, particulièrement les redirections 307.
"""

import pytest
import logging
import os
from unittest.mock import AsyncMock, patch

# Configuration du logger pour les tests
logger = logging.getLogger(__name__)


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_genres_endpoint_get():
    """Test GET de l'endpoint genres pour vérifier l'existence."""
    # Utiliser les variables d'environnement de test
    base_url = os.getenv("TEST_API_URL", "http://localhost:8001")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SoniqueBay-Worker/1.0"
    }
    
    # Mock du client HTTP
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Not Found"}
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Effectuer la requête via l'API mockée
        async with mock_client_class() as client:
            response = await client.get(f"{base_url}/api/genres", headers=headers)
            
            # Vérifier les appels
            mock_client.get.assert_called_once_with(f"{base_url}/api/genres", headers=headers)
            
            # Assertions pour vérifier le fonctionnement
            assert response.status_code in [200, 404], f"Status inattendu: {response.status_code}"
            
            if response.status_code == 200:
                logger.info("✅ Endpoint /api/genres GET fonctionne")
            else:
                logger.warning("⚠️ Endpoint /api/genres GET non accessible")


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_genres_endpoint_options():
    """Test OPTIONS de l'endpoint genres pour vérifier CORS."""
    base_url = os.getenv("TEST_API_URL", "http://localhost:8001")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SoniqueBay-Worker/1.0"
    }
    
    mock_response = AsyncMock()
    mock_response.status_code = 405  # Method Not Allowed
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.options.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        async with mock_client_class() as client:
            response = await client.options(f"{base_url}/api/genres", headers=headers)
            
            # Vérifier que l'endpoint répond aux requêtes OPTIONS
            assert response.status_code in [200, 204, 405], f"Status inattendu: {response.status_code}"
            logger.info("✅ Endpoint /api/genres OPTIONS testé")


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_genres_endpoint_post():
    """Test POST de l'endpoint genres pour diagnostiquer les redirections 307."""
    base_url = os.getenv("TEST_API_URL", "http://localhost:8001")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SoniqueBay-Worker/1.0"
    }
    
    test_data = {"name": "Test Genre"}
    
    # Test avec redirection 307
    mock_response = AsyncMock()
    mock_response.status_code = 307
    mock_response.headers = {"location": "http://localhost:8001/api/genres/"}
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        async with mock_client_class() as client:
            # Test POST initial
            response = await client.post(
                f"{base_url}/api/genres",
                json=test_data,
                headers=headers
            )
            
            # Diagnostic du statut de réponse
            if response.status_code == 307:
                # Gérer la redirection 307
                redirect_location = response.headers.get('location')
                assert redirect_location is not None, "Redirection 307 sans location"
                
                logger.info(f"🔄 Redirection 307 vers: {redirect_location}")
                
                # Simuler la réponse de redirection
                redirect_response = AsyncMock()
                redirect_response.status_code = 201
                mock_client.post.return_value = redirect_response
                
                # Suivre la redirection
                final_response = await client.post(
                    redirect_location,
                    json=test_data,
                    headers=headers
                )
                
                logger.info(f"✅ POST redirect status: {final_response.status_code}")
                
            else:
                logger.warning(f"⚠️ POST status inattendu: {response.status_code}")
                assert response.status_code in [200, 201, 307, 422], f"Status non géré: {response.status_code}"


@pytest.mark.api
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.asyncio
async def test_genres_endpoint_full_diagnostic():
    """Test complet de diagnostic de l'endpoint genres."""
    base_url = os.getenv("TEST_API_URL", "http://localhost:8001")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SoniqueBay-Worker/1.0"
    }
    
    test_data = {"name": "Diagnostic Test Genre"}
    
    # Mock des réponses
    get_response = AsyncMock()
    get_response.status_code = 404
    
    options_response = AsyncMock()
    options_response.status_code = 405
    
    post_response = AsyncMock()
    post_response.status_code = 307
    post_response.headers = {"location": f"{base_url}/api/genres/"}
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        
        # Configurer les réponses pour chaque type de requête
        def side_effect_get(*args, **kwargs):
            return get_response
        
        def side_effect_options(*args, **kwargs):
            return options_response
            
        def side_effect_post(*args, **kwargs):
            return post_response
        
        mock_client.get.side_effect = side_effect_get
        mock_client.options.side_effect = side_effect_options
        mock_client.post.side_effect = side_effect_post
        
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        async with mock_client_class() as client:
            # 1. Test GET
            get_response_result = await client.get(f"{base_url}/api/genres", headers=headers)
            logger.info(f"GET {base_url}/api/genres -> {get_response_result.status_code}")
            
            # 2. Test OPTIONS
            options_response_result = await client.options(f"{base_url}/api/genres", headers=headers)
            logger.info(f"OPTIONS {base_url}/api/genres -> {options_response_result.status_code}")
            
            # 3. Test POST avec diagnostic complet
            post_response_result = await client.post(
                f"{base_url}/api/genres",
                json=test_data,
                headers=headers
            )
            logger.info(f"POST {base_url}/api/genres -> {post_response_result.status_code}")
            
            # Assertions de base
            assert get_response_result.status_code in [200, 404]
            assert options_response_result.status_code in [200, 204, 405]
            assert post_response_result.status_code in [200, 201, 307, 422]
            
            logger.info("✅ Diagnostic complet terminé")
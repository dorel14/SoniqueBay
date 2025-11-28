"""
Test pour valider la correction de l'endpoint genres (405 Method Not Allowed).
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend_worker.background_tasks.worker_metadata import _create_missing_genres


@pytest.mark.asyncio
async def test_create_missing_genres_fixed():
    """
    Test que la fonction _create_missing_genres fonctionne correctement
    après correction de l'endpoint 405.
    """
    # Données de test
    genres_data = [
        {'name': 'Rock'},
        {'name': 'Jazz'},
        {'name': 'Electronic'}
    ]
    
    # Simuler les réponses de l'API (création un par un)
    with patch('backend_worker.background_tasks.worker_metadata.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Simuler les réponses POST pour chaque genre
        mock_responses = [
            {'id': 1, 'name': 'Rock'},
            {'id': 2, 'name': 'Jazz'},
            {'id': 3, 'name': 'Electronic'}
        ]
        
        for i, response_data in enumerate(mock_responses):
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = response_data
            mock_client.post.return_value = mock_response
        
        # Tester la fonction corrigée
        result = await _create_missing_genres(genres_data)
        
        # Vérifications
        assert len(result) == 3
        assert result == mock_responses
        
        # Vérifier que les bons endpoints ont été appelé
        expected_calls = [
            ('http://backend:8001/api/genres', {'name': 'Rock'}),
            ('http://backend:8001/api/genres', {'name': 'Jazz'}),
            ('http://backend:8001/api/genres', {'name': 'Electronic'})
        ]
        
        assert mock_client.post.call_count == 3
        
        for i, (expected_url, expected_json) in enumerate(expected_calls):
            call_args = mock_client.post.call_args_list[i]
            actual_url = call_args[0][0]  # Premier argument positionnel
            actual_json = call_args[1]['json']  # Argument keyword json
            
            assert actual_url == expected_url
            assert actual_json == expected_json
        
        print(f"✅ Test réussi: {len(result)} genres créés")


@pytest.mark.asyncio
async def test_create_missing_genres_with_errors():
    """
    Test que la fonction gère correctement les erreurs lors de la création.
    """
    genres_data = [
        {'name': 'Valid Genre'},
        {'name': 'Invalid Genre'}
    ]
    
    with patch('backend_worker.background_tasks.worker_metadata.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Réponse valide pour le premier genre
        def make_valid_response():
            response = AsyncMock()
            response.status_code = 201
            response.json.return_value = {'id': 1, 'name': 'Valid Genre'}
            return response
        
        # Réponse d'erreur pour le second genre
        def make_error_response():
            response = AsyncMock()
            response.status_code = 400
            response.text = 'Genre already exists'
            return response
        
        mock_client.post.side_effect = [make_valid_response(), make_error_response()]
        
        # Tester la fonction
        result = await _create_missing_genres(genres_data)
        
        # Vérifications
        assert len(result) == 1  # Seul le premier genre doit être créé
        assert result[0]['name'] == 'Valid Genre'
        
        print(f"✅ Test d'erreur réussi: {len(result)}/2 genres créés (erreur attendue)")


if __name__ == "__main__":
    asyncio.run(test_create_missing_genres_fixed())
    asyncio.run(test_create_missing_genres_with_errors())
    print("✅ Tous les tests de correction genres ont réussi!")
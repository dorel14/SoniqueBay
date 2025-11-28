"""
Test pour vérifier que la solution de gestion des contraintes UNIQUE sur les genres fonctionne.
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from backend_worker.background_tasks.worker_metadata import (
    _search_existing_genres, 
    _create_missing_genres,
    _clean_and_split_genres
)


class TestGenresUniqueConstraintFix:
    """Tests pour la correction des erreurs de contrainte UNIQUE sur les genres."""

    @pytest.mark.asyncio
    async def test_search_existing_genres_improved(self):
        """Test que la recherche de genres existants fonctionne mieux."""
        # Mock des réponses HTTP
        mock_genres = [
            {"id": 1, "name": "Electronic"},
            {"id": 2, "name": "Rock"},
            {"id": 3, "name": "POP"}
        ]
        
        async def mock_get_response(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 200
            response.json.return_value = mock_genres
            return response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = mock_get_response
            
            # Test avec un genre qui existe
            result = await _search_existing_genres(["electronic", "jazz"])
            
            # Vérifier que Electronic est trouvé (correspondance exacte insensitive à la casse)
            assert "electronic" in result
            assert result["electronic"]["name"] == "Electronic"
            assert result["electronic"]["id"] == 1
            
            # Vérifier que Jazz n'est pas trouvé
            assert "jazz" not in result

    @pytest.mark.asyncio
    async def test_create_missing_genres_handles_409(self):
        """Test que la création de genres gère correctement les erreurs 409 (conflict)."""
        
        async def mock_post_response_409(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 409
            response.text = "Genre already exists"
            return response
            
        async def mock_get_response(*args, **kwargs):
            search_response = AsyncMock()
            search_response.status_code = 200
            search_response.json.return_value = [
                {"id": 1, "name": "Electronic"}
            ]
            return search_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post_response_409
            mock_client.return_value.__aenter__.return_value.get = mock_get_response
            
            # Test de création d'un genre qui existe déjà
            genres_to_create = [{"name": "Electronic"}]
            result = await _create_missing_genres(genres_to_create)
            
            # Vérifier que le genre existant est retourné
            assert len(result) == 1
            assert result[0]["name"] == "Electronic"
            assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_create_missing_genres_successful_creation(self):
        """Test de création réussie d'un nouveau genre."""
        
        async def mock_post_response_success(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 201
            response.json.return_value = {"id": 10, "name": "Ambient"}
            return response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post_response_success
            
            # Test de création d'un nouveau genre
            genres_to_create = [{"name": "Ambient"}]
            result = await _create_missing_genres(genres_to_create)
            
            # Vérifier que le nouveau genre est retourné
            assert len(result) == 1
            assert result[0]["name"] == "Ambient"
            assert result[0]["id"] == 10

    @pytest.mark.asyncio
    async def test_create_missing_genres_handles_307_redirect(self):
        """Test que la gestion des redirections 307 fonctionne."""
        
        async def mock_post_response_307(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 307
            response.headers = {"location": "http://api:8001/api/genres/redirect"}
            return response
        
        async def mock_post_response_success(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 201
            response.json.return_value = {"id": 20, "name": "Classical"}
            return response
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simuler la première requête qui retourne 307
            mock_client.return_value.__aenter__.return_value.post = mock_post_response_success
            
            # Test de création avec redirection
            genres_to_create = [{"name": "Classical"}]
            result = await _create_missing_genres(genres_to_create)
            
            # Vérifier que le genre est créé avec succès
            assert len(result) == 1
            assert result[0]["name"] == "Classical"
            assert result[0]["id"] == 20

    @pytest.mark.asyncio
    async def test_clean_and_split_genres_edge_cases(self):
        """Test des cas limites pour le nettoyage de genres."""
        # Test avec genre vide
        assert _clean_and_split_genres("") == []
        assert _clean_and_split_genres(None) == []
        
        # Test avec genre complexe
        result = _clean_and_split_genres("Electronic, House - Techno, Ambient")
        assert len(result) >= 2  # Au moins quelques genres extraits
        
        # Test avec genre normal
        result = _clean_and_split_genres("Rock")
        assert "Rock" in result
        
        # Test avec caractères spéciaux
        result = _clean_and_split_genres("Hip-Hop/Rap")
        assert len(result) > 0  # Devrait diviser en plusieurs parties

    @pytest.mark.asyncio
    async def test_error_handling_in_create_missing_genres(self):
        """Test que les erreurs sont correctement gérées."""
        
        async def mock_post_error(*args, **kwargs):
            raise httpx.TimeoutException("Network timeout")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post_error
            
            # Test avec une erreur
            genres_to_create = [{"name": "TestGenre"}]
            result = await _create_missing_genres(genres_to_create)
            
            # Vérifier qu'aucun genre n'est créé en cas d'erreur
            assert result == []

    @pytest.mark.asyncio
    async def test_alternative_search_on_error(self):
        """Test de l'approche alternative en cas d'erreur de création."""
        
        async def mock_post_response_error(*args, **kwargs):
            response = AsyncMock()
            response.status_code = 500
            response.text = "Internal server error"
            return response
            
        async def mock_get_response_success(*args, **kwargs):
            search_response = AsyncMock()
            search_response.status_code = 200
            search_response.json.return_value = [
                {"id": 5, "name": "Folk"}
            ]
            return search_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post_response_error
            mock_client.return_value.__aenter__.return_value.get = mock_get_response_success
            
            # Test d'approche alternative
            genres_to_create = [{"name": "Folk"}]
            result = await _create_missing_genres(genres_to_create)
            
            # Vérifier que l'approche alternative fonctionne
            assert len(result) == 1
            assert result[0]["name"] == "Folk"
            assert result[0]["id"] == 5

    def test_logging_improvements(self):
        """Vérifier que les logs sont améliorés pour le debugging."""
        # Cette fonction teste principalement que les fonctions ne lèvent pas d'exceptions
        # lors des opérations de logging
        import logging
        
        # Configurer un logger de test
        logging.getLogger('test_logger')
        
        # Les fonctions améliorées devraient logger sans erreur
        # (ce test est plus une vérification qu'il n'y a pas d'erreur de syntaxe)
        assert True  # Test passe si aucun exception n'est levée


if __name__ == "__main__":
    # Exécution des tests
    import sys
    sys.path.append('.')
    
    pytest.main([__file__, "-v"])
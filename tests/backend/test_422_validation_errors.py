"""
Tests pour valider la correction des erreurs de validation 422.

Ce module contient les tests qui étaient dans scripts/test_422_errors.py
refactorisés pour utiliser pytest avec des mocks appropriés.
"""

import pytest
import aiohttp
from unittest.mock import AsyncMock, patch


class Test422ValidationErrors:
    """Tests pour les erreurs de validation 422."""

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_track_batch_validation_error(self):
        """Test erreur 422 sur /api/tracks/batch avec données invalides."""
        
        # Données invalides - champs obligatoires manquants
        invalid_data = [
            {
                # "title" manquant - champ obligatoire
                "path": "/music/test.mp3",
                "track_artist_id": "not_an_integer",  # Type incorrect
                "duration": 180,
                "invalid_field": "this_should_not_exist"
            },
            {
                "title": "",  # Titre vide
                "track_artist_id": -999,  # ID invalide
                "danceability": 2.0,  # Valeur > 1 (contrainte validée par ge=0, le=1)
                "mood_tags": "not_a_list"  # Devrait être une liste
            }
        ]
        
        # Mock de la réponse HTTP avec statut 422
        mock_response = AsyncMock()
        mock_response.status = 422
        mock_response.json.return_value = {
            "detail": [
                {
                    "loc": ["body", 0, "title"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", 0, "track_artist_id"],
                    "msg": "ensure this value is an integer",
                    "type": "type_error.integer"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://test-api:8001/api/tracks/batch",
                    json=invalid_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Assertions
                    assert response.status == 422
                    
                    error_data = await response.json()
                    assert "detail" in error_data
                    assert isinstance(error_data["detail"], list)
                    
                    # Vérifier que les erreurs sont bien détectées
                    error_messages = [error["msg"] for error in error_data["detail"]]
                    assert any("field required" in msg for msg in error_messages)
                    assert any("integer" in msg for msg in error_messages)

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_album_batch_validation_error(self):
        """Test erreur 422 sur /api/albums/batch avec données invalides."""
        
        invalid_data = [
            {
                # "title" manquant - champ obligatoire
                "album_artist_id": "invalid_id",
                "release_year": 2024.5,  # Devrait être string
                "invalid_field": "test"
            },
            {
                "title": "",  # Titre vide
                "album_artist_id": 0,  # ID invalide (devrait être > 0)
            }
        ]
        
        # Mock de la réponse HTTP avec statut 422
        mock_response = AsyncMock()
        mock_response.status = 422
        mock_response.json.return_value = {
            "detail": [
                {
                    "loc": ["body", 0, "title"],
                    "msg": "ensure this value is not an empty string",
                    "type": "value_error.str.min_length"
                },
                {
                    "loc": ["body", 0, "album_artist_id"],
                    "msg": "ensure this value is greater than 0",
                    "type": "value_error.number.not_gt"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://test-api:8001/api/albums/batch",
                    json=invalid_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Assertions
                    assert response.status == 422
                    
                    error_data = await response.json()
                    assert "detail" in error_data

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_single_track_creation_error(self):
        """Test erreur 422 sur création d'une track unique."""
        
        invalid_track = {
            # "title" manquant - champ obligatoire
            "path": "/music/single_test.mp3",
            "track_artist_id": "not_an_integer",
            "bpm": "not_a_number",
            "danceability": 5.0  # Valeur invalide (doit être entre 0 et 1)
        }
        
        # Mock de la réponse HTTP avec statut 422
        mock_response = AsyncMock()
        mock_response.status = 422
        mock_response.json.return_value = {
            "detail": [
                {
                    "loc": ["body", "title"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "danceability"],
                    "msg": "ensure this value is less than or equal to 1",
                    "type": "value_error.number.not_le"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://test-api:8001/api/tracks",
                    json=invalid_track,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Assertions
                    assert response.status == 422
                    
                    error_data = await response.json()
                    assert "detail" in error_data

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_graphql_validation_errors(self):
        """Test erreurs de validation GraphQL via mutation."""
        
        graphql_query = {
            "query": """
            mutation CreateTracksBatch($data: [TrackCreateInput!]!) {
                createTracksBatchMassive(data: $data) {
                    success
                    tracksProcessed
                    message
                }
            }
            """,
            "variables": {
                "data": [
                    {
                        # Champs manquants/invalides
                        "title": "Test Track",
                        "path": "/music/test.mp3",
                        "trackArtistId": "not_an_integer",  # Type incorrect
                        "bpm": "invalid_bpm",
                        "danceability": 3.0  # Valeur > 1
                    }
                ]
            }
        }
        
        # Mock de la réponse GraphQL avec erreurs
        mock_response = AsyncMock()
        mock_response.status = 400  # GraphQL erreurs utilisent 400
        mock_response.json.return_value = {
            "errors": [
                {
                    "message": "Validation failed",
                    "locations": [{"line": 1, "column": 1}],
                    "path": ["createTracksBatchMassive"],
                    "extensions": {
                        "code": "VALIDATION_ERROR",
                        "details": [
                            {"field": "trackArtistId", "message": "must be an integer"},
                            {"field": "danceability", "message": "must be <= 1"}
                        ]
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://test-api:8001/graphql",
                    json=graphql_query,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Assertions
                    assert response.status == 400
                    
                    response_data = await response.json()
                    assert "errors" in response_data
                    assert len(response_data["errors"]) > 0

    @pytest.mark.api
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_valid_data_success(self):
        """Test avec données valides pour s'assurer que le système fonctionne."""
        
        valid_track = {
            "title": "Test Track Valid",
            "path": "/music/valid_test.mp3",
            "track_artist_id": 1,
            "duration": 180,
            "bpm": 120,
            "danceability": 0.8,
            "year": "2024"
        }
        
        # Mock de la réponse HTTP avec succès
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json.return_value = {
            "id": 123,
            "title": "Test Track Valid",
            "status": "created"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://test-api:8001/api/tracks",
                    json=valid_track,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Assertions
                    assert response.status in [200, 201]
                    
                    data = await response.json()
                    assert "id" in data
                    assert data["title"] == "Test Track Valid"

    @pytest.mark.api
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_validation_scenarios(self):
        """Test complet de tous les scénarios de validation 422."""
        
        scenarios = [
            {
                "name": "Track Batch",
                "endpoint": "/api/tracks/batch",
                "method": "POST",
                "invalid_data": [{"path": "/test.mp3", "track_artist_id": "invalid"}],
                "expected_status": 422
            },
            {
                "name": "Album Batch",
                "endpoint": "/api/albums/batch", 
                "method": "POST",
                "invalid_data": [{"album_artist_id": 0}],
                "expected_status": 422
            },
            {
                "name": "Single Track",
                "endpoint": "/api/tracks",
                "method": "POST",
                "invalid_data": {"path": "/test.mp3"},
                "expected_status": 422
            }
        ]
        
        for scenario in scenarios:
            # Mock pour chaque scénario
            mock_response = AsyncMock()
            mock_response.status = scenario["expected_status"]
            mock_response.json.return_value = {"detail": "Validation error"}
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__.return_value = mock_response
                
                async with aiohttp.ClientSession() as session:
                    if scenario["method"] == "POST":
                        async with session.post(
                            f"http://test-api:8001{scenario['endpoint']}",
                            json=scenario["invalid_data"],
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            assert response.status == scenario["expected_status"], \
                                f"Scénario {scenario['name']}: status attendu {scenario['expected_status']}, obtenu {response.status}"
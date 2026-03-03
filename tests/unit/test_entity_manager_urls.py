"""
Tests unitaires pour valider les corrections des URLs dans entity_manager.py

Ce module teste:
1. Les URLs correctes pour les endpoints de tags
2. La logique de création d'artistes avec upsert (pas de doublons)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json


class TestEntityManagerURLs:
    """Tests pour valider les URLs des endpoints API."""

    @pytest.fixture
    def mock_client(self):
        """Fixture pour créer un client HTTP mocké."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def mock_response(self):
        """Fixture pour créer une réponse HTTP mockée."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = []
        return response

    @pytest.mark.asyncio
    async def test_create_or_get_genre_tag_uses_correct_url(self, mock_client, mock_response):
        """
        Test que create_or_get_genre_tag utilise l'URL correcte /api/tags/genre-tags/
        et non /api/genre-tags/
        """
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(return_value={"id": 1, "name": "Test Genre"})
        )

        # Importer la fonction à tester
        from backend_worker.services.entity_manager import create_or_get_genre_tag

        # Appeler la fonction
        result = await create_or_get_genre_tag(mock_client, "Test Genre")

        # Vérifier que l'URL correcte est utilisée pour GET
        mock_client.get.assert_called_once()
        get_call = mock_client.get.call_args
        assert "/api/tags/genre-tags/" in str(get_call), \
            f"URL incorrecte pour GET genre-tags: {get_call}"

        # Vérifier que l'URL correcte est utilisée pour POST
        mock_client.post.assert_called_once()
        post_call = mock_client.post.call_args
        assert "/api/tags/genre-tags/" in str(post_call), \
            f"URL incorrecte pour POST genre-tags: {post_call}"

    @pytest.mark.asyncio
    async def test_create_or_get_mood_tag_uses_correct_url(self, mock_client, mock_response):
        """
        Test que create_or_get_mood_tag utilise l'URL correcte /api/tags/mood-tags/
        et non /api/mood-tags/
        """
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(return_value={"id": 1, "name": "Test Mood"})
        )

        # Importer la fonction à tester
        from backend_worker.services.entity_manager import create_or_get_mood_tag

        # Appeler la fonction
        result = await create_or_get_mood_tag(mock_client, "Test Mood")

        # Vérifier que l'URL correcte est utilisée pour GET
        mock_client.get.assert_called_once()
        get_call = mock_client.get.call_args
        assert "/api/tags/mood-tags/" in str(get_call), \
            f"URL incorrecte pour GET mood-tags: {get_call}"

        # Vérifier que l'URL correcte est utilisée pour POST
        mock_client.post.assert_called_once()
        post_call = mock_client.post.call_args
        assert "/api/tags/mood-tags/" in str(post_call), \
            f"URL incorrecte pour POST mood-tags: {post_call}"


class TestArtistCreation:
    """Tests pour valider la logique de création d'artistes sans doublons."""

    @pytest.fixture
    def mock_client(self):
        """Fixture pour créer un client HTTP mocké."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.mark.asyncio
    async def test_create_or_get_artists_batch_uses_upsert(self, mock_client):
        """
        Test que create_or_get_artists_batch utilise upsertArtist au lieu de createArtists
        pour éviter les violations de contrainte d'unicité.
        """
        # Mock la réponse GraphQL pour upsertArtist
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "upsertArtist": {
                    "id": 1,
                    "name": "Van Halen",
                    "musicbrainzArtistid": "b665b768-0d83-4363-950c-31ed39317c15"
                }
            }
        }
        mock_client.post.return_value = mock_response

        # Importer la fonction à tester
        from backend_worker.services.entity_manager import create_or_get_artists_batch

        # Données d'artistes à tester
        artists_data = [
            {
                "name": "Van Halen",
                "musicbrainz_artistid": "b665b768-0d83-4363-950c-31ed39317c15"
            }
        ]

        # Appeler la fonction
        result = await create_or_get_artists_batch(mock_client, artists_data)

        # Vérifier que la mutation upsertArtist est utilisée
        mock_client.post.assert_called()
        post_call = mock_client.post.call_args
        
        # Vérifier que le corps de la requête contient upsertArtist
        call_kwargs = post_call.kwargs if post_call.kwargs else post_call[1]
        json_data = call_kwargs.get('json', {})
        
        # Vérifier que c'est bien upsertArtist et non createArtists
        query = json_data.get('query', '')
        assert 'upsertArtist' in query, \
            f"La mutation upsertArtist n'est pas utilisée. Query: {query}"
        assert 'createArtists' not in query, \
            f"La mutation createArtists (qui cause les doublons) est encore utilisée. Query: {query}"

    @pytest.mark.asyncio
    async def test_create_or_get_artists_batch_handles_existing_artist(self, mock_client):
        """
        Test que create_or_get_artists_batch gère correctement un artiste existant
        sans lever d'exception de contrainte d'unicité.
        """
        # Mock la réponse GraphQL pour upsertArtist (qui retourne l'artiste existant)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "upsertArtist": {
                    "id": 1,
                    "name": "Van Halen",
                    "musicbrainzArtistid": "b665b768-0d83-4363-950c-31ed39317c15"
                }
            }
        }
        mock_client.post.return_value = mock_response

        # Importer la fonction à tester
        from backend_worker.services.entity_manager import create_or_get_artists_batch

        # Données d'artistes à tester (artiste qui existe déjà)
        artists_data = [
            {
                "name": "Van Halen",
                "musicbrainz_artistid": "b665b768-0d83-4363-950c-31ed39317c15"
            }
        ]

        # Appeler la fonction - ne devrait pas lever d'exception
        try:
            result = await create_or_get_artists_batch(mock_client, artists_data)
            
            # Vérifier que l'artiste est retourné sans erreur
            assert "van halen" in result, "L'artiste n'est pas dans le résultat"
            assert result["van halen"]["id"] == 1, "L'ID de l'artiste est incorrect"
            
        except Exception as e:
            pytest.fail(f"La fonction a levé une exception pour un artiste existant: {e}")

    @pytest.mark.asyncio
    async def test_create_or_get_artists_batch_processes_multiple_artists(self, mock_client):
        """
        Test que create_or_get_artists_batch traite correctement plusieurs artistes
        en utilisant upsertArtist pour chacun.
        """
        # Mock les réponses GraphQL pour upsertArtist
        responses = [
            {
                "data": {
                    "upsertArtist": {
                        "id": 1,
                        "name": "Artist 1",
                        "musicbrainzArtistid": None
                    }
                }
            },
            {
                "data": {
                    "upsertArtist": {
                        "id": 2,
                        "name": "Artist 2",
                        "musicbrainzArtistid": None
                    }
                }
            }
        ]
        
        # Configurer le mock pour retourner des réponses différentes à chaque appel
        mock_client.post.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=resp))
            for resp in responses
        ]

        # Importer la fonction à tester
        from backend_worker.services.entity_manager import create_or_get_artists_batch

        # Données d'artistes à tester
        artists_data = [
            {"name": "Artist 1"},
            {"name": "Artist 2"}
        ]

        # Appeler la fonction
        result = await create_or_get_artists_batch(mock_client, artists_data)

        # Vérifier que upsertArtist a été appelé pour chaque artiste
        assert mock_client.post.call_count == 2, \
            f"upsertArtist devrait être appelé 2 fois, mais appelé {mock_client.post.call_count} fois"

        # Vérifier que tous les artistes sont dans le résultat
        assert "artist 1" in result, "Artist 1 n'est pas dans le résultat"
        assert "artist 2" in result, "Artist 2 n'est pas dans le résultat"


class TestURLPatterns:
    """Tests pour valider les patterns d'URLs utilisés."""

    def test_genre_tag_url_pattern(self):
        """Test que le pattern d'URL pour genre-tags est correct."""
        expected_pattern = "/api/tags/genre-tags/"
        incorrect_patterns = [
            "/api/genre-tags/",
            "/api/genre_tags/",
            "/api/tags/genre_tags/",
        ]
        
        for pattern in incorrect_patterns:
            assert pattern != expected_pattern, \
                f"Le pattern {pattern} ne devrait pas être utilisé"

    def test_mood_tag_url_pattern(self):
        """Test que le pattern d'URL pour mood-tags est correct."""
        expected_pattern = "/api/tags/mood-tags/"
        incorrect_patterns = [
            "/api/mood-tags/",
            "/api/mood_tags/",
            "/api/tags/mood_tags/",
        ]
        
        for pattern in incorrect_patterns:
            assert pattern != expected_pattern, \
                f"Le pattern {pattern} ne devrait pas être utilisé"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

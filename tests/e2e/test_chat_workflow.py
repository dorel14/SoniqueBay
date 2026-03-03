# tests/e2e/test_chat_workflow.py
"""
Tests E2E pour le workflow complet du chat IA SoniqueBay.

Ce module contient les tests de bout en bout pour:
- Le workflow complet du chat IA
- La persistance des conversations
- Les réponses de l'agent
- L'intégration avec la bibliothèque musicale

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.e2e, pytest.mark.chat, pytest.mark.ai
"""

import pytest
import logging
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from tests.conftest import (
    client,
    db_session,
    create_test_track,
    create_test_tracks,
    create_test_artist_album_tracks,
)

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.chat
@pytest.mark.ai
class TestChatWorkflow:
    """Tests du workflow complet du chat IA."""

    @pytest.fixture
    def chat_endpoint(self):
        """Endpoint du chat IA."""
        return "/api/chat"

    def test_chat_initialization(self, client, chat_endpoint):
        """Test l'initialisation d'une nouvelle conversation."""
        response = client.post(
            chat_endpoint,
            json={"message": "Bonjour, je cherche de la musique"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "response" in data
        assert "message_id" in data

    def test_chat_response_content(self, client, chat_endpoint):
        """Test le contenu des réponses du chat."""
        response = client.post(
            chat_endpoint,
            json={"message": "Je veux écouter du rock"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_conversation_context(self, client, chat_endpoint):
        """Test la conservation du contexte de conversation."""
        # Première question
        response1 = client.post(
            chat_endpoint,
            json={"message": "Je cherche des albums de jazz"}
        )
        conversation_id = response1.json()["conversation_id"]

        # Question suivante (doit maintenir le contexte)
        response2 = client.post(
            chat_endpoint,
            json={
                "conversation_id": conversation_id,
                "message": "Et des pistes similaires?"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["conversation_id"] == conversation_id

    def test_multi_turn_conversation(self, client, chat_endpoint):
        """Test une conversation multi-tours."""
        conversation_id = None
        messages = [
            "Salut, je cherche de la musique",
            "J'aime le rock des années 80",
            "Tu as des recommandations?",
            "Plus exactement, du hard rock",
        ]

        for msg in messages:
            payload = {"message": msg}
            if conversation_id:
                payload["conversation_id"] = conversation_id

            response = client.post(chat_endpoint, json=payload)
            assert response.status_code == 200
            data = response.json()
            conversation_id = data["conversation_id"]

        # Vérifier que la conversation existe toujours
        assert conversation_id is not None


@pytest.mark.e2e
@pytest.mark.chat
@pytest.mark.ai
class TestConversationPersistence:
    """Tests pour la persistance des conversations."""

    @pytest.fixture
    def saved_conversation(self, client, chat_endpoint):
        """Crée une conversation sauvegardée."""
        response = client.post(
            chat_endpoint,
            json={"message": "Test conversation persistence"}
        )
        return response.json()

    def test_conversation_saved(self, client, saved_conversation):
        """Test qu'une conversation est sauvegardée."""
        conversation_id = saved_conversation["conversation_id"]

        # Récupérer la conversation
        response = client.get(f"/api/chat/{conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id

    def test_conversation_history(self, client, chat_endpoint):
        """Test l'historique des conversations."""
        # Créer plusieurs conversations
        conv_ids = []
        for i in range(3):
            response = client.post(
                chat_endpoint,
                json={"message": f"Conversation {i+1}"}
            )
            conv_ids.append(response.json()["conversation_id"])

        # Lister les conversations
        response = client.get("/api/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        # Vérifier que nos conversations sont présentes
        saved_ids = [c["id"] for c in data["conversations"]]
        for cid in conv_ids:
            assert cid in saved_ids

    def test_conversation_messages(self, client, chat_endpoint):
        """Test les messages d'une conversation."""
        # Créer une conversation avec plusieurs messages
        response = client.post(
            chat_endpoint,
            json={"message": "Premier message"}
        )
        conv_id = response.json()["conversation_id"]

        client.post(
            chat_endpoint,
            json={
                "conversation_id": conv_id,
                "message": "Deuxième message"
            }
        )

        # Récupérer les messages
        response = client.get(f"/api/chat/{conv_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) >= 2

    def test_conversation_deletion(self, client, chat_endpoint):
        """Test la suppression d'une conversation."""
        # Créer une conversation
        response = client.post(
            chat_endpoint,
            json={"message": "Conversation à supprimer"}
        )
        conv_id = response.json()["conversation_id"]

        # Supprimer
        response = client.delete(f"/api/chat/{conv_id}")
        assert response.status_code == 200

        # Vérifier la suppression
        response = client.get(f"/api/chat/{conv_id}")
        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.chat
@pytest.mark.ai
class TestChatLibraryIntegration:
    """Tests pour l'intégration du chat avec la bibliothèque musicale."""

    @pytest.fixture
    def populated_library(self, db_session):
        """Crée une bibliothèque avec des pistes variées."""
        return create_test_artist_album_tracks(db_session, track_count=5)

    def test_chat_recommends_tracks(self, client, chat_endpoint, populated_library):
        """Test que le chat peut recommander des pistes."""
        response = client.post(
            chat_endpoint,
            json={"message": "Recommande-moi des pistes"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # La réponse peut contenir des références à des pistes
        assert isinstance(data["response"], str)

    def test_chat_searches_library(self, client, chat_endpoint, populated_library):
        """Test la recherche dans la bibliothèque via le chat."""
        artist, album, tracks = populated_library

        response = client.post(
            chat_endpoint,
            json={"message": f"cherche des pistes de {artist.name}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_gets_track_details(self, client, chat_endpoint, populated_library):
        """Test la récupération des détails d'une piste via le chat."""
        artist, album, tracks = populated_library

        response = client.post(
            chat_endpoint,
            json={"message": f"Détails sur {tracks[0].title}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_navigation_suggestions(self, client, chat_endpoint):
        """Test les suggestions de navigation du chat."""
        response = client.post(
            chat_endpoint,
            json={"message": "Parcours ma bibliothèque"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # La réponse peut contenir des suggestions de navigation


@pytest.mark.e2e
@pytest.mark.chat
@pytest.mark.ai
class TestChatAgentResponses:
    """Tests pour les réponses de l'agent IA."""

    def test_greeting_response(self, client, chat_endpoint):
        """Test la réponse à un message de salutation."""
        response = client.post(
            chat_endpoint,
            json={"message": "Bonjour"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # La réponse devrait être contextuellement appropriée

    def test_music_query_response(self, client, chat_endpoint):
        """Test la réponse aux requêtes musicales."""
        queries = [
            "Joue de la musique",
            "Qu'est-ce que tu as dans ma bibliothèque?",
            "Trouve des chansons populaires",
        ]

        for query in queries:
            response = client.post(chat_endpoint, json={"message": query})
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert isinstance(data["response"], str)

    def test_help_response(self, client, chat_endpoint):
        """Test la réponse à une demande d'aide."""
        response = client.post(
            chat_endpoint,
            json={"message": "Aide"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # Devrait fournir de l'aide

    def test_error_handling_response(self, client, chat_endpoint):
        """Test la gestion des erreurs dans les réponses."""
        # Envoyer une requête qui pourrait causer une erreur
        response = client.post(
            chat_endpoint,
            json={"message": "x" * 10000}  # Message très long
        )
        # Devrait gérer gracieusement
        assert response.status_code in [200, 400, 413]


@pytest.mark.e2e
@pytest.mark.chat
@pytest.mark.ai
class TestChatEdgeCases:
    """Tests des cas limites pour le chat."""

    def test_empty_message(self, client, chat_endpoint):
        """Test avec un message vide."""
        response = client.post(
            chat_endpoint,
            json={"message": ""}
        )
        # Devrait gérer correctement
        assert response.status_code in [200, 400]

    def test_very_long_message(self, client, chat_endpoint):
        """Test avec un message très long."""
        long_message = "a" * 5000
        response = client.post(
            chat_endpoint,
            json={"message": long_message}
        )
        assert response.status_code in [200, 400, 413]

    def test_special_characters(self, client, chat_endpoint):
        """Test avec des caractères spéciaux."""
        special_message = "Test with émojis 🎵 and spëciäl chars 中文"
        response = client.post(
            chat_endpoint,
            json={"message": special_message}
        )
        assert response.status_code == 200

    def test_invalid_conversation_id(self, client, chat_endpoint):
        """Test avec un ID de conversation invalide."""
        response = client.post(
            chat_endpoint,
            json={
                "conversation_id": "invalid-id-123",
                "message": "Test message"
            }
        )
        assert response.status_code in [200, 404]

    def test_concurrent_messages(self, client, chat_endpoint):
        """Test l'envoi de messages concurrents."""
        # Simuler plusieurs messages rapides
        responses = []
        for i in range(5):
            response = client.post(
                chat_endpoint,
                json={"message": f"Message concurrent {i+1}"}
            )
            responses.append(response)

        # Vérifier les réponses
        for response in responses:
            assert response.status_code == 200

    def test_language_detection(self, client, chat_endpoint):
        """Test la détection de langue."""
        # Message en français
        response = client.post(
            chat_endpoint,
            json={"message": "Je cherche des chansons en français"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

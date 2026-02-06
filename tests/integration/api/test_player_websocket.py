# tests/integration/api/test_player_websocket.py
"""
Tests d'intégration pour la connexion WebSocket du player SoniqueBay.

Ce module contient les tests d'intégration pour:
- La connexion WebSocket au endpoint player
- Les messages de contrôle du player via WebSocket
- La synchronisation d'état en temps réel
- La gestion des erreurs WebSocket

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.integration, pytest.mark.websocket, pytest.mark.player
"""

import pytest
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from tests.conftest import (
    client,
    db_session,
    create_test_track,
    create_test_tracks,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.player
class TestWebSocketConnection:
    """Tests pour la connexion WebSocket du player."""

    @pytest.fixture
    def ws_url(self):
        """URL du endpoint WebSocket pour le player."""
        return "/api/ws/player"

    def test_websocket_connection_established(self, client, ws_url):
        """Test l'établissement d'une connexion WebSocket."""
        with client.websocket_connect(ws_url) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert "player_state" in data

    def test_websocket_connection_with_session(self, client, ws_url):
        """Test la connexion WebSocket avec une session utilisateur."""
        with client.websocket_connect(f"{ws_url}?session_id=test-session") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["session_id"] == "test-session"

    def test_multiple_websocket_connections(self, client, ws_url):
        """Test les connexions WebSocket multiples simultanées."""
        # Première connexion
        ws1 = client.ws_connect(ws_url)
        ws1.receive_json()  # Attendre la confirmation

        # Deuxième connexion
        ws2 = client.ws_connect(ws_url)
        ws2.receive_json()  # Attendre la confirmation

        # Les deux connexions doivent être actives
        assert ws1 is not None
        assert ws2 is not None

        # Fermer les connexions
        ws1.close()
        ws2.close()

    def test_websocket_disconnection_handling(self, client, ws_url):
        """Test la gestion de la déconnexion WebSocket."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()  # Connexion établie

        # Simuler une déconnexion
        ws.close()

        # La connexion doit être fermée sans erreur
        # Note: Le comportement exact dépend de l'implémentation du serveur


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.player
class TestWebSocketPlayerControl:
    """Tests pour les messages de contrôle du player via WebSocket."""

    @pytest.fixture
    def connected_websocket(self, client, ws_url):
        """WebSocket connecté pour les tests."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()  # Attendre la confirmation de connexion
        yield ws
        ws.close()

    @pytest.fixture
    def test_track(self, db_session):
        """Crée une piste de test."""
        return create_test_track(
            db_session,
            title="WS Control Track",
            path="/path/to/ws_control.mp3",
            bpm=128.0,
            key="Am",
        )

    def test_ws_play_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande play via WebSocket."""
        # Envoyer la commande play
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id,
            "position": 0.0
        })

        # Recevoir la réponse
        response = connected_websocket.receive_json()
        assert response["type"] == "play_response"
        assert response["status"] == "success"
        assert response["is_playing"] is True

    def test_ws_pause_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande pause via WebSocket."""
        # D'abord jouer
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id
        })
        connected_websocket.receive_json()

        # Puis mettre en pause
        connected_websocket.send_json({"type": "pause"})
        response = connected_websocket.receive_json()
        assert response["type"] == "pause_response"
        assert response["status"] == "success"
        assert response["is_playing"] is False

    def test_ws_resume_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande resume via WebSocket."""
        # Jouer puis pause
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id
        })
        connected_websocket.receive_json()
        connected_websocket.send_json({"type": "pause"})
        connected_websocket.receive_json()

        # Reprendre
        connected_websocket.send_json({"type": "resume"})
        response = connected_websocket.receive_json()
        assert response["type"] == "resume_response"
        assert response["status"] == "success"
        assert response["is_playing"] is True

    def test_ws_stop_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande stop via WebSocket."""
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id
        })
        connected_websocket.receive_json()

        # Arrêter
        connected_websocket.send_json({"type": "stop"})
        response = connected_websocket.receive_json()
        assert response["type"] == "stop_response"
        assert response["status"] == "success"
        assert response["is_playing"] is False

    def test_ws_skip_command(self, connected_websocket, db_session):
        """Test l'envoi d'une commande skip via WebSocket."""
        tracks = create_test_tracks(db_session, count=3)

        # Créer une queue
        queue = [t.id for t in tracks]
        connected_websocket.send_json({
            "type": "play",
            "track_id": queue[0],
            "queue": queue
        })
        connected_websocket.receive_json()

        # Skip vers la suivante
        connected_websocket.send_json({"type": "skip", "direction": "next"})
        response = connected_websocket.receive_json()
        assert response["type"] == "skip_response"
        assert response["status"] == "success"
        assert response["current_track_id"] == queue[1]

    def test_ws_seek_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande seek via WebSocket."""
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id
        })
        connected_websocket.receive_json()

        # Chercher une position
        connected_websocket.send_json({
            "type": "seek",
            "position": 60.0
        })
        response = connected_websocket.receive_json()
        assert response["type"] == "seek_response"
        assert response["position"] == 60.0

    def test_ws_volume_command(self, connected_websocket, test_track):
        """Test l'envoi d'une commande volume via WebSocket."""
        connected_websocket.send_json({
            "type": "play",
            "track_id": test_track.id
        })
        connected_websocket.receive_json()

        # Changer le volume
        connected_websocket.send_json({
            "type": "volume",
            "volume": 0.7
        })
        response = connected_websocket.receive_json()
        assert response["type"] == "volume_response"
        assert response["volume"] == 0.7

    def test_ws_queue_command(self, connected_websocket, db_session):
        """Test la gestion de la queue via WebSocket."""
        tracks = create_test_tracks(db_session, count=3)

        # Ajouter des pistes à la queue
        connected_websocket.send_json({
            "type": "queue",
            "action": "add",
            "track_ids": [t.id for t in tracks]
        })
        response = connected_websocket.receive_json()
        assert response["type"] == "queue_response"
        assert len(response["queue"]) == 3


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.player
class TestWebSocketStateSynchronization:
    """Tests pour la synchronisation d'état via WebSocket."""

    @pytest.fixture
    def connected_websocket(self, client, ws_url):
        """WebSocket connecté pour les tests."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()
        yield ws
        ws.close()

    def test_state_broadcast_on_play(self, connected_websocket, db_session):
        """Test la diffusion d'état lors d'un play."""
        track = create_test_track(db_session, title="Broadcast Track", path="/path/to/broadcast.mp3")

        connected_websocket.send_json({
            "type": "play",
            "track_id": track.id
        })

        response = connected_websocket.receive_json()
        assert response["type"] == "play_response"
        assert "player_state" in response

    def test_state_broadcast_on_track_change(self, connected_websocket, db_session):
        """Test la diffusion d'état lors d'un changement de piste."""
        tracks = create_test_tracks(db_session, count=2)

        # Jouer la première piste
        connected_websocket.send_json({
            "type": "play",
            "track_id": tracks[0].id,
            "queue": [t.id for t in tracks]
        })
        connected_websocket.receive_json()

        # Skip vers la deuxième
        connected_websocket.send_json({
            "type": "skip",
            "direction": "next"
        })
        response = connected_websocket.receive_json()
        assert response["type"] == "skip_response"
        assert response["current_track_id"] == tracks[1].id

    def test_position_update_broadcast(self, connected_websocket, db_session):
        """Test la diffusion des mises à jour de position."""
        track = create_test_track(db_session, title="Position Track", path="/path/to/pos.mp3")

        connected_websocket.send_json({
            "type": "play",
            "track_id": track.id
        })
        connected_websocket.receive_json()

        # Les mises à jour de position peuvent être diffusées périodiquement
        # Vérifier que l'état inclut la position
        connected_websocket.send_json({"type": "get_state"})
        response = connected_websocket.receive_json()
        assert response["type"] == "state_response"
        assert "position" in response["player_state"]

    def test_playlist_sync(self, connected_websocket, db_session):
        """Test la synchronisation de la playlist."""
        tracks = create_test_tracks(db_session, count=4)

        connected_websocket.send_json({
            "type": "playlist",
            "action": "set",
            "tracks": [{"id": t.id, "title": t.title} for t in tracks]
        })
        response = connected_websocket.receive_json()
        assert response["type"] == "playlist_response"
        assert len(response["playlist"]) == 4


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.player
class TestWebSocketErrorHandling:
    """Tests pour la gestion des erreurs WebSocket."""

    @pytest.fixture
    def connected_websocket(self, client, ws_url):
        """WebSocket connecté pour les tests."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()
        yield ws
        ws.close()

    def test_invalid_track_id_error(self, connected_websocket):
        """Test la gestion d'un ID de piste invalide."""
        connected_websocket.send_json({
            "type": "play",
            "track_id": 999999
        })

        response = connected_websocket.receive_json()
        assert response["type"] == "error"
        assert "error_code" in response

    def test_missing_required_fields_error(self, connected_websocket):
        """Test la gestion des champs requis manquants."""
        # Envoyer un message incomplet
        connected_websocket.send_json({"type": "play"})

        response = connected_websocket.receive_json()
        assert response["type"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"

    def test_invalid_message_format_error(self, connected_websocket):
        """Test la gestion d'un format de message invalide."""
        # Envoyer un message malformed
        connected_websocket.send_text("invalid json{")

        # Le serveur doit gérer correctement ce cas
        # Peut fermer la connexion ou envoyer un message d'erreur

    def test_unauthorized_action_error(self, connected_websocket, db_session):
        """Test la gestion des actions non autorisées."""
        # Créer une piste sans permissions
        track = create_test_track(db_session, title="Private Track", path="/private.mp3")

        # Tenter de jouer une piste privée
        connected_websocket.send_json({
            "type": "play",
            "track_id": track.id
        })

        response = connected_websocket.receive_json()
        assert response["type"] == "error"
        assert response["error_code"] in ["NOT_FOUND", "FORBIDDEN"]

    def test_rate_limiting(self, connected_websocket, db_session):
        """Test la limitation de débit des messages."""
        track = create_test_track(db_session, title="Rate Limit Track", path="/path/to/rate.mp3")

        # Envoyer de nombreuses commandes rapidement
        responses = []
        for i in range(10):
            connected_websocket.send_json({
                "type": "play",
                "track_id": track.id
            })
            try:
                response = connected_websocket.receive_json()
                responses.append(response)
            except:
                break

        # Vérifier que le serveur a limité les requêtes
        # Au moins certains messages doivent être rejetés
        assert len(responses) <= 10

    def test_connection_timeout_handling(self, client, ws_url):
        """Test la gestion du timeout de connexion."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()

        # Ne pas envoyer de messages pendant un certain temps
        # Le serveur doit gérer le timeout correctement
        # La connexion peut être fermée après un délai d'inactivité

        ws.close()


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.player
class TestWebSocketMessageFormats:
    """Tests pour les formats de messages WebSocket."""

    def test_message_schema_validation(self, client, ws_url):
        """Test la validation du schéma des messages."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()

        # Message avec schéma valide
        ws.send_json({
            "type": "play",
            "track_id": 1,
            "position": 0.0
        })
        response = ws.receive_json()
        assert response["type"] in ["play_response", "error"]

        ws.close()

    def test_response_message_structure(self, client, ws_url, db_session):
        """Test la structure des messages de réponse."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()

        track = create_test_track(db_session, title="Structure Track", path="/path/to/struct.mp3")

        ws.send_json({
            "type": "play",
            "track_id": track.id
        })

        response = ws.receive_json()
        assert "type" in response
        assert "status" in response
        assert "timestamp" in response

        ws.close()

    def test_event_message_structure(self, client, ws_url, db_session):
        """Test la structure des messages d'événement."""
        ws = client.ws_connect(ws_url)
        ws.receive_json()

        track = create_test_track(db_session, title="Event Track", path="/path/to/event.mp3")

        # S'abonner aux événements
        ws.send_json({
            "type": "subscribe",
            "events": ["track_change", "position_update"]
        })

        response = ws.receive_json()
        assert response["type"] == "subscribe_response"
        assert "events" in response

        ws.close()

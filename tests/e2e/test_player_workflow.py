# tests/e2e/test_player_workflow.py
"""
Tests E2E pour le workflow complet du lecteur audio SoniqueBay.

Ce module contient les tests de bout en bout pour:
- Le workflow complet du lecteur audio
- La gestion de la file de lecture (queue)
- Les contrôles de lecture (play, pause, skip, previous)
- La synchronisation WebSocket avec le backend

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.e2e, pytest.mark.player
"""

import pytest
import asyncio
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
@pytest.mark.player
class TestPlayerWorkflow:
    """Tests du workflow complet du lecteur audio."""

    @pytest.fixture
    def player_state(self):
        """État initial du player pour les tests."""
        return {
            "is_playing": False,
            "current_track_id": None,
            "queue": [],
            "volume": 0.8,
            "position": 0.0,
            "duration": 180.0,
            "repeat": False,
            "shuffle": False,
        }

    @pytest.fixture
    def sample_queue_tracks(self, db_session):
        """Crée une file de lecture d'exemple."""
        return create_test_tracks(db_session, count=5)

    def test_player_initial_state(self, client, player_state):
        """Test l'état initial du player après connexion."""
        response = client.get("/api/player/state")
        assert response.status_code == 200
        data = response.json()
        assert data["is_playing"] is False
        assert data["current_track_id"] is None
        assert data["volume"] == 0.8

    def test_play_track_workflow(self, client, db_session, create_test_track):
        """Test le workflow complet de lecture d'une piste."""
        # Créer une piste de test
        track = create_test_track(
            title="Test Track for Play",
            path="/path/to/test_play.mp3",
            bpm=120.0,
            key="C",
        )

        # Démarrer la lecture
        response = client.post(
            f"/api/player/play/{track.id}",
            json={"position": 0.0}
        )
        assert response.status_code == 200
        play_data = response.json()
        assert play_data["is_playing"] is True
        assert play_data["current_track_id"] == track.id

        # Vérifier l'état du player
        response = client.get("/api/player/state")
        assert response.status_code == 200
        state = response.json()
        assert state["is_playing"] is True

    def test_pause_resume_workflow(self, client, db_session, create_test_track):
        """Test le workflow pause/reprise."""
        track = create_test_track(
            title="Test Track for Pause",
            path="/path/to/test_pause.mp3",
        )

        # Démarrer la lecture
        client.post(f"/api/player/play/{track.id}")

        # Mettre en pause
        response = client.post("/api/player/pause")
        assert response.status_code == 200
        pause_data = response.json()
        assert pause_data["is_playing"] is False

        # Reprendre la lecture
        response = client.post("/api/player/resume")
        assert response.status_code == 200
        resume_data = response.json()
        assert resume_data["is_playing"] is True

    def test_skip_next_track(self, client, db_session, sample_queue_tracks):
        """Test le passage à la piste suivante."""
        # Charger la queue avec les pistes de test
        queue_ids = [t.id for t in sample_queue_tracks]

        # Démarrer avec la première piste
        response = client.post(
            f"/api/player/play/{queue_ids[0]}",
            json={"queue": queue_ids}
        )
        assert response.status_code == 200

        # Skip vers la suivante
        response = client.post("/api/player/skip/next")
        assert response.status_code == 200
        skip_data = response.json()
        assert skip_data["current_track_id"] == queue_ids[1]
        assert skip_data["is_playing"] is True

    def test_skip_previous_track(self, client, db_session, sample_queue_tracks):
        """Test le retour à la piste précédente."""
        queue_ids = [t.id for t in sample_queue_tracks]

        # Démarrer avec la deuxième piste
        client.post(
            f"/api/player/play/{queue_ids[1]}",
            json={"queue": queue_ids}
        )

        # Retour à la piste précédente
        response = client.post("/api/player/skip/previous")
        assert response.status_code == 200
        prev_data = response.json()
        assert prev_data["current_track_id"] == queue_ids[0]

    def test_stop_playback(self, client, db_session, create_test_track):
        """Test l'arrêt complet de la lecture."""
        track = create_test_track(
            title="Test Track for Stop",
            path="/path/to/test_stop.mp3",
        )

        # Démarrer la lecture
        client.post(f"/api/player/play/{track.id}")

        # Arrêter
        response = client.post("/api/player/stop")
        assert response.status_code == 200
        stop_data = response.json()
        assert stop_data["is_playing"] is False
        assert stop_data["current_track_id"] is None


@pytest.mark.e2e
@pytest.mark.queue
class TestPlayqueueManagement:
    """Tests pour la gestion de la file de lecture (queue)."""

    @pytest.fixture
    def queue_data(self, db_session):
        """Données pour tester la queue."""
        return create_test_tracks(db_session, count=5)

    def test_add_to_queue(self, client, db_session, create_test_track):
        """Test l'ajout de pistes à la file d'attente."""
        track1 = create_test_track(title="Queue Track 1", path="/path/to/q1.mp3")
        track2 = create_test_track(title="Queue Track 2", path="/path/to/q2.mp3")

        # Ajouter des pistes à la queue
        response = client.post(
            "/api/player/queue/add",
            json={"track_ids": [track1.id, track2.id]}
        )
        assert response.status_code == 200
        queue_response = response.json()
        assert len(queue_response["queue"]) == 2
        assert queue_response["queue"][0]["id"] == track1.id
        assert queue_response["queue"][1]["id"] == track2.id

    def test_clear_queue(self, client, db_session, sample_queue_tracks):
        """Test le vidage de la file d'attente."""
        queue_ids = [t.id for t in sample_queue_tracks]

        # Ajouter des pistes
        client.post(
            "/api/player/queue/add",
            json={"track_ids": queue_ids}
        )

        # Vider la queue
        response = client.post("/api/player/queue/clear")
        assert response.status_code == 200
        clear_data = response.json()
        assert len(clear_data["queue"]) == 0

    def test_remove_from_queue(self, client, db_session, sample_queue_tracks):
        """Test la suppression d'une piste de la queue."""
        queue_ids = [t.id for t in sample_queue_tracks]

        # Ajouter des pistes
        client.post(
            "/api/player/queue/add",
            json={"track_ids": queue_ids}
        )

        # Supprimer la deuxième piste
        response = client.delete(f"/api/player/queue/track/{queue_ids[1]}")
        assert response.status_code == 200
        remove_data = response.json()
        assert len(remove_data["queue"]) == 4

    def test_reorder_queue(self, client, db_session, sample_queue_tracks):
        """Test la réorganisation de la queue."""
        queue_ids = [t.id for t in sample_queue_tracks]

        # Ajouter des pistes
        client.post(
            "/api/player/queue/add",
            json={"track_ids": queue_ids}
        )

        # Inverser l'ordre
        reordered_ids = list(reversed(queue_ids))
        response = client.put(
            "/api/player/queue/reorder",
            json={"track_ids": reordered_ids}
        )
        assert response.status_code == 200
        reorder_data = response.json()
        assert reorder_data["queue"][0]["id"] == queue_ids[-1]

    def test_shuffle_queue(self, client, db_session, sample_queue_tracks):
        """Test l'activation du mode shuffle."""
        queue_ids = [t.id for t in sample_queue_tracks]

        # Activer le shuffle
        response = client.post(
            "/api/player/queue/shuffle",
            json={"track_ids": queue_ids}
        )
        assert response.status_code == 200
        shuffle_data = response.json()
        assert shuffle_data["shuffle"] is True
        # Vérifier que l'ordre a changé
        result_ids = [t["id"] for t in shuffle_data["queue"]]
        assert result_ids != queue_ids

    def test_repeat_mode(self, client, db_session, create_test_track):
        """Test les modes de répétition."""
        track = create_test_track(
            title="Repeat Track",
            path="/path/to/repeat.mp3",
        )

        # Activer repeat all
        response = client.post(
            f"/api/player/repeat/{track.id}",
            json={"mode": "all"}
        )
        assert response.status_code == 200
        repeat_data = response.json()
        assert repeat_data["repeat"] == "all"

        # Activer repeat one
        response = client.post(
            f"/api/player/repeat/{track.id}",
            json={"mode": "one"}
        )
        assert response.status_code == 200
        repeat_one_data = response.json()
        assert repeat_one_data["repeat"] == "one"


@pytest.mark.e2e
@pytest.mark.player
@pytest.mark.websocket
class TestPlayerWebSocketSync:
    """Tests pour la synchronisation WebSocket du player."""

    def test_player_position_sync(self, client, db_session, create_test_track):
        """Test la synchronisation de la position de lecture."""
        track = create_test_track(
            title="Position Sync Track",
            path="/path/to/pos_sync.mp3",
            duration=180.0,
        )

        # Démarrer la lecture
        client.post(f"/api/player/play/{track.id}")

        # Mettre à jour la position
        response = client.put(
            "/api/player/position",
            json={"position": 45.5}
        )
        assert response.status_code == 200
        pos_data = response.json()
        assert pos_data["position"] == 45.5

    def test_volume_control(self, client, db_session, create_test_track):
        """Test le contrôle du volume."""
        track = create_test_track(
            title="Volume Test Track",
            path="/path/to/vol.mp3",
        )

        # Démarrer la lecture
        client.post(f"/api/player/play/{track.id}")

        # Changer le volume
        response = client.put(
            "/api/player/volume",
            json={"volume": 0.5}
        )
        assert response.status_code == 200
        vol_data = response.json()
        assert vol_data["volume"] == 0.5

        # Couper le son
        response = client.put(
            "/api/player/volume",
            json={"muted": True}
        )
        assert response.status_code == 200
        muted_data = response.json()
        assert muted_data["muted"] is True

    def test_playback_history_tracking(self, client, db_session, create_test_track):
        """Test le suivi de l'historique de lecture."""
        track1 = create_test_track(title="History Track 1", path="/path-to/h1.mp3")
        track2 = create_test_track(title="History Track 2", path="/path-to/h2.mp3")

        # Jouer la première piste
        client.post(f"/api/player/play/{track1.id}")
        client.post("/api/player/stop")

        # Jouer la deuxième piste
        client.post(f"/api/player/play/{track2.id}")

        # Vérifier l'historique
        response = client.get("/api/player/history")
        assert response.status_code == 200
        history_data = response.json()
        assert len(history_data) >= 2


@pytest.mark.e2e
@pytest.mark.player
class TestPlayerEdgeCases:
    """Tests des cas limites pour le player."""

    def test_empty_queue_playback(self, client):
        """Test la tentative de lecture sur une queue vide."""
        response = client.post("/api/player/play")
        # Devrait retourner une erreur ou un état approprié
        assert response.status_code in [400, 404]

    def test_invalid_track_id(self, client):
        """Test avec un ID de piste invalide."""
        response = client.post("/api/player/play/999999")
        assert response.status_code == 404

    def test_skip_empty_queue(self, client):
        """Test le skip sur une queue vide."""
        response = client.post("/api/player/skip/next")
        assert response.status_code in [400, 404]

    def test_volume_bounds(self, client, db_session, create_test_track):
        """Test les limites du volume."""
        track = create_test_track(title="Volume Bounds", path="/path-to/vb.mp3")
        client.post(f"/api/player/play/{track.id}")

        # Volume maximum
        response = client.put("/api/player/volume", json={"volume": 1.0})
        assert response.status_code == 200

        # Volume minimum
        response = client.put("/api/player/volume", json={"volume": 0.0})
        assert response.status_code == 200

    def test_concurrent_player_commands(self, client, db_session, create_test_track):
        """Test les commandes concurrentes sur le player."""
        track = create_test_track(title="Concurrent", path="/path-to/conc.mp3")

        # Envoi de plusieurs commandes simultanées
        responses = []
        for _ in range(3):
            response = client.post(f"/api/player/play/{track.id}")
            responses.append(response)

        # Au moins une réponse doit être succès
        assert any(r.status_code == 200 for r in responses)

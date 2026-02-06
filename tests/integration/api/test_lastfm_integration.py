# -*- coding: UTF-8 -*-
"""
Tests d'intégration pour l'API Last.fm.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.api.api_app import create_api


class TestLastFMIntegration:
    """Tests d'intégration pour les fonctionnalités Last.fm."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        app = create_api()
        return TestClient(app)

    @pytest.fixture
    def mock_lastfm_service(self):
        """Mock du service Last.fm."""
        with patch('backend.api.services.lastfm_service.LastFMService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    def test_fetch_artist_lastfm_info_success(self, client, mock_lastfm_service):
        """Test récupération réussie des infos Last.fm d'un artiste."""
        # Mock du résultat du service
        mock_result = {
            "success": True,
            "artist_id": 1,
            "artist_name": "Test Artist",
            "info": {
                "url": "https://www.last.fm/music/Test+Artist",
                "listeners": 1000000,
                "playcount": 50000000,
                "tags": ["electronic", "ambient", "experimental"],
                "fetched_at": "2024-01-15T10:00:00"
            },
            "message": "Last.fm info fetched and stored for Test Artist"
        }
        mock_lastfm_service.fetch_artist_info.return_value = mock_result

        response = client.post("/api/artists/1/lastfm-info")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["artist_id"] == 1
        assert data["artist_name"] == "Test Artist"
        assert "listeners" in data["info"]
        assert "playcount" in data["info"]

        # Vérifier que le service a été appelé
        mock_lastfm_service.fetch_artist_info.assert_called_once_with(1)

    def test_fetch_artist_lastfm_info_not_found(self, client, mock_lastfm_service):
        """Test récupération d'infos Last.fm pour un artiste inexistant."""
        mock_lastfm_service.fetch_artist_info.side_effect = ValueError("Artist with ID 999 not found")

        response = client.post("/api/artists/999/lastfm-info")

        assert response.status_code == 500
        data = response.json()
        assert "Artist with ID 999 not found" in data["detail"]

    def test_fetch_similar_artists_success(self, client, mock_lastfm_service):
        """Test récupération réussie des artistes similaires."""
        mock_result = {
            "success": True,
            "artist_id": 1,
            "artist_name": "Test Artist",
            "similar_artists_fetched": 5,
            "skipped": 2,
            "message": "Fetched and stored 5 similar artists for Test Artist"
        }
        mock_lastfm_service.fetch_similar_artists.return_value = mock_result

        response = client.post("/api/artists/1/similar?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["similar_artists_fetched"] == 5
        assert data["skipped"] == 2

        # Vérifier que le service a été appelé avec les bons paramètres
        mock_lastfm_service.fetch_similar_artists.assert_called_once_with(1, 10)

    def test_fetch_similar_artists_limit_validation(self, client):
        """Test validation des limites pour les artistes similaires."""
        # Test limite trop basse
        response = client.post("/api/artists/1/similar?limit=0")
        assert response.status_code == 422  # Validation error

        # Test limite trop haute
        response = client.post("/api/artists/1/similar?limit=100")
        assert response.status_code == 422  # Validation error

        # Test limite valide
        with patch('backend.api.services.lastfm_service.LastFMService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.fetch_similar_artists.return_value = {"success": True}

            response = client.post("/api/artists/1/similar?limit=25")
            assert response.status_code == 200

    def test_get_similar_artists_success(self, client, mock_lastfm_service):
        """Test récupération des artistes similaires depuis la DB."""
        mock_similar_artists = [
            {
                "id": 2,
                "name": "Similar Artist 1",
                "weight": 0.85,
                "lastfm_url": "https://www.last.fm/music/Similar+Artist+1",
                "listeners": 500000
            },
            {
                "id": 3,
                "name": "Similar Artist 2",
                "weight": 0.72,
                "lastfm_url": "https://www.last.fm/music/Similar+Artist+2",
                "listeners": 300000
            }
        ]
        mock_lastfm_service.get_similar_artists.return_value = mock_similar_artists

        response = client.get("/api/artists/1/similar")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Similar Artist 1"
        assert data[0]["weight"] == 0.85
        assert data[1]["name"] == "Similar Artist 2"
        assert data[1]["weight"] == 0.72

        # Vérifier que le service a été appelé
        mock_lastfm_service.get_similar_artists.assert_called_once_with(1, 10)

    def test_get_similar_artists_empty(self, client, mock_lastfm_service):
        """Test récupération d'artistes similaires quand il n'y en a pas."""
        mock_lastfm_service.get_similar_artists.return_value = []

        response = client.get("/api/artists/1/similar")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_lastfm_service_error_handling(self, client, mock_lastfm_service):
        """Test gestion d'erreurs du service Last.fm."""
        mock_lastfm_service.fetch_artist_info.side_effect = Exception("Last.fm API error")

        response = client.post("/api/artists/1/lastfm-info")

        assert response.status_code == 500
        data = response.json()
        assert "Last.fm API error" in data["detail"]

    @patch('backend.api.services.lastfm_service.pylast.LastFMNetwork')
    def test_lastfm_service_initialization(self, mock_network_class, mock_lastfm_service):
        """Test initialisation du service Last.fm."""
        from backend.api.services.lastfm_service import LastFMService
        from sqlalchemy.orm import Session

        # Mock session
        mock_session = MagicMock(spec=Session)

        # Créer le service
        service = LastFMService(mock_session)

        # Vérifier que le réseau n'est pas initialisé au départ
        assert service._network is None

        # Mock des variables d'environnement
        with patch.dict('os.environ', {
            'LASTFM_API_KEY': 'test_api_key',
            'LASTFM_API_SECRET': 'test_api_secret'
        }):
            # Accéder au réseau (devrait l'initialiser)
            with patch('backend.api.services.lastfm_service.logger') as mock_logger:
                try:
                    _ = service.network
                except Exception:
                    pass  # On s'attend à une erreur car les credentials sont mockés

                # Vérifier que l'initialisation a été tentée
                mock_logger.info.assert_any_call("[LASTFM] Last.fm network initialized")

    def test_lastfm_service_missing_credentials(self):
        """Test que le service échoue sans credentials."""
        from backend.api.services.lastfm_service import LastFMService
        from sqlalchemy.orm import Session

        # Mock session
        mock_session = MagicMock(spec=Session)

        # Créer le service
        service = LastFMService(mock_session)

        # Mock des variables d'environnement manquantes
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="LASTFM_API_KEY and LASTFM_API_SECRET environment variables must be set"):
                _ = service.network

    def test_artist_similar_model_creation(self):
        """Test création du modèle ArtistSimilar."""
        from backend.api.models.artist_similar_model import ArtistSimilar
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        import tempfile
        import os

        # Créer une base temporaire
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            engine = create_engine(f"sqlite:///{temp_db.name}")
            ArtistSimilar.__table__.create(engine)

            Session = sessionmaker(bind=engine)
            session = Session()

            # Créer un objet ArtistSimilar
            similar = ArtistSimilar(
                artist_id=1,
                similar_artist_id=2,
                weight=0.85
            )

            session.add(similar)
            session.commit()

            # Vérifier que l'objet a été créé
            assert similar.id is not None
            assert similar.artist_id == 1
            assert similar.similar_artist_id == 2
            assert similar.weight == 0.85

            session.close()

        finally:
            os.unlink(temp_db.name)

    def test_artist_model_lastfm_fields(self):
        """Test que le modèle Artist a les champs Last.fm."""
        from backend.api.models.artists_model import Artist

        # Vérifier que les champs Last.fm existent
        assert hasattr(Artist, 'lastfm_url')
        assert hasattr(Artist, 'lastfm_listeners')
        assert hasattr(Artist, 'lastfm_playcount')
        assert hasattr(Artist, 'lastfm_tags')
        assert hasattr(Artist, 'lastfm_similar_artists_fetched')
        assert hasattr(Artist, 'lastfm_info_fetched_at')
        assert hasattr(Artist, 'vector')

    def test_worker_celery_integration(self):
        """Test intégration des workers Celery Last.fm."""
        with patch('backend_worker.workers.lastfm.lastfm_worker.celery') as mock_celery:
            from backend_worker.workers.lastfm.lastfm_worker import fetch_artist_lastfm_info

            mock_task = MagicMock()
            mock_task.id = "test-lastfm-task-123"
            mock_celery.send_task.return_value = mock_task

            # Appeler la fonction
            result = fetch_artist_lastfm_info(1)

            # Vérifier que Celery a été appelé
            mock_celery.send_task.assert_called_once_with(
                "lastfm.fetch_artist_info",
                args=[1],
                queue="deferred"
            )

            assert result.id == "test-lastfm-task-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
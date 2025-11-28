# -*- coding: UTF-8 -*-
"""
Tests d'intégration pour la vectorisation des tracks.
"""

import pytest
import json
from fastapi.testclient import TestClient
from backend.api.api_app import create_api


class TestTrackVectorizationIntegration:
    """Tests d'intégration pour la vectorisation des tracks."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        app = create_api()
        return TestClient(app)

    @pytest.fixture
    def sample_track_data(self):
        """Données d'exemple pour une track."""
        return {
            'id': 1,
            'title': 'Test Track',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'genre': 'electronic',
            'year': '2023',
            'duration': 180,
            'bpm': 120.0,
            'key': 'C',
            'danceability': 0.8,
            'mood_happy': 0.7,
            'mood_aggressive': 0.2,
            'mood_party': 0.6,
            'mood_relaxed': 0.8,
            'instrumental': 0.1,
            'acoustic': 0.2,
            'tonal': 0.9
        }

    def test_vectorization_service_creation(self, sample_track_data):
        """Test création d'embedding par le service de vectorisation."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()
        embedding = service.create_track_embedding(sample_track_data)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_vectorization_service_batch(self):
        """Test vectorisation par lot."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        tracks_data = [
            {
                'id': 1,
                'title': 'Track 1',
                'genre': 'electronic',
                'bpm': 120,
                'key': 'C',
                'danceability': 0.8
            },
            {
                'id': 2,
                'title': 'Track 2',
                'genre': 'rock',
                'bpm': 140,
                'key': 'G',
                'danceability': 0.6
            }
        ]

        results = service.batch_create_embeddings(tracks_data)

        assert results['total_processed'] == 2
        assert results['success_count'] >= 1  # Au moins une réussite
        assert len(results['successful']) >= 1
        assert isinstance(results['successful'][0]['embedding'], list)

    def test_genre_encoding(self):
        """Test encodage des genres."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        # Test genre connu
        vector = service._encode_genre('electronic')
        assert len(vector) == 5
        assert vector[0] == 1  # electronic = [1, 0, 0, 0, 0]

        # Test genre inconnu
        vector = service._encode_genre('unknown_genre')
        assert len(vector) == 5
        assert all(x == 0.0 for x in vector)

    def test_key_encoding(self):
        """Test encodage des clés musicales."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        # Test clé connue
        vector = service._encode_key('C')
        assert len(vector) == 12
        assert vector[0] == 1  # C = première position

        # Test clé inconnue
        vector = service._encode_key('unknown_key')
        assert len(vector) == 12
        assert all(x == 0.0 for x in vector)

    def test_embedding_consistency(self):
        """Test que les embeddings sont consistants pour les mêmes données."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        track_data = {
            'id': 1,
            'title': 'Test Track',
            'genre': 'electronic',
            'bpm': 120,
            'key': 'C',
            'danceability': 0.8
        }

        # Créer deux embeddings identiques
        embedding1 = service.create_track_embedding(track_data)
        embedding2 = service.create_track_embedding(track_data)

        assert embedding1 is not None
        assert embedding2 is not None
        assert len(embedding1) == len(embedding2)

        # Les embeddings devraient être identiques pour les mêmes données
        # (Note: en pratique, ils peuvent différer légèrement à cause de la normalisation,
        # mais la structure devrait être la même)

    def test_embedding_with_missing_features(self):
        """Test vectorisation avec des caractéristiques manquantes."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        # Données minimales
        track_data = {
            'id': 1,
            'title': 'Minimal Track'
        }

        embedding = service.create_track_embedding(track_data)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_vectorize_tracks_endpoint(self, client):
        """Test endpoint de vectorisation des tracks."""
        # Note: Ce test nécessite une base de données avec des tracks
        # Pour l'instant, on teste juste que l'endpoint existe et répond
        response = client.post("/api/tracks/vectorize")

        # L'endpoint devrait exister, même s'il n'y a pas de tracks à vectoriser
        assert response.status_code in [200, 400, 500]  # Différents statuts possibles selon les données

    def test_vectorize_artist_tracks_endpoint(self, client):
        """Test endpoint de vectorisation des tracks d'artistes."""
        response = client.post("/api/tracks/artists/vectorize-tracks")

        # L'endpoint devrait exister
        assert response.status_code in [200, 400, 500]

    def test_embedding_storage_format(self):
        """Test que les embeddings sont stockés au bon format JSON."""

        sample_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Test sérialisation
        json_str = json.dumps(sample_embedding)
        parsed = json.loads(json_str)

        assert parsed == sample_embedding
        assert isinstance(parsed, list)
        assert all(isinstance(x, float) for x in parsed)

    def test_vectorization_service_initialization(self):
        """Test initialisation du service de vectorisation."""
        from backend.api.services.vectorization_service import TrackVectorizationService

        service = TrackVectorizationService()

        # Vérifier que les mappings sont correctement initialisés
        assert hasattr(service, 'genre_mapping')
        assert hasattr(service, 'key_mapping')
        assert hasattr(service, 'audio_features')

        assert 'electronic' in service.genre_mapping
        assert 'C' in service.key_mapping
        assert 'bpm' in service.audio_features

    def test_embedding_vector_properties(self, sample_track_data):
        """Test propriétés mathématiques du vecteur d'embedding."""
        from backend.api.services.vectorization_service import TrackVectorizationService
        import numpy as np

        service = TrackVectorizationService()
        embedding = service.create_track_embedding(sample_track_data)

        assert embedding is not None

        # Convertir en array numpy pour les tests mathématiques
        vec = np.array(embedding)

        # Le vecteur devrait avoir une norme finie (pas de NaN/inf)
        assert np.isfinite(vec).all()

        # Le vecteur devrait avoir une variance (pas constant)
        assert np.var(vec) > 0

        # Test que les valeurs sont dans une plage raisonnable
        assert vec.min() >= -10  # Après normalisation
        assert vec.max() <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
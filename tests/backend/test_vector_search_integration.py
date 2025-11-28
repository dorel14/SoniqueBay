# -*- coding: UTF-8 -*-
"""
Tests d'intégration pour la recherche vectorielle avec sqlite-vec.
"""

import pytest
import numpy as np
from backend.api.services.vector_search_service import VectorSearchService


class TestVectorSearchIntegration:
    """Tests d'intégration pour le service de recherche vectorielle."""

    @pytest.fixture
    def vector_service(self):
        """Service de recherche vectorielle."""
        return VectorSearchService()

    @pytest.fixture
    def sample_embeddings(self):
        """Embeddings d'exemple pour les tests."""
        return {
            "electronic_track": [1.0, 0.8, 0.6, 0.4, 0.2] + [0.0] * 20,  # Electronic genre
            "rock_track": [0.2, 1.0, 0.8, 0.6, 0.4] + [0.0] * 20,  # Rock genre
            "jazz_track": [0.1, 0.3, 0.1, 1.0, 0.8] + [0.0] * 20,  # Jazz genre
            "pop_track": [0.8, 0.4, 1.0, 0.2, 0.6] + [0.0] * 20,  # Pop genre
        }

    def test_add_and_retrieve_track_embedding(self, vector_service):
        """Test ajout et récupération d'embedding de track."""
        track_id = 999
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 20

        # Add embedding
        success = vector_service.add_track_embedding(track_id, embedding)
        assert success

        # Retrieve embedding
        retrieved = vector_service.get_track_embedding(track_id)
        assert retrieved is not None
        assert len(retrieved) == len(embedding)

        # Check values are close (floating point precision)
        np.testing.assert_allclose(retrieved, embedding, rtol=1e-6)

    def test_add_and_retrieve_artist_embedding(self, vector_service):
        """Test ajout et récupération d'embedding d'artiste."""
        artist_name = "Test Artist"
        embedding = [0.5, 0.4, 0.3, 0.2, 0.1] + [0.0] * 20

        # Add embedding
        success = vector_service.add_artist_embedding(artist_name, embedding)
        assert success

        # Retrieve embedding
        retrieved = vector_service.get_artist_embedding(artist_name)
        assert retrieved is not None
        assert len(retrieved) == len(embedding)

        # Check values are close
        np.testing.assert_allclose(retrieved, embedding, rtol=1e-6)

    def test_similar_tracks_search(self, vector_service, sample_embeddings):
        """Test recherche de tracks similaires."""
        # Add sample embeddings
        for i, (track_type, embedding) in enumerate(sample_embeddings.items()):
            vector_service.add_track_embedding(i + 1, embedding)

        # Search for tracks similar to electronic track
        query_embedding = sample_embeddings["electronic_track"]
        similar_tracks = vector_service.find_similar_tracks(query_embedding, limit=3)

        assert len(similar_tracks) > 0
        assert all("track_id" in track for track in similar_tracks)
        assert all("distance" in track for track in similar_tracks)
        assert all("similarity_score" in track for track in similar_tracks)

        # Most similar should be the electronic track itself
        most_similar = similar_tracks[0]
        assert most_similar["similarity_score"] > 0.8  # High similarity with itself

    def test_similar_artists_search(self, vector_service):
        """Test recherche d'artistes similaires."""
        # Add sample artist embeddings
        artists = [
            ("Electronic Artist", [1.0, 0.8, 0.6, 0.4, 0.2] + [0.0] * 20),
            ("Rock Artist", [0.2, 1.0, 0.8, 0.6, 0.4] + [0.0] * 20),
            ("Jazz Artist", [0.1, 0.3, 0.1, 1.0, 0.8] + [0.0] * 20),
        ]

        for artist_name, embedding in artists:
            vector_service.add_artist_embedding(artist_name, embedding)

        # Search for artists similar to Electronic Artist
        query_embedding = artists[0][1]  # Electronic artist embedding
        similar_artists = vector_service.find_similar_artists(query_embedding, limit=2)

        assert len(similar_artists) > 0
        assert all("artist_name" in artist for artist in similar_artists)
        assert all("distance" in artist for artist in similar_artists)
        assert all("similarity_score" in artist for artist in similar_artists)

    def test_batch_add_embeddings(self, vector_service):
        """Test ajout par lot d'embeddings."""
        # Prepare batch data
        track_embeddings = [
            {"track_id": 1001, "embedding": [0.1, 0.2, 0.3] + [0.0] * 22},
            {"track_id": 1002, "embedding": [0.4, 0.5, 0.6] + [0.0] * 22},
            {"track_id": 1003, "embedding": [0.7, 0.8, 0.9] + [0.0] * 22},
        ]

        # Add batch
        result = vector_service.batch_add_track_embeddings(track_embeddings)

        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["total"] == 3

        # Verify embeddings were added
        for data in track_embeddings:
            retrieved = vector_service.get_track_embedding(data["track_id"])
            assert retrieved is not None
            np.testing.assert_allclose(retrieved, data["embedding"], rtol=1e-6)

    def test_batch_add_artist_embeddings(self, vector_service):
        """Test ajout par lot d'embeddings d'artistes."""
        # Prepare batch data
        artist_embeddings = [
            {"artist_name": "Batch Artist 1", "embedding": [0.1, 0.2, 0.3] + [0.0] * 22},
            {"artist_name": "Batch Artist 2", "embedding": [0.4, 0.5, 0.6] + [0.0] * 22},
        ]

        # Add batch
        result = vector_service.batch_add_artist_embeddings(artist_embeddings)

        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2

        # Verify embeddings were added
        for data in artist_embeddings:
            retrieved = vector_service.get_artist_embedding(data["artist_name"])
            assert retrieved is not None
            np.testing.assert_allclose(retrieved, data["embedding"], rtol=1e-6)

    def test_similarity_score_calculation(self, vector_service):
        """Test calcul des scores de similarité."""
        # Add two similar embeddings
        embedding1 = [1.0, 0.9, 0.8] + [0.0] * 22
        embedding2 = [0.9, 1.0, 0.7] + [0.0] * 22

        vector_service.add_track_embedding(1, embedding1)
        vector_service.add_track_embedding(2, embedding2)

        # Search with embedding1 as query
        similar = vector_service.find_similar_tracks(embedding1, limit=2)

        assert len(similar) >= 1

        # The most similar should be track 1 itself
        most_similar = similar[0]
        assert most_similar["track_id"] == 1
        assert most_similar["similarity_score"] > 0.9  # Very high similarity with itself

        # Check that similarity scores are between 0 and 1
        for result in similar:
            assert 0 <= result["similarity_score"] <= 1

    def test_vector_database_stats(self, vector_service):
        """Test récupération des statistiques de la base vectorielle."""
        # Add some test data
        vector_service.add_track_embedding(1, [0.1] * 25)
        vector_service.add_track_embedding(2, [0.2] * 25)
        vector_service.add_artist_embedding("Test Artist", [0.3] * 25)

        # Get stats
        stats = vector_service.get_stats()

        assert "tracks_with_embeddings" in stats
        assert "artists_with_embeddings" in stats
        assert "total_embeddings" in stats

        assert stats["tracks_with_embeddings"] >= 2
        assert stats["artists_with_embeddings"] >= 1
        assert stats["total_embeddings"] >= 3

    def test_embedding_update(self, vector_service):
        """Test mise à jour d'embedding existant."""
        track_id = 777
        original_embedding = [0.1, 0.2, 0.3] + [0.0] * 22
        updated_embedding = [0.9, 0.8, 0.7] + [0.0] * 22

        # Add original
        success1 = vector_service.add_track_embedding(track_id, original_embedding)
        assert success1

        # Verify original
        retrieved1 = vector_service.get_track_embedding(track_id)
        np.testing.assert_allclose(retrieved1, original_embedding, rtol=1e-6)

        # Update with new embedding
        success2 = vector_service.add_track_embedding(track_id, updated_embedding)
        assert success2

        # Verify updated
        retrieved2 = vector_service.get_track_embedding(track_id)
        np.testing.assert_allclose(retrieved2, updated_embedding, rtol=1e-6)

    def test_nonexistent_embedding(self, vector_service):
        """Test récupération d'embedding inexistant."""
        # Try to get embedding for non-existent track/artist
        track_embedding = vector_service.get_track_embedding(99999)
        artist_embedding = vector_service.get_artist_embedding("NonExistent Artist")

        assert track_embedding is None
        assert artist_embedding is None

    def test_empty_similar_search(self, vector_service):
        """Test recherche similaire sans données."""
        # Search without any data in the vector database
        query_embedding = [0.5] * 25
        similar_tracks = vector_service.find_similar_tracks(query_embedding)
        similar_artists = vector_service.find_similar_artists(query_embedding)

        # Should return empty lists, not crash
        assert isinstance(similar_tracks, list)
        assert isinstance(similar_artists, list)
        assert len(similar_tracks) == 0
        assert len(similar_artists) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
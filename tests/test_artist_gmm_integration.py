# -*- coding: UTF-8 -*-
"""
Tests d'intégration pour le système GMM des artistes.

Tests complets du pipeline : génération d'embeddings → entraînement GMM → recommandations.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.api.services.artist_embedding_service import ArtistEmbeddingService
from backend.api.schemas.artist_embeddings_schema import (
    ArtistEmbeddingCreate,
    GMMTrainingRequest
)


class TestArtistGMMIntegration:
    """Tests d'intégration du système GMM pour les artistes."""

    @pytest.fixture
    def sample_embeddings_data(self):
        """Données d'exemple pour les tests d'embeddings."""
        return [
            {
                "artist_name": "Artist_1",
                "vector": [0.1, 0.2, 0.3, 0.4, 0.5] * 5,  # Vecteur de dimension 25
                "cluster": None,
                "cluster_probabilities": None
            },
            {
                "artist_name": "Artist_2",
                "vector": [0.2, 0.3, 0.4, 0.5, 0.6] * 5,
                "cluster": None,
                "cluster_probabilities": None
            },
            {
                "artist_name": "Artist_3",
                "vector": [0.3, 0.4, 0.5, 0.6, 0.7] * 5,
                "cluster": None,
                "cluster_probabilities": None
            },
            {
                "artist_name": "Artist_4",
                "vector": [0.4, 0.5, 0.6, 0.7, 0.8] * 5,
                "cluster": None,
                "cluster_probabilities": None
            },
            {
                "artist_name": "Artist_5",
                "vector": [0.5, 0.6, 0.7, 0.8, 0.9] * 5,
                "cluster": None,
                "cluster_probabilities": None
            }
        ]

    def test_full_gmm_pipeline(self, db_session, sample_embeddings_data):
        """Test du pipeline complet GMM : création → entraînement → recommandations."""
        service = ArtistEmbeddingService(db_session)

        # Étape 1: Créer les embeddings
        embeddings = []
        for data in sample_embeddings_data:
            embedding_data = ArtistEmbeddingCreate(**data)
            embedding = service.create_embedding(embedding_data)
            embeddings.append(embedding)
            assert embedding.artist_name == data["artist_name"]
            assert embedding.cluster is None  # Pas encore clusterisé

        # Vérifier que tous les embeddings ont été créés
        assert len(embeddings) == 5

        # Étape 2: Entraîner le GMM
        training_request = GMMTrainingRequest(
            n_components=2,  # 2 clusters pour 5 artistes
            max_iterations=50
        )

        result = service.train_gmm(training_request)

        # Vérifier le résultat de l'entraînement
        assert result.success is True
        assert result.n_components == 2
        assert result.n_artists == 5
        assert result.log_likelihood is not None
        assert result.training_time > 0

        # Étape 3: Vérifier que les clusters ont été assignés
        for embedding in embeddings:
            updated = service.get_embedding_by_artist(embedding.artist_name)
            assert updated.cluster is not None  # Doit avoir un cluster assigné
            assert updated.cluster_probabilities is not None  # Doit avoir des probabilités

            # Vérifier que les probabilités sont valides
            probs = updated.cluster_probabilities
            assert isinstance(probs, dict)
            assert len(probs) == 2  # 2 clusters
            assert all(isinstance(p, float) and 0 <= p <= 1 for p in probs.values())

        # Étape 4: Tester les recommandations de similarité
        similar_artists = service.get_similar_artists("Artist_1", limit=3)

        assert similar_artists.artist_name == "Artist_1"
        assert similar_artists.cluster_based is True
        assert len(similar_artists.similar_artists) > 0

        # Vérifier la structure des recommandations
        for rec in similar_artists.similar_artists:
            assert "artist_name" in rec
            assert "cluster" in rec
            assert "similarity_score" in rec
            assert isinstance(rec["similarity_score"], float)
            assert 0 <= rec["similarity_score"] <= 1

    def test_gmm_with_insufficient_data(self, db_session):
        """Test GMM avec données insuffisantes."""
        service = ArtistEmbeddingService(db_session)

        # Créer seulement 1 embedding
        embedding_data = ArtistEmbeddingCreate(
            artist_name="Single_Artist",
            vector=[0.1, 0.2, 0.3, 0.4, 0.5] * 5
        )
        service.create_embedding(embedding_data)

        # Tenter d'entraîner GMM avec 3 composants mais seulement 1 artiste
        training_request = GMMTrainingRequest(n_components=3, max_iterations=10)

        result = service.train_gmm(training_request)

        # Doit échouer car pas assez de données
        assert result.success is False
        assert "Not enough embeddings" in result.message or "Not enough valid vectors" in result.message

    def test_cluster_info_endpoint(self, db_session, sample_embeddings_data):
        """Test de récupération des informations de cluster."""
        service = ArtistEmbeddingService(db_session)

        # Sans données
        info = service.get_cluster_info()
        assert info["total_artists"] == 0
        assert info["clusters"] == {}
        assert info["gmm_model"] is None

        # Avec données mais sans GMM entraîné
        for data in sample_embeddings_data:
            embedding_data = ArtistEmbeddingCreate(**data)
            service.create_embedding(embedding_data)

        info = service.get_cluster_info()
        assert info["total_artists"] == 5
        assert info["clusters"] == {}  # Pas de clusters assignés
        assert info["gmm_model"] is None

        # Après entraînement GMM
        training_request = GMMTrainingRequest(n_components=2)
        service.train_gmm(training_request)

        info = service.get_cluster_info()
        assert info["total_artists"] == 5
        assert len(info["clusters"]) > 0  # Doit avoir des clusters
        assert info["gmm_model"] is not None
        assert info["gmm_model"]["n_components"] == 2

    def test_embedding_crud_operations(self, db_session):
        """Test des opérations CRUD sur les embeddings."""
        service = ArtistEmbeddingService(db_session)

        # Créer
        embedding_data = ArtistEmbeddingCreate(
            artist_name="Test_Artist",
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            cluster=1,
            cluster_probabilities={"0": 0.3, "1": 0.7}
        )

        created = service.create_embedding(embedding_data)
        assert created.artist_name == "Test_Artist"
        assert created.cluster == 1

        # Lire
        retrieved = service.get_embedding_by_artist("Test_Artist")
        assert retrieved is not None
        assert retrieved.artist_name == "Test_Artist"

        # Mettre à jour
        from backend.api.schemas.artist_embeddings_schema import ArtistEmbeddingUpdate
        update_data = ArtistEmbeddingUpdate(cluster=2)
        updated = service.update_embedding("Test_Artist", update_data)
        assert updated.cluster == 2

        # Supprimer
        deleted = service.delete_embedding("Test_Artist")
        assert deleted is True

        # Vérifier suppression
        retrieved_after_delete = service.get_embedding_by_artist("Test_Artist")
        assert retrieved_after_delete is None

    def test_similarity_scoring(self, db_session):
        """Test du calcul des scores de similarité."""
        service = ArtistEmbeddingService(db_session)

        # Créer des embeddings avec des probabilités connues
        artists_data = [
            {
                "artist_name": "Artist_A",
                "vector": [0.1] * 10,
                "cluster": 0,
                "cluster_probabilities": {"0": 0.8, "1": 0.2}
            },
            {
                "artist_name": "Artist_B",
                "vector": [0.2] * 10,
                "cluster": 0,
                "cluster_probabilities": {"0": 0.7, "1": 0.3}
            },
            {
                "artist_name": "Artist_C",
                "vector": [0.3] * 10,
                "cluster": 1,
                "cluster_probabilities": {"0": 0.2, "1": 0.8}
            }
        ]

        for data in artists_data:
            embedding_data = ArtistEmbeddingCreate(**data)
            service.create_embedding(embedding_data)

        # Tester similarité
        similar = service.get_similar_artists("Artist_A", limit=5)

        assert similar.artist_name == "Artist_A"
        assert len(similar.similar_artists) >= 1

        # Artist_B devrait être plus similaire à Artist_A qu'Artist_C
        # (même cluster avec probabilités similaires)
        artist_b_score = None
        artist_c_score = None

        for rec in similar.similar_artists:
            if rec["artist_name"] == "Artist_B":
                artist_b_score = rec["similarity_score"]
            elif rec["artist_name"] == "Artist_C":
                artist_c_score = rec["similarity_score"]

        if artist_b_score is not None and artist_c_score is not None:
            assert artist_b_score >= artist_c_score  # Artist_B devrait être plus similaire

    @pytest.mark.asyncio
    async def test_celery_worker_integration(self, db_session, sample_embeddings_data):
        """Test d'intégration avec les workers Celery."""
        # Ce test nécessite que les workers Celery soient disponibles
        # Dans un environnement de test réel, on mockerait les appels Celery

        from backend_worker.workers.artist_gmm.artist_gmm_worker import (
            generate_artist_embeddings,
            train_artist_gmm,
            update_artist_clusters
        )

        # Mock pour éviter les vraies dépendances Celery
        with patch('backend_worker.workers.artist_gmm.artist_gmm_worker.celery') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-task-id"
            mock_celery.send_task.return_value = mock_task

            # Tester génération d'embeddings
            result = generate_artist_embeddings()
            assert result is not None

            # Tester entraînement GMM
            result = train_artist_gmm(n_components=2)
            assert result is not None

            # Tester mise à jour des clusters
            result = update_artist_clusters()
            assert result is not None

    def test_error_handling(self, db_session):
        """Test de la gestion d'erreurs."""
        service = ArtistEmbeddingService(db_session)

        # Tester artiste inexistant
        similar = service.get_similar_artists("NonExistent_Artist")
        assert similar.artist_name == "NonExistent_Artist"
        assert similar.similar_artists == []
        assert similar.cluster_based is False

        # Tester suppression d'artiste inexistant
        deleted = service.delete_embedding("NonExistent_Artist")
        assert deleted is False

        # Tester mise à jour d'artiste inexistant
        from backend.api.schemas.artist_embeddings_schema import ArtistEmbeddingUpdate
        updated = service.update_embedding("NonExistent_Artist", ArtistEmbeddingUpdate(cluster=1))
        assert updated is None


if __name__ == "__main__":
    # Exécuter les tests si appelé directement
    pytest.main([__file__, "-v"])
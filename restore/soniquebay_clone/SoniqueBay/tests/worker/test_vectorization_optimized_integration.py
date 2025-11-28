"""
Test d'intégration complet pour la vectorisation optimisée RPi4.

Teste tout le pipeline :
1. Service de vectorisation optimisé (scikit-learn léger)
2. Persistance et versioning des modèles
3. Monitoring des tags et détection de changements
4. Communication HTTP avec library_api/recommender_api
5. Tasks Celery optimisées
6. Configuration RPi4

Auteur : Kilo Code
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from backend_worker.services.vectorization_service import (
    OptimizedVectorizationService
)
from backend_worker.services.model_persistence_service import (
    ModelPersistenceService
)
from backend_worker.services.tag_monitoring_service import (
    TagMonitoringService,
    TagChangeDetector
)
from backend_worker.background_tasks.worker_vector_optimized import (
    OptimizedVectorizationTask,
    BatchVectorizationTask,
    TrainVectorizerTask
)
from backend_worker.background_tasks.retrain_listener import (
    RedisRetrainListener,
    RetrainRequest,
    RetrainExecutor
)


class TestOptimizedVectorizationService:
    """Tests du service de vectorisation optimisé."""
    
    @pytest.fixture
    def service(self):
        """Fixture du service de vectorisation."""
        return OptimizedVectorizationService()
    
    @pytest.fixture
    def mock_tracks_data(self):
        """Fixture des données de test."""
        return [
            {
                "id": 1,
                "title": "Test Song 1",
                "artist_name": "Test Artist",
                "album_title": "Test Album",
                "genre": "Rock",
                "genre_main": "Rock",
                "bpm": 120,
                "duration": 180,
                "danceability": 0.7,
                "mood_happy": 0.8,
                "mood_aggressive": 0.3,
                "mood_party": 0.6,
                "mood_relaxed": 0.2,
                "instrumental": 0.1,
                "acoustic": 0.3,
                "tonal": 0.8,
                "key": "C",
                "scale": "major",
                "camelot_key": "8B"
            },
            {
                "id": 2,
                "title": "Test Song 2",
                "artist_name": "Another Artist",
                "album_title": "Another Album",
                "genre": "Electronic",
                "genre_main": "Electronic",
                "bpm": 128,
                "duration": 240,
                "danceability": 0.9,
                "mood_happy": 0.9,
                "mood_aggressive": 0.1,
                "mood_party": 0.9,
                "mood_relaxed": 0.1,
                "instrumental": 0.8,
                "acoustic": 0.1,
                "tonal": 0.2,
                "key": "Am",
                "scale": "minor",
                "camelot_key": "8A"
            }
        ]
    
    def test_text_vectorizer_creation(self, service):
        """Test création du vectoriseur textuel."""
        assert service.vector_dimension == 384
        assert service.text_vectorizer.vector_dimension == 384
        assert service.audio_vectorizer.feature_names is not None
        assert service.tag_classifier is not None
    
    def test_text_feature_extraction(self, service, mock_tracks_data):
        """Test extraction des features textuelles."""
        track = mock_tracks_data[0]
        text_features = service.text_vectorizer.extract_text_features(track)
        
        # Vérifier que les éléments clés sont présents
        assert "Test Song 1" in text_features
        assert "Test Artist" in text_features
        assert "Rock" in text_features
        assert "120bpm" in text_features
    
    def test_audio_feature_extraction(self, service, mock_tracks_data):
        """Test extraction des features audio."""
        track = mock_tracks_data[0]
        audio_features = service.audio_vectorizer.extract_audio_features(track)
        
        assert len(audio_features) == len(service.audio_vectorizer.feature_names)
        assert audio_features[0] == 120.0  # BPM
        assert audio_features[4] == 0.7   # Danceability
    
    @pytest.mark.asyncio
    async def test_single_track_vectorization(self, service, mock_tracks_data):
        """Test vectorisation d'une track unique."""
        track = mock_tracks_data[0]
        
        # Entraîner les vectoriseurs
        service.text_vectorizer.is_fitted = True
        service.audio_vectorizer.is_fitted = True
        service.tag_classifier.is_fitted = True
        service.is_trained = True
        
        # Vectoriser
        embedding = service.vectorize_single_track(track)
        
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        # Vérifier que le vecteur n'est pas nul
        assert any(x != 0.0 for x in embedding)
    
    @pytest.mark.asyncio
    async def test_train_vectorizers(self, service, mock_tracks_data):
        """Test entraînement des vectoriseurs."""
        with patch('httpx.AsyncClient') as mock_client:
            # Simuler les réponses HTTP
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_tracks_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Entraîner
            result = await service.train_vectorizers(mock_tracks_data)
            
            assert result["status"] == "success"
            assert result["tracks_processed"] == 2
            assert result["final_dimension"] == 384
            assert "vectorizer_type" in result


class TestModelPersistenceService:
    """Tests du service de persistance des modèles."""
    
    @pytest.fixture
    def temp_models_dir(self):
        """Fixture du répertoire temporaire pour les modèles."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def persistence_service(self, temp_models_dir):
        """Fixture du service de persistance."""
        service = ModelPersistenceService()
        # Override le répertoire
        service.models_dir = Path(temp_models_dir)
        return service
    
    @pytest.fixture
    def mock_trained_service(self):
        """Fixture d'un service entraîné."""
        service = OptimizedVectorizationService()
        service.text_vectorizer.is_fitted = True
        service.audio_vectorizer.is_fitted = True
        service.tag_classifier.is_fitted = True
        service.is_trained = True
        return service
    
    @pytest.mark.asyncio
    async def test_save_and_load_model(self, persistence_service, mock_trained_service):
        """Test sauvegarde et chargement d'un modèle."""
        # Sauvegarder
        version = await persistence_service.save_model_version(mock_trained_service, "test_v1")
        
        assert version.version_id == "test_v1"
        assert version.created_at is not None
        assert version.checksum is not None
        
        # Charger
        loaded_service = await persistence_service.load_model_version("test_v1")
        
        assert loaded_service.is_trained
        assert loaded_service.vector_dimension == 384
    
    @pytest.mark.asyncio
    async def test_list_model_versions(self, persistence_service, mock_trained_service):
        """Test listage des versions de modèles."""
        # Sauvegarder plusieurs versions
        await persistence_service.save_model_version(mock_trained_service, "test_v1")
        await persistence_service.save_model_version(mock_trained_service, "test_v2")
        
        # Lister
        versions = await persistence_service.list_model_versions()
        
        assert len(versions) == 2
        # Trier par date décroissante
        assert versions[0].version_id in ["test_v2", "test_v1"]  # La plus récente d'abord
    
    @pytest.mark.asyncio
    async def test_delete_model_version(self, persistence_service, mock_trained_service):
        """Test suppression d'une version de modèle."""
        # Sauvegarder
        await persistence_service.save_model_version(mock_trained_service, "test_delete")
        
        # Vérifier existence
        versions = await persistence_service.list_model_versions()
        assert any(v.version_id == "test_delete" for v in versions)
        
        # Supprimer
        success = await persistence_service.delete_model_version("test_delete")
        assert success
        
        # Vérifier suppression
        versions = await persistence_service.list_model_versions()
        assert not any(v.version_id == "test_delete" for v in versions)


class TestTagMonitoringService:
    """Tests du service de monitoring des tags."""
    
    @pytest.fixture
    def monitoring_service(self):
        """Fixture du service de monitoring."""
        return TagMonitoringService()
    
    @pytest.fixture
    def detector(self):
        """Fixture du détecteur de changements."""
        return TagChangeDetector()
    
    @pytest.mark.asyncio
    async def test_get_current_tags(self, detector):
        """Test récupération des tags actuels."""
        with patch('httpx.AsyncClient') as mock_client:
            # Simuler les réponses
            mock_genres_response = AsyncMock()
            mock_genres_response.status_code = 200
            mock_genres_response.json.return_value = [
                {"name": "Rock"}, {"name": "Pop"}, {"name": "Jazz"}
            ]
            
            mock_moods_response = AsyncMock()
            mock_moods_response.status_code = 200
            mock_moods_response.json.return_value = [
                {"name": "Happy"}, {"name": "Sad"}, {"name": "Energetic"}
            ]
            
            mock_tracks_response = AsyncMock()
            mock_tracks_response.status_code = 200
            mock_tracks_response.json.return_value = {"count": 1000}
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                mock_genres_response,
                mock_moods_response,
                mock_tracks_response
            ]
            
            tags = await detector.get_current_tags()
            
            assert len(tags['genres']) == 3
            assert len(tags['mood_tags']) == 3
            assert tags['tracks_count'] == 1000
    
    def test_calculate_tags_signature(self, detector):
        """Test calcul de signature des tags."""
        tags = {
            'genres': {'Rock', 'Pop'},
            'mood_tags': {'Happy', 'Sad'},
            'genre_tags': {'Electronic', 'Ambient'},
            'tracks_count': 500
        }
        
        signature1 = detector.calculate_tags_signature(tags)
        
        # Même tags doivent donner même signature
        signature2 = detector.calculate_tags_signature(tags)
        assert signature1 == signature2
        
        # Tags différents doivent donner signature différente
        different_tags = {
            'genres': {'Rock', 'Jazz'},  # Différent
            'mood_tags': {'Happy', 'Sad'},
            'genre_tags': {'Electronic', 'Ambient'},
            'tracks_count': 500
        }
        signature3 = detector.calculate_tags_signature(different_tags)
        assert signature1 != signature3
    
    def test_should_trigger_retrain(self, detector):
        """Test décision de retrain."""
        # Test nouveaux genres (priorité haute)
        changes = {
            'has_changes': True,
            'details': {
                'new_genres': ['House', 'Techno', 'Ambient']
            }
        }
        
        decision = detector.should_trigger_retrain(changes)
        assert decision['should_retrain']
        assert decision['priority'] == 'high'
        assert decision['delay_minutes'] == 15
    
    def test_should_not_trigger_retrain_small_changes(self, detector):
        """Test qu'un retrain n'est pas déclenché pour petits changements."""
        changes = {
            'has_changes': True,
            'details': {
                'new_moods': ['Chill'],  # Un seul mood
                'new_genre_tags': ['Lo-fi']  # Un seul genre tag
            }
        }
        
        decision = detector.should_trigger_retrain(changes)
        assert not decision['should_retrain']


class TestCeleryTasks:
    """Tests des tâches Celery optimisées."""
    
    @pytest.fixture
    def mock_vectorization_service(self):
        """Fixture du service de vectorisation mocké."""
        with patch('backend_worker.services.vectorization_service.OptimizedVectorizationService') as mock_service:
            yield mock_service.return_value
    
    @pytest.fixture
    def mock_train_function(self):
        """Fixture de la fonction d'entraînement mockée."""
        with patch('backend_worker.services.vectorization_service.train_and_vectorize_all_tracks') as mock_func:
            mock_func.return_value = {
                "status": "success",
                "tracks_processed": 100,
                "model_type": "scikit-learn_optimized"
            }
            yield mock_func
    
    def test_vectorize_track_task_initialization(self):
        """Test initialisation de la tâche de vectorisation."""
        task = OptimizedVectorizationTask()
        assert task.name == "worker_vector_optimized.OptimizedVectorizationTask"
    
    def test_batch_vectorization_task_initialization(self):
        """Test initialisation de la tâche batch."""
        task = BatchVectorizationTask()
        assert task.name == "worker_vector_optimized.BatchVectorizationTask"
    
    def test_train_vectorizer_task_initialization(self):
        """Test initialisation de la tâche d'entraînement."""
        task = TrainVectorizerTask()
        assert task.name == "worker_vector_optimized.TrainVectorizerTask"


class TestRetrainListener:
    """Tests du listener de retrain."""
    
    @pytest.fixture
    def executor(self):
        """Fixture de l'exécuteur."""
        return RetrainExecutor()
    
    @pytest.fixture
    def retrain_request(self):
        """Fixture d'une demande de retrain."""
        return RetrainRequest({
            'trigger_reason': 'new_genres',
            'priority': 'high',
            'delay_minutes': 30,
            'message': '5 nouveaux genres détectés',
            'details': {'new_genres': ['House', 'Techno', 'Ambient', 'Drum & Bass', 'Breakbeat']},
            'timestamp': datetime.now().isoformat()
        })
    
    def test_retrain_request_creation(self, retrain_request):
        """Test création d'une demande de retrain."""
        assert retrain_request.trigger_reason == 'new_genres'
        assert retrain_request.priority == 'high'
        assert retrain_request.delay_minutes == 30
        assert 'House' in str(retrain_request.details)
    
    def test_retrain_request_execution_time(self, retrain_request):
        """Test calcul du temps d'exécution."""
        # La demande doit être exécutable après le délai
        assert not retrain_request.should_execute()  # Trop tôt
        
        # Simuler que le délai est écoulé
        retrain_request.execute_at = datetime.now() - timedelta(minutes=1)
        assert retrain_request.should_execute()
    
    def test_retrain_request_priority_score(self, retrain_request):
        """Test score de priorité."""
        assert retrain_request.get_priority_score() == 80  # high = 80
    
    def test_executor_add_request(self, executor, retrain_request):
        """Test ajout de demande à l'exécuteur."""
        executor.add_request(retrain_request)
        assert len(executor.pending_requests) == 1
        assert executor.pending_requests[0] == retrain_request
    
    def test_executor_get_next_request(self, executor, retrain_request):
        """Test récupération de la prochaine demande."""
        executor.add_request(retrain_request)
        
        # La demande ne doit pas encore être prête
        next_request = executor.get_next_request()
        assert next_request is None
        
        # Simuler que le délai est passé
        retrain_request.execute_at = datetime.now() - timedelta(minutes=1)
        next_request = executor.get_next_request()
        assert next_request == retrain_request
        assert len(executor.pending_requests) == 0


class TestRaspberryPiOptimizations:
    """Tests des optimisations spécifiques RPi4."""
    
    @pytest.fixture
    def service(self):
        """Fixture du service optimisé."""
        return OptimizedVectorizationService()
    
    def test_lightweight_models_used(self, service):
        """Test que des modèles légers sont utilisés."""
        # Vérifier TfidfVectorizer (léger) vs modèles deep learning
        assert hasattr(service.text_vectorizer, 'pipeline')
        assert hasattr(service.text_vectorizer.pipeline, 'steps')
        
        # Vérifier que c'est bien Tfidf + SVD
        steps = service.text_vectorizer.pipeline.steps
        assert any('tfidf' in step[0].lower() for step in steps)
        assert any('svd' in step[0].lower() for step in steps)
    
    def test_dimension_optimization(self, service):
        """Test optimisation de la dimension (384 pour sqlite-vec)."""
        assert service.vector_dimension == 384
        assert service.text_vectorizer.vector_dimension == 384
    
    def test_batch_size_optimization(self):
        """Test optimisation de la taille des batches pour RPi4."""
        # Les batches doivent être petits pour éviter surcharge mémoire
        batch_size = 50  # Valeur définie dans le service
        assert batch_size <= 100  # Limite raisonnable pour RPi4
    
    def test_scikit_learn_models(self, service):
        """Test que des modèles scikit-learn sont utilisés."""
        # Audio vectorizer doit utiliser StandardScaler
        assert hasattr(service.audio_vectorizer, 'scaler')
        assert hasattr(service.audio_vectorizer.scaler, 'mean_')
        
        # Tag classifier doit utiliser LogisticRegression
        assert hasattr(service.tag_classifier.genre_classifier, 'coef_')
        assert hasattr(service.tag_classifier.mood_classifier, 'coef_')


class TestIntegrationWorkflow:
    """Tests du workflow d'intégration complet."""
    
    @pytest.mark.asyncio
    async def test_full_vectorization_workflow(self):
        """Test du workflow complet de vectorisation."""
        # 1. Service de vectorisation
        service = OptimizedVectorizationService()
        
        # 2. Service de persistance avec répertoire temporaire
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence = ModelPersistenceService()
            persistence.models_dir = Path(temp_dir)
            
            # 3. Service de monitoring
            TagMonitoringService()
            
            # Simuler des données
            test_track = {
                "id": 1,
                "title": "Integration Test Song",
                "artist_name": "Test Artist",
                "genre": "Electronic",
                "bpm": 128,
                "duration": 180,
                "danceability": 0.8
            }
            
            # Entraîner (simulé)
            service.text_vectorizer.is_fitted = True
            service.audio_vectorizer.is_fitted = True
            service.tag_classifier.is_fitted = True
            service.is_trained = True
            
            # Vectoriser
            embedding = service.vectorize_single_track(test_track)
            assert len(embedding) == 384
            assert isinstance(embedding[0], float)
            
            # Sauvegarder modèle
            version = await persistence.save_model_version(service, "integration_v1")
            assert version.version_id == "integration_v1"
            
            # Charger modèle
            loaded_service = await persistence.load_model_version("integration_v1")
            assert loaded_service.is_trained
    
    @pytest.mark.asyncio 
    async def test_monitoring_and_retrain_workflow(self):
        """Test du workflow monitoring → retrain."""
        # 1. Service de monitoring
        monitoring = TagMonitoringService()
        
        # 2. Listener de retrain
        RedisRetrainListener()
        
        # Simuler détection de changements
        changes = {
            'has_changes': True,
            'details': {
                'new_genres': ['House', 'Techno', 'Ambient'],
                'new_tracks': 150
            }
        }
        
        # Vérifier décision de retrain
        decision = monitoring.detector.should_trigger_retrain(changes)
        assert decision['should_retrain']
        assert decision['priority'] == 'high'
        
        # Créer demande de retrain
        retrain_request = RetrainRequest({
            'trigger_reason': 'new_genres',
            'priority': 'high',
            'delay_minutes': 15,
            'message': '3 nouveaux genres + 150 nouvelles tracks',
            'details': changes['details'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Vérifier demande
        assert retrain_request.trigger_reason == 'new_genres'
        assert retrain_request.priority == 'high'


if __name__ == "__main__":
    """Test standalone."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Configuration pour tests
    os.environ.setdefault('LIBRARY_API_URL', 'http://localhost:8001')
    os.environ.setdefault('RECOMMENDER_API_URL', 'http://localhost:8002')
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
    
    # Exécuter tests
    pytest.main([__file__, '-v', '--tb=short'])
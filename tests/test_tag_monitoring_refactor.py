"""
Tests pour le service refactoré de monitoring des tags.

Teste la nouvelle implémentation avec CeleryTaskPublisher au lieu de recommender_api.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from backend_worker.services.tag_monitoring_service import (
    TagChangeDetector,
    TagMonitoringService,
    CeleryTaskPublisher,
    RedisPublisher
)


class TestTagChangeDetector:
    """Tests du détecteur de changements de tags."""

    @pytest.fixture
    def detector(self):
        """Fixture du détecteur."""
        return TagChangeDetector()

    @pytest.mark.asyncio
    async def test_get_current_tags_success(self):
        """Test de récupération réussie des tags actuels."""
        detector = TagChangeDetector()

        # Mock httpx pour éviter les vraies appels API
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response_genres = Mock()
            mock_response_genres.status_code = 200
            mock_response_genres.json.return_value = [
                {'name': 'Rock'}, {'name': 'Pop'}, {'name': 'Jazz'}
            ]
            
            mock_response_moods = Mock()
            mock_response_moods.status_code = 200
            mock_response_moods.json.return_value = [
                {'name': 'Happy'}, {'name': 'Sad'}
            ]
            
            mock_response_genre_tags = Mock()
            mock_response_genre_tags.status_code = 200
            mock_response_genre_tags.json.return_value = [
                {'name': 'Alternative'}, {'name': 'Indie'}
            ]
            
            mock_response_tracks = Mock()
            mock_response_tracks.status_code = 200
            mock_response_tracks.json.return_value = {'count': 150}
            
            # Configurer les réponses selon l'ordre des appels
            mock_client.get.side_effect = [
                mock_response_genres,
                mock_response_moods,
                mock_response_genre_tags,
                mock_response_tracks
            ]
            
            mock_client_class.return_value.__aenter__.return_value = mock_client

            current_tags = await detector.get_current_tags()

            # Vérifier que les tags sont correctement récupérés
            assert 'genres' in current_tags
            assert 'mood_tags' in current_tags
            assert 'genre_tags' in current_tags
            assert 'tracks_count' in current_tags
            assert len(current_tags['genres']) == 3
            assert 'Rock' in current_tags['genres']
            assert 'Pop' in current_tags['genres']
            assert 'Jazz' in current_tags['genres']
            assert len(current_tags['mood_tags']) == 2
            assert 'Happy' in current_tags['mood_tags']
            assert current_tags['tracks_count'] == 150

    @pytest.mark.asyncio
    async def test_get_current_tags_api_error(self):
        """Test de gestion d'erreur API."""
        detector = TagChangeDetector()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            # Simuler une erreur HTTP
            mock_client.get.side_effect = Exception("API Error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            current_tags = await detector.get_current_tags()

            # Vérifier que les tags par défaut sont retournés en cas d'erreur
            assert current_tags['genres'] == set()
            assert current_tags['mood_tags'] == set()
            assert current_tags['genre_tags'] == set()
            assert current_tags['tracks_count'] == 0

    def test_calculate_tags_signature(self, detector):
        """Test du calcul de signature des tags."""
        tags = {
            'genres': {'Rock', 'Pop'},
            'mood_tags': {'Happy'},
            'genre_tags': {'Alternative'},
            'tracks_count': 100
        }

        signature1 = detector.calculate_tags_signature(tags)
        signature2 = detector.calculate_tags_signature(tags)

        # La signature doit être déterministe
        assert signature1 == signature2

        # Modifier les tags doit changer la signature
        tags_modified = tags.copy()
        tags_modified['genres'] = {'Jazz', 'Pop'}
        signature3 = detector.calculate_tags_signature(tags_modified)

        assert signature1 != signature3

    @pytest.mark.asyncio
    async def test_detect_changes_first_check(self, detector):
        """Test de la première vérification."""
        with patch.object(detector, 'get_current_tags') as mock_get_tags:
            mock_get_tags.return_value = {
                'genres': {'Rock'},
                'mood_tags': {'Happy'},
                'genre_tags': {'Alternative'},
                'tracks_count': 50
            }

            result = await detector.detect_changes()

            # Première vérification doit indiquer des changements
            assert result['has_changes'] is True
            assert result['reason'] == 'first_check'
            assert 'details' in result
            assert result['details']['new_genres'] == 1
            assert result['details']['tracks_count'] == 50

    @pytest.mark.asyncio
    async def test_detect_changes_no_changes(self, detector):
        """Test de détection sans changements."""
        # Simuler une vérification précédente
        detector.last_check = {
            'tags': {
                'genres': {'Rock'},
                'mood_tags': {'Happy'},
                'genre_tags': {'Alternative'},
                'tracks_count': 50
            },
            'signature': 'test_signature',
            'timestamp': '2024-01-01T00:00:00'
        }

        with patch.object(detector, 'get_current_tags') as mock_get_tags:
            mock_get_tags.return_value = {
                'genres': {'Rock'},
                'mood_tags': {'Happy'},
                'genre_tags': {'Alternative'},
                'tracks_count': 50
            }

            with patch.object(detector, 'calculate_tags_signature', return_value='test_signature'):
                result = await detector.detect_changes()

                assert result['has_changes'] is False
                assert result['reason'] == 'no_changes'

    @pytest.mark.asyncio
    async def test_detect_changes_new_genres(self, detector):
        """Test de détection de nouveaux genres."""
        # Simuler une vérification précédente
        detector.last_check = {
            'tags': {
                'genres': {'Rock'},
                'mood_tags': {'Happy'},
                'genre_tags': {'Alternative'},
                'tracks_count': 50
            },
            'signature': 'old_signature',
            'timestamp': '2024-01-01T00:00:00'
        }

        with patch.object(detector, 'get_current_tags') as mock_get_tags:
            mock_get_tags.return_value = {
                'genres': {'Rock', 'Jazz'},
                'mood_tags': {'Happy'},
                'genre_tags': {'Alternative'},
                'tracks_count': 50
            }

            with patch.object(detector, 'calculate_tags_signature', return_value='new_signature'):
                result = await detector.detect_changes()

                assert result['has_changes'] is True
                assert result['reason'] == 'tags_modified'
                assert 'new_genres' in result['details']
                assert 'Jazz' in result['details']['new_genres']

    def test_should_trigger_retrain_new_genres(self, detector):
        """Test de décision de retrain pour nouveaux genres."""
        changes = {
            'has_changes': True,
            'details': {'new_genres': ['Rock', 'Pop', 'Jazz']}
        }

        decision = detector.should_trigger_retrain(changes)

        assert decision['should_retrain'] is True
        assert decision['priority'] == 'high'
        assert decision['reason'] == 'new_genres'
        assert decision['delay_minutes'] == 15

    def test_should_trigger_retrain_significant_tracks(self, detector):
        """Test de décision de retrain pour nombreuses nouvelles tracks."""
        changes = {
            'has_changes': True,
            'details': {'new_tracks': 150}
        }

        decision = detector.should_trigger_retrain(changes)

        assert decision['should_retrain'] is True
        assert decision['priority'] == 'medium'
        assert decision['reason'] == 'significant_new_tracks'
        assert decision['delay_minutes'] == 120

    def test_should_trigger_retrain_new_tags(self, detector):
        """Test de décision de retrain pour nouveaux tags."""
        changes = {
            'has_changes': True,
            'details': {'new_moods': ['Energetic'], 'new_genre_tags': ['Indie', 'Alternative', 'Electronic', 'Ambient', 'Experimental', 'Folk']}
        }

        decision = detector.should_trigger_retrain(changes)

        assert decision['should_retrain'] is True
        assert decision['priority'] == 'low'
        assert decision['reason'] == 'new_tags'
        assert decision['delay_minutes'] == 480

    def test_should_trigger_retrain_no_retrain(self, detector):
        """Test de décision sans retrain nécessaire."""
        changes = {
            'has_changes': True,
            'details': {'new_moods': ['Happy']}  # Seulement 1 tag
        }

        decision = detector.should_trigger_retrain(changes)

        assert decision['should_retrain'] is False
        assert decision['priority'] == 'none'
        assert decision['reason'] == 'insignificant_changes'


class TestCeleryTaskPublisher:
    """Tests du publieur de tâches Celery."""

    @pytest.fixture
    def mock_celery(self):
        """Fixture mock Celery."""
        mock = Mock()
        mock.send_task = Mock()
        mock.send_task.return_value = Mock(id='mock_task_id')
        return mock

    @pytest.fixture
    def mock_redis(self):
        """Fixture mock Redis."""
        mock = Mock()
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def mock_config(self, mock_celery):
        """Fixture mock configuration Celery."""
        mock = Mock()
        mock.get_celery_app.return_value = mock_celery
        return mock

    @pytest.mark.asyncio
    async def test_trigger_retrain_task_success(self, mock_celery, mock_redis, mock_config):
        """Test le déclenchement réussi d'une tâche de retrain."""
        trigger_info = {
            'reason': 'new_genres',
            'priority': 'high',
            'message': '3 nouveaux genres détectés',
            'details': {'new_genres': ['Rock', 'Pop', 'Jazz']},
            'delay_minutes': 15
        }

        with patch('backend_worker.services.tag_monitoring_service.get_celery_config', return_value=mock_config), \
             patch('redis.asyncio.from_url', return_value=mock_redis):
            
            publisher = CeleryTaskPublisher()
            result = await publisher.trigger_retrain_task(trigger_info)
            
            assert result['success'] is True
            assert result['celery_task_id'] == 'mock_task_id'
            
            # Vérifier que la tâche Celery a été appelée avec les bons paramètres
            mock_celery.send_task.assert_called_once()
            args, kwargs = mock_celery.send_task.call_args
            assert args[0] == 'train_recommendation_model'
            assert 'priority' in kwargs
            assert kwargs['priority'] == 9  # high priority
            assert 'countdown' in kwargs
            assert kwargs['countdown'] == 15 * 60  # 15 minutes

    @pytest.mark.asyncio
    async def test_trigger_retrain_task_failure(self, mock_celery, mock_config):
        """Test l'échec du déclenchement d'une tâche de retrain."""
        trigger_info = {
            'reason': 'new_genres',
            'priority': 'medium',
            'message': 'Test failure',
            'details': {},
            'delay_minutes': 30
        }

        # Simuler une exception Celery
        mock_celery.send_task.side_effect = Exception("Celery error")
        
        with patch('backend_worker.services.tag_monitoring_service.get_celery_config', return_value=mock_config):
            publisher = CeleryTaskPublisher()
            result = await publisher.trigger_retrain_task(trigger_info)
            
            assert result['success'] is False
            assert 'error' in result
            assert 'Celery error' in result['error']

    def test_priority_mapping(self):
        """Test la conversion des priorités en niveaux Celery."""
        publisher = CeleryTaskPublisher()
        
        # Test des mappings de priorité
        assert publisher._map_priority_to_celery('high') == 9
        assert publisher._map_priority_to_celery('medium') == 5
        assert publisher._map_priority_to_celery('low') == 1
        assert publisher._map_priority_to_celery('none') == 0


class TestRedisPublisher:
    """Tests du publieur Redis."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture mock Redis."""
        mock = Mock()
        mock.publish = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_publish_retrain_request_success(self, mock_redis):
        """Test de publication réussie via Redis."""
        trigger_info = {
            'reason': 'new_genres',
            'priority': 'high',
            'message': 'Test retrain',
            'details': {'new_genres': ['Rock']},
            'delay_minutes': 15
        }

        with patch('redis.asyncio.from_url', return_value=mock_redis):
            publisher = RedisPublisher()
            result = await publisher.publish_retrain_request(trigger_info)
            
            assert result is True
            # Vérifier que les messages ont été publiés
            assert mock_redis.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_retrain_request_failure(self):
        """Test d'échec de publication via Redis."""
        trigger_info = {
            'reason': 'test',
            'priority': 'low',
            'message': 'Test',
            'details': {},
            'delay_minutes': 30
        }

        with patch('redis.asyncio.from_url') as mock_from_url:
            # Simuler une erreur Redis
            mock_from_url.side_effect = Exception("Redis error")
            
            publisher = RedisPublisher()
            result = await publisher.publish_retrain_request(trigger_info)
            
            assert result is False


class TestTagMonitoringService:
    """Tests du service principal de monitoring."""

    @pytest.fixture
    def mock_celery(self):
        """Fixture mock Celery."""
        mock = Mock()
        mock.send_task = Mock()
        mock.send_task.return_value = Mock(id='mock_task_id')
        return mock

    @pytest.fixture
    def mock_redis(self):
        """Fixture mock Redis."""
        mock = Mock()
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def mock_config(self, mock_celery):
        """Fixture mock configuration Celery."""
        mock = Mock()
        mock.get_celery_app.return_value = mock_celery
        return mock

    @pytest.mark.asyncio
    async def test_check_and_publish_retrain_needed(self, mock_celery, mock_redis, mock_config):
        """Test de vérification avec retrain nécessaire."""
        # Mock du détecteur de changements
        mock_detector = Mock()
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': True,
            'reason': 'tags_modified',
            'message': 'Nouveaux tags détectés',
            'details': {'new_genres': ['Electronic']}
        })
        mock_detector.should_trigger_retrain = Mock(return_value={
            'should_retrain': True,
            'priority': 'medium',
            'message': 'Retrain recommandé',
            'details': {'new_genres': ['Electronic']},
            'delay_minutes': 60
        })

        with patch('backend_worker.services.tag_monitoring_service.get_celery_config', return_value=mock_config), \
             patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector), \
             patch('redis.asyncio.from_url', return_value=mock_redis):
            
            service = TagMonitoringService()
            result = await service.check_and_publish_if_needed()
            
            assert result['status'] == 'retrain_requested'
            assert result['priority'] == 'medium'
            assert 'celery_published' in result
            assert 'redis_published' in result
            assert result['celery_published'] is True
            assert result['redis_published'] is True

    @pytest.mark.asyncio
    async def test_check_and_publish_no_retrain(self, mock_detector):
        """Test de vérification sans retrain nécessaire."""
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': True,
            'reason': 'tags_modified',
            'message': 'Nouveaux tags détectés'
        })
        mock_detector.should_trigger_retrain = Mock(return_value={
            'should_retrain': False,
            'priority': 'none',
            'message': 'Retrain non nécessaire',
            'details': {}
        })

        with patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector):
            service = TagMonitoringService()
            result = await service.check_and_publish_if_needed()
            
            assert result['status'] == 'retrain_not_needed'
            assert result['message'] == 'Retrain non nécessaire'

    @pytest.mark.asyncio
    async def test_check_and_publish_no_changes(self):
        """Test de vérification sans changements détectés."""
        mock_detector = Mock()
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': False,
            'reason': 'no_changes',
            'message': 'Aucun changement détecté'
        })

        with patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector):
            service = TagMonitoringService()
            result = await service.check_and_publish_if_needed()
            
            assert result['status'] == 'no_action'
            assert result['message'] == 'Aucun changement détecté'

    @pytest.mark.asyncio
    async def test_manual_check(self, mock_detector):
        """Test de vérification manuelle."""
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': False,
            'reason': 'no_changes',
            'message': 'Test manuel'
        })

        with patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector):
            service = TagMonitoringService()
            result = await service.manual_check()
            
            assert result['status'] == 'no_action'
            assert result['message'] == 'Test manuel'


class TestBackwardCompatibility:
    """Tests de compatibilité avec l'ancienne implémentation."""

    @pytest.mark.asyncio
    async def test_tag_change_detection_still_works(self):
        """Test que la détection de changements fonctionne toujours."""
        detector = TagChangeDetector()

        # Mock httpx pour éviter les vraies appels API
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response_genres = Mock()
            mock_response_genres.status_code = 200
            mock_response_genres.json.return_value = [
                {'name': 'Rock'}, {'name': 'Pop'}, {'name': 'Jazz'}
            ]
            
            mock_response_moods = Mock()
            mock_response_moods.status_code = 200
            mock_response_moods.json.return_value = [
                {'name': 'Happy'}, {'name': 'Sad'}
            ]
            
            mock_response_genre_tags = Mock()
            mock_response_genre_tags.status_code = 200
            mock_response_genre_tags.json.return_value = [
                {'name': 'Alternative'}, {'name': 'Indie'}
            ]
            
            mock_response_tracks = Mock()
            mock_response_tracks.status_code = 200
            mock_response_tracks.json.return_value = {'count': 150}
            
            # Configurer les réponses selon l'ordre des appels
            mock_client.get.side_effect = [
                mock_response_genres,
                mock_response_moods,
                mock_response_genre_tags,
                mock_response_tracks
            ]
            
            mock_client_class.return_value.__aenter__.return_value = mock_client

            current_tags = await detector.get_current_tags()

            # Vérifier que les tags sont correctement récupérés
            assert 'genres' in current_tags
            assert 'mood_tags' in current_tags
            assert 'genre_tags' in current_tags
            assert 'tracks_count' in current_tags
            assert len(current_tags['genres']) == 3
            assert 'Rock' in current_tags['genres']
            assert 'Pop' in current_tags['genres']
            assert 'Jazz' in current_tags['genres']
            assert len(current_tags['mood_tags']) == 2
            assert 'Happy' in current_tags['mood_tags']
            assert current_tags['tracks_count'] == 150


class TestIntegration:
    """Tests d'intégration."""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self):
        """Test du workflow complet avec succès."""
        # Mock des dépendances
        mock_celery = Mock()
        mock_celery.send_task = Mock(return_value=Mock(id='task_123'))
        
        mock_redis = Mock()
        mock_redis.publish = AsyncMock()
        
        mock_config = Mock()
        mock_config.get_celery_app.return_value = mock_celery
        
        mock_detector = Mock()
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': True,
            'reason': 'tags_modified',
            'message': 'Nouveaux genres détectés',
            'details': {'new_genres': ['Electronic']}
        })
        mock_detector.should_trigger_retrain = Mock(return_value={
            'should_retrain': True,
            'priority': 'high',
            'message': 'Retrain urgent nécessaire',
            'details': {'new_genres': ['Electronic']},
            'delay_minutes': 15
        })

        with patch('backend_worker.services.tag_monitoring_service.get_celery_config', return_value=mock_config), \
             patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector), \
             patch('redis.asyncio.from_url', return_value=mock_redis):
            
            service = TagMonitoringService()
            result = await service.check_and_publish_if_needed()
            
            # Vérifier le résultat complet
            assert result['status'] == 'retrain_requested'
            assert result['priority'] == 'high'
            assert result['celery_published'] is True
            assert result['redis_published'] is True
            assert result['celery_task_id'] == 'task_123'
            assert result['delay_minutes'] == 15

    @pytest.mark.asyncio
    async def test_full_workflow_partial_failure(self):
        """Test du workflow avec échec partiel (Celery OK, Redis KO)."""
        # Mock des dépendances
        mock_celery = Mock()
        mock_celery.send_task = Mock(return_value=Mock(id='task_456'))
        
        mock_redis = Mock()
        mock_redis.publish = AsyncMock(side_effect=Exception("Redis error"))
        
        mock_config = Mock()
        mock_config.get_celery_app.return_value = mock_celery
        
        mock_detector = Mock()
        mock_detector.detect_changes = AsyncMock(return_value={
            'has_changes': True,
            'reason': 'tags_modified',
            'message': 'Test partial failure',
            'details': {'new_genres': ['Jazz']}
        })
        mock_detector.should_trigger_retrain = Mock(return_value={
            'should_retrain': True,
            'priority': 'medium',
            'message': 'Retrain nécessaire',
            'details': {'new_genres': ['Jazz']},
            'delay_minutes': 60
        })

        with patch('backend_worker.services.tag_monitoring_service.get_celery_config', return_value=mock_config), \
             patch('backend_worker.services.tag_monitoring_service.TagChangeDetector', return_value=mock_detector), \
             patch('redis.asyncio.from_url', return_value=mock_redis):
            
            service = TagMonitoringService()
            result = await service.check_and_publish_if_needed()
            
            # Vérifier que Celery a fonctionné mais pas Redis
            assert result['status'] == 'retrain_requested'
            assert result['celery_published'] is True
            assert result['redis_published'] is False
            assert result['celery_task_id'] == 'task_456'
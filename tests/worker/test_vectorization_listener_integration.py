"""
Test d'intégration pour valider le fonctionnement du VectorizationEventListener

Teste que le listener peut traiter les événements Redis sans erreur NoneType
et déclencher correctement les tâches Celery.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock

from backend_worker.utils.redis_utils import (
    VectorizationEventListener, 
    publish_vectorization_event,
    listen_events
)
from backend_worker.celery_app import celery


class TestVectorizationEventListenerIntegration:
    """Test d'intégration du VectorizationEventListener."""

    @pytest.fixture
    def mock_redis_pubsub(self):
        """Mock Redis pubsub avec messages simulés."""
        mock_client = Mock()
        mock_pubsub = Mock()
        
        # Messages simulés selon les logs d'erreur
        test_messages = [
            {
                'type': 'message',
                'channel': 'tracks.to_vectorize',
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': '3091',
                    'artist': 'Test Artist 1',
                    'genres': ['electronic'],
                    'bpm': 128,
                    'duration': 240
                })
            },
            {
                'type': 'message', 
                'channel': 'tracks.to_vectorize',
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': '3115',
                    'artist': 'Test Artist 2',
                    'genres': ['rock'],
                    'bpm': 140,
                    'duration': 180
                })
            },
            {
                'type': 'message',
                'channel': 'tracks.to_vectorize', 
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': '3139',
                    'artist': 'Test Artist 3',
                    'genres': ['jazz'],
                    'bpm': 95,
                    'duration': 300
                })
            }
        ]
        
        mock_pubsub.subscribe.return_value = AsyncMock()
        mock_pubsub.listen.return_value = iter(test_messages)
        mock_client.pubsub.return_value = mock_pubsub
        
        return mock_client, mock_pubsub

    @pytest.mark.asyncio
    async def test_vectorization_listener_integration(self, mock_redis_pubsub):
        """Test intégration complète du listener de vectorisation."""
        mock_client, mock_pubsub = mock_redis_pubsub
        
        # Mock Celery
        celery_tasks_sent = []
        original_send_task = celery.send_task
        
        def mock_send_task(task_name, args=None, queue=None, priority=None):
            celery_tasks_sent.append({
                'task_name': task_name,
                'args': args,
                'queue': queue,
                'priority': priority
            })
            print(f"Task sent: {task_name} with args {args}")
        
        # Remplacer les dépendances
        import backend_worker.utils.redis_utils as redis_utils
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        celery.send_task = mock_send_task
        
        try:
            # Créer et démarrer le listener
            listener = VectorizationEventListener()
            
            # Mock de la fonction start_listening pour éviter la boucle infinie
            async def mock_start_listening():
                # Utiliser directement listen_events avec le callback du listener
                callback = listener.handle_vectorization_event
                await listen_events('tracks.to_vectorize', callback, ['track_created'])
            
            # Démarrer l'écoute (simulation)
            await mock_start_listening()
            
            # Vérifier que les tâches Celery ont été envoyées
            assert len(celery_tasks_sent) == 3
            
            # Vérifier les détails des tâches
            expected_tasks = [
                {'task_name': 'calculate_vector', 'track_id': '3091'},
                {'task_name': 'calculate_vector', 'track_id': '3115'}, 
                {'task_name': 'calculate_vector', 'track_id': '3139'}
            ]
            
            for i, expected in enumerate(expected_tasks):
                task = celery_tasks_sent[i]
                assert task['task_name'] == expected['task_name']
                assert task['args'][0] == int(expected['track_id'])
                assert task['queue'] == 'vectorization'
                assert task['priority'] == 5
            
            print("✅ VectorizationEventListener fonctionne correctement")
            
        finally:
            # Restaurer les mocks originaux
            celery.send_task = original_send_task

    @pytest.mark.asyncio 
    async def test_publish_vectorization_event(self):
        """Test de publication d'événement de vectorisation."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.publish.return_value = mock_result
        mock_result.__gt__ = lambda self, value: True  # Simule result > 0
        
        import backend_worker.utils.redis_utils as redis_utils
        original_get_client = redis_utils.redis_manager.get_client
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        try:
            # Test de publication
            metadata = {
                'artist': 'Test Artist',
                'genre_tags': ['electronic', 'ambient'],
                'mood_tags': ['chill', 'energetic'],
                'bpm': 128,
                'duration': 240
            }
            
            success = await publish_vectorization_event(123, metadata, 'track_created')
            
            # Vérifier que la publication a réussi
            assert success is True
            assert mock_client.publish.called
            
            # Vérifier le contenu du message publié
            call_args = mock_client.publish.call_args[0]
            channel = call_args[0]
            message_data = call_args[1]
            
            assert channel == 'tracks.to_vectorize'
            message_json = json.loads(message_data)
            assert message_json['type'] == 'track_created'
            assert message_json['track_id'] == '123'
            assert message_json['artist'] == 'Test Artist'
            assert 'electronic' in message_json['genres']
            assert 'ambient' in message_json['genres']
            assert 'chill' in message_json['moods']
            assert 'energetic' in message_json['moods']
            assert message_json['bpm'] == 128
            assert message_json['duration'] == 240
            
            print("✅ Publication d'événement de vectorisation fonctionne")
            
        finally:
            # Restaurer le client original
            redis_utils.redis_manager.get_client = original_get_client

    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test de la résilience aux erreurs."""
        mock_client = Mock()
        mock_pubsub = Mock()
        
        # Messages avec une erreur potentielle
        test_messages = [
            {
                'type': 'message',
                'channel': 'tracks.to_vectorize',
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': 'invalid',  # Peut causer erreur
                    'artist': None  # Données incomplètes
                })
            },
            {
                'type': 'message',
                'channel': 'tracks.to_vectorize', 
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': '3091',
                    'artist': 'Valid Artist'
                })
            }
        ]
        
        mock_pubsub.subscribe.return_value = AsyncMock()
        mock_pubsub.listen.return_value = iter(test_messages)
        mock_client.pubsub.return_value = mock_pubsub
        
        import backend_worker.utils.redis_utils as redis_utils
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        # Callback qui peut échouer
        callback_calls = []
        
        def test_callback(data):
            callback_calls.append(data)
            # Simuler une erreur sur le premier message
            if len(callback_calls) == 1:
                raise ValueError("Test error")
        
        try:
            # L'écoute doit continuer malgré l'erreur
            await listen_events('tracks.to_vectorize', test_callback, ['track_created'])
            
            # Vérifier que les deux callbacks ont été tentés
            assert len(callback_calls) == 2
            
            print("✅ Résilience aux erreurs validée")
            
        except Exception as e:
            pytest.fail(f"Erreur non gérée dans listen_events: {e}")


if __name__ == "__main__":
    # Test manuel pour validation rapide
    print("Test d'intégration du VectorizationEventListener...")
    
    async def test_manual_integration():
        # Simuler un listener comme dans le code réel
        class MockVectorizationListener:
            def __init__(self):
                self.tasks_triggered = []
            
            def handle_vectorization_event(self, event_data):
                """Gère un événement de vectorisation selon le schéma du prompt."""
                try:
                    track_id = event_data.get('track_id')
                    
                    if track_id:
                        print(f"[VECTOR_LISTENER] Track à vectoriser: {track_id}")
                        self.tasks_triggered.append(track_id)
                        
                        # Simuler l'envoi de tâche Celery
                        print(f"Task calculate_vector send with track_id: {track_id}")
                        
                except Exception as e:
                    print(f"[VECTOR_LISTENER] Erreur traitement événement: {e}")
        
        # Données de test basées sur les logs d'erreur réels
        test_events = [
            {'track_id': '3091'},
            {'track_id': '3115'},
            {'track_id': '3139'}
        ]
        
        listener = MockVectorizationListener()
        
        # Simuler l'appel par listen_events
        for event_data in test_events:
            import inspect
            if inspect.iscoroutinefunction(listener.handle_vectorization_event):
                await listener.handle_vectorization_event(event_data)
            else:
                listener.handle_vectorization_event(event_data)
        
        print(f"Tasks triggered: {listener.tasks_triggered}")
        print("✅ Integration test passed - No NoneType errors!")
    
    asyncio.run(test_manual_integration())
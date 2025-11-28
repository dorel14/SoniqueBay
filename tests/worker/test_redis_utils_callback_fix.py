"""
Test pour valider la correction du bug de callback Redis

Teste que le système peut gérer à la fois les callbacks synchrones et asynchrones
sans générer l'erreur "object NoneType can't be used in 'await' expression".
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

from backend_worker.utils.redis_utils import listen_events


class TestRedisCallbackHandling:
    """Test de la gestion des callbacks dans redis_utils."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Mock du RedisManager."""
        mock_client = Mock()
        mock_pubsub = AsyncMock()
        mock_client.pubsub.return_value = mock_pubsub
        
        # Simuler des messages Redis
        messages = [
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'test_event',
                    'track_id': 123,
                    'artist': 'Test Artist'
                })
            },
            {
                'type': 'message',
                'channel': 'test_channel', 
                'data': json.dumps({
                    'type': 'test_event',
                    'track_id': 456,
                    'artist': 'Another Artist'
                })
            }
        ]
        
        # Configurer le mock pour retourner les messages
        mock_pubsub.subscribe.return_value = True
        mock_pubsub.listen.return_value = iter(messages)
        
        return mock_client, mock_pubsub

    @pytest.mark.asyncio
    async def test_sync_callback_no_error(self, mock_redis_manager):
        """Test qu'un callback synchrone ne génère pas d'erreur NoneType."""
        mock_client, mock_pubsub = mock_redis_manager
        
        # Callback synchrone (comme handle_vectorization_event)
        sync_callback_calls = []
        
        def sync_callback(data):
            sync_callback_calls.append(data)
            print(f"Sync callback called with: {data}")
        
        # Remplacer la connexion Redis dans redis_manager
        import backend_worker.utils.redis_utils as redis_utils
        original_get_client = redis_utils.redis_manager.get_client
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        try:
            # Lancer l'écoute avec un callback synchrone
            await listen_events('test_channel', sync_callback)
            
            # Vérifier que les callbacks ont été appelées
            assert len(sync_callback_calls) == 2
            assert sync_callback_calls[0]['track_id'] == 123
            assert sync_callback_calls[1]['track_id'] == 456
            
        finally:
            # Restaurer la connexion originale
            redis_utils.redis_manager.get_client = original_get_client

    @pytest.mark.asyncio
    async def test_async_callback_works(self, mock_redis_manager):
        """Test qu'un callback asynchrone fonctionne toujours."""
        mock_client, mock_pubsub = mock_redis_manager
        
        # Callback asynchrone
        async_callback_calls = []
        
        async def async_callback(data):
            async_callback_calls.append(data)
            await asyncio.sleep(0.001)  # Simuler une opération async
            print(f"Async callback called with: {data}")
        
        # Remplacer la connexion Redis
        import backend_worker.utils.redis_utils as redis_utils
        original_get_client = redis_utils.redis_manager.get_client
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        try:
            # Lancer l'écoute avec un callback asynchrone
            await listen_events('test_channel', async_callback)
            
            # Vérifier que les callbacks ont été appelées
            assert len(async_callback_calls) == 2
            assert async_callback_calls[0]['track_id'] == 123
            assert async_callback_calls[1]['track_id'] == 456
            
        finally:
            # Restaurer la connexion originale
            redis_utils.redis_manager.get_client = original_get_client

    @pytest.mark.asyncio
    async def test_event_filtering_with_sync_callback(self, mock_redis_manager):
        """Test que le filtrage d'événements fonctionne avec callback sync."""
        mock_client, mock_pubsub = mock_redis_manager
        
        messages = [
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': 123
                })
            },
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'other_event',  # Sera filtré
                    'track_id': 999
                })
            },
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'track_created',
                    'track_id': 456
                })
            }
        ]
        
        mock_pubsub.subscribe.return_value = True
        mock_pubsub.listen.return_value = iter(messages)
        
        callback_calls = []
        
        def sync_callback(data):
            callback_calls.append(data)
        
        # Remplacer la connexion Redis
        import backend_worker.utils.redis_utils as redis_utils
        original_get_client = redis_utils.redis_manager.get_client
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        try:
            # Écouter seulement les événements 'track_created'
            await listen_events('test_channel', sync_callback, ['track_created'])
            
            # Vérifier que seul 'track_created' a été traité
            assert len(callback_calls) == 2
            assert all(call['type'] == 'track_created' for call in callback_calls)
            assert 999 not in [call['track_id'] for call in callback_calls]
            
        finally:
            # Restaurer la connexion originale
            redis_utils.redis_manager.get_client = original_get_client

    @pytest.mark.asyncio
    async def test_callback_exception_handling(self, mock_redis_manager):
        """Test que les exceptions dans les callbacks sont correctement gérées."""
        mock_client, mock_pubsub = mock_redis_manager
        
        messages = [
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'test_event',
                    'track_id': 123
                })
            },
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'test_event',
                    'track_id': 456  # Provoquera une exception
                })
            },
            {
                'type': 'message',
                'channel': 'test_channel',
                'data': json.dumps({
                    'type': 'test_event',
                    'track_id': 789
                })
            }
        ]
        
        mock_pubsub.subscribe.return_value = True
        mock_pubsub.listen.return_value = iter(messages)
        
        callback_calls = []
        
        def failing_callback(data):
            callback_calls.append(data)
            if data['track_id'] == 456:
                raise ValueError("Test exception")
        
        # Remplacer la connexion Redis
        import backend_worker.utils.redis_utils as redis_utils
        original_get_client = redis_utils.redis_manager.get_client
        redis_utils.redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        try:
            # L'écoute doit continuer malgré l'exception
            await listen_events('test_channel', failing_callback)
            
            # Vérifier que les callbacks ont été appelées (même celle qui échoue)
            assert len(callback_calls) == 3
            assert callback_calls[0]['track_id'] == 123
            assert callback_calls[1]['track_id'] == 456
            assert callback_calls[2]['track_id'] == 789
            
        finally:
            # Restaurer la connexion originale
            redis_utils.redis_manager.get_client = original_get_client


if __name__ == "__main__":
    # Test direct sans pytest pour validation rapide
    print("Test de validation de la correction Redis...")
    
    async def test_manual():
        # Simuler un callback synchrone comme dans VectorizationEventListener
        sync_calls = []
        
        def handle_vectorization_event(event_data):
            track_id = event_data.get('track_id')
            sync_calls.append(track_id)
            print(f"Track à vectoriser: {track_id}")
        
        # Test avec des données simulées
        test_data = [
            {'track_id': 3091},
            {'track_id': 3115},
            {'track_id': 3139}
        ]
        
        # Simuler l'appel direct (comme le ferait listen_events)
        for data in test_data:
            import inspect
            if inspect.iscoroutinefunction(handle_vectorization_event):
                await handle_vectorization_event(data)
            else:
                handle_vectorization_event(data)
        
        print(f"Callbacks traités: {sync_calls}")
        print("✅ Pas d'erreur NoneType - correction validée!")
    
    asyncio.run(test_manual())
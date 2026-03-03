"""
Tests unitaires pour RealtimeServiceV2.
"""

from unittest.mock import patch

import pytest

from backend.api.services.realtime_service_v2 import (
    ChatRealtimeManager,
    RealtimeChannel,
    RealtimeServiceV2,
    get_realtime_service_v2,
    reset_realtime_service_v2,
)


class TestRealtimeChannel:
    """Tests pour RealtimeChannel."""
    
    def test_to_postgres_changes_with_table(self):
        """Test conversion en postgres_changes."""
        channel = RealtimeChannel(
            name="test",
            table="tracks",
            event="INSERT",
            filter="user_id=eq.123"
        )
        
        changes = channel.to_postgres_changes()
        
        assert changes == {
            "event": "INSERT",
            "schema": "public",
            "table": "tracks",
            "filter": "user_id=eq.123"
        }
    
    def test_to_postgres_changes_without_table(self):
        """Test conversion sans table."""
        channel = RealtimeChannel(name="test")
        assert channel.to_postgres_changes() is None
    
    def test_to_postgres_changes_default_event(self):
        """Test conversion avec event par défaut."""
        channel = RealtimeChannel(name="test", table="tracks")
        changes = channel.to_postgres_changes()
        assert changes["event"] == "*"


class TestRealtimeServiceV2:
    """Tests pour RealtimeServiceV2."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_realtime_service_v2()
    
    def test_init_fallback_mode(self):
        """Test initialisation en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            assert service.use_supabase is False
    
    def test_init_supabase_mode(self):
        """Test initialisation en mode Supabase."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.utils.db_config.is_migrated', return_value=True):
                    # Recréer le service pour prendre en compte le patch
                    reset_realtime_service_v2()
                    service = RealtimeServiceV2()
                    assert service.use_supabase is True
    
    @pytest.mark.asyncio
    async def test_connect_fallback(self):
        """Test connexion en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            result = await service.connect()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_fallback(self):
        """Test abonnement en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            callback_called = False
            def callback(event):
                nonlocal callback_called
                callback_called = True
            
            result = await service.subscribe(
                channel_name="test",
                callback=callback
            )
            
            assert result is True
            assert "test" in service._fallback_callbacks
    
    @pytest.mark.asyncio
    async def test_broadcast_fallback(self):
        """Test broadcast en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            received_events = []
            def callback(event):
                received_events.append(event)
            
            await service.subscribe("test", callback=callback)
            
            result = await service.broadcast(
                channel_name="test",
                event="test_event",
                payload={"data": "test"}
            )
            
            assert result is True
            assert len(received_events) == 1
            assert received_events[0]["type"] == "broadcast"
            assert received_events[0]["event"] == "test_event"
    
    @pytest.mark.asyncio
    async def test_unsubscribe_fallback(self):
        """Test désabonnement en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            await service.subscribe("test", callback=lambda x: x)
            assert "test" in service._fallback_callbacks
            
            result = await service.unsubscribe("test")
            assert result is True
            assert "test" not in service._fallback_callbacks
    
    @pytest.mark.asyncio
    async def test_subscribe_chat(self):
        """Test abonnement au canal de chat."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            def callback(event):
                pass
            
            result = await service.subscribe_chat("chat123", callback)
            assert result is True
            assert "chat:chat123" in service._fallback_callbacks
    
    @pytest.mark.asyncio
    async def test_subscribe_notifications(self):
        """Test abonnement aux notifications."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            def callback(event):
                pass
            
            result = await service.subscribe_notifications("user123", callback)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_progress(self):
        """Test abonnement à la progression."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            def callback(event):
                pass
            
            result = await service.subscribe_progress("task123", callback)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_library_updates(self):
        """Test abonnement aux mises à jour bibliothèque."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            def callback(event):
                pass
            
            result = await service.subscribe_library_updates(callback)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_chat_message(self):
        """Test envoi message chat."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            received = []
            def callback(event):
                received.append(event)
            
            await service.subscribe_chat("chat123", callback)
            
            result = await service.send_chat_message(
                chat_id="chat123",
                message={"content": "Hello", "sender": "user"}
            )
            
            assert result is True
            assert len(received) == 1
    
    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test envoi notification."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            result = await service.send_notification(
                user_id="user123",
                notification={"title": "Test", "body": "Message"}
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_update_progress(self):
        """Test mise à jour progression."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            
            result = await service.update_progress(
                task_id="task123",
                progress={"percent": 50, "status": "running"}
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_disconnect_fallback(self):
        """Test déconnexion en mode fallback."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service = RealtimeServiceV2()
            # Ne devrait pas lever d'exception
            await service.disconnect()


class TestChatRealtimeManager:
    """Tests pour ChatRealtimeManager."""
    
    def setup_method(self):
        reset_realtime_service_v2()
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test démarrage et arrêt du chat."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            manager = ChatRealtimeManager("chat123")
            
            received = []
            def on_message(event):
                received.append(event)
            
            result = await manager.start(on_message)
            assert result is True
            
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test envoi message via manager."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            manager = ChatRealtimeManager("chat123")
            
            result = await manager.send_message(
                content="Hello",
                sender="user",
                metadata={"key": "value"}
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_message(self):
        """Test gestion des messages entrants."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            manager = ChatRealtimeManager("chat123")
            
            received = []
            def on_message(event):
                received.append(event)
            
            await manager.start(on_message)
            
            # Simuler un message
            test_event = {
                "type": "broadcast",
                "payload": {"content": "Test message"}
            }
            manager._handle_message(test_event)
            
            assert len(received) == 1
            assert received[0] == test_event


class TestRealtimeServiceV2Factory:
    """Tests pour la factory."""
    
    def setup_method(self):
        reset_realtime_service_v2()
    
    def test_singleton(self):
        """Test pattern singleton."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service1 = get_realtime_service_v2()
            service2 = get_realtime_service_v2()
            assert service1 is service2
    
    def test_reset(self):
        """Test reset du singleton."""
        with patch('backend.api.services.realtime_service_v2.SUPABASE_AVAILABLE', False):
            service1 = get_realtime_service_v2()
            reset_realtime_service_v2()
            service2 = get_realtime_service_v2()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

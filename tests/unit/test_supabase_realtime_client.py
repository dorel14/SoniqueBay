"""
Tests unitaires pour SupabaseRealtimeClient (frontend).
"""

import pytest
from unittest.mock import patch
from frontend.utils.supabase_realtime import (
    SupabaseRealtimeClient,
    get_realtime_client,
    reset_realtime_client,
    ChatManager,
    RealtimeSubscription
)


class TestRealtimeSubscription:
    """Tests pour RealtimeSubscription."""
    
    def test_dataclass(self):
        """Test création du dataclass."""
        sub = RealtimeSubscription(
            channel_name="test",
            callback=lambda x: x,
            is_active=True
        )
        assert sub.channel_name == "test"
        assert sub.is_active is True


class TestSupabaseRealtimeClient:
    """Tests pour SupabaseRealtimeClient."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_realtime_client()
    
    def test_init_fallback_mode(self):
        """Test initialisation en mode fallback."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            assert client._connected is False
    
    def test_init_no_key(self):
        """Test initialisation sans clé."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                client = SupabaseRealtimeClient()
                assert client._key is None
    
    @pytest.mark.asyncio
    async def test_connect_fallback(self):
        """Test connexion en mode fallback."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            result = await client.connect()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_fallback(self):
        """Test abonnement en mode fallback."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            received = []
            def callback(event):
                received.append(event)
            
            result = await client.subscribe("test", callback)
            
            assert result is True
            assert "test" in client._subscriptions
            assert client._subscriptions["test"].is_active is True
    
    @pytest.mark.asyncio
    async def test_handle_event(self):
        """Test gestion des événements."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            received = []
            def callback(event):
                received.append(event)
            
            await client.subscribe("test", callback)
            
            # Simuler un événement
            client._handle_event("test", {"data": "message"})
            
            assert len(received) == 1
            assert received[0]["channel"] == "test"
    
    @pytest.mark.asyncio
    async def test_handle_event_inactive(self):
        """Test gestion événement sur abonnement inactif."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            received = []
            def callback(event):
                received.append(event)
            
            await client.subscribe("test", callback)
            client._subscriptions["test"].is_active = False
            
            # Ne devrait pas appeler le callback
            client._handle_event("test", {"data": "message"})
            
            assert len(received) == 0
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test désabonnement."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            await client.subscribe("test", lambda x: x)
            assert "test" in client._subscriptions
            
            result = await client.unsubscribe("test")
            
            assert result is True
            assert "test" not in client._subscriptions
    
    @pytest.mark.asyncio
    async def test_subscribe_chat(self):
        """Test abonnement au chat."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            result = await client.subscribe_chat("chat123", lambda x: x)
            
            assert result is True
            assert "chat:chat123" in client._subscriptions
    
    @pytest.mark.asyncio
    async def test_subscribe_notifications(self):
        """Test abonnement aux notifications."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            result = await client.subscribe_notifications(lambda x: x)
            
            assert result is True
            assert "notifications" in client._subscriptions
    
    @pytest.mark.asyncio
    async def test_subscribe_progress(self):
        """Test abonnement à la progression."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            result = await client.subscribe_progress("task123", lambda x: x)
            
            assert result is True
            assert "progress:task123" in client._subscriptions
    
    @pytest.mark.asyncio
    async def test_subscribe_library_updates(self):
        """Test abonnement aux mises à jour bibliothèque."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            result = await client.subscribe_library_updates(lambda x: x)
            
            assert result is True
            assert "library_updates" in client._subscriptions
    
    @pytest.mark.asyncio
    async def test_send_message_fallback(self):
        """Test envoi message en mode fallback."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            received = []
            def callback(event):
                received.append(event)
            
            await client.subscribe("test", callback)
            
            result = await client.send_message(
                channel_name="test",
                event="test_event",
                payload={"data": "test"}
            )
            
            assert result is True
            assert len(received) == 1
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test déconnexion."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client = SupabaseRealtimeClient()
            
            await client.subscribe("test1", lambda x: x)
            await client.subscribe("test2", lambda x: x)
            
            await client.disconnect()
            
            assert len(client._subscriptions) == 0
            assert client._connected is False


class TestChatManager:
    """Tests pour ChatManager."""
    
    def setup_method(self):
        reset_realtime_client()
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connexion et déconnexion."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            manager = ChatManager("chat123")
            
            result = await manager.connect(lambda x: x)
            assert result is True
            assert manager._is_connected is True
            
            await manager.disconnect()
            assert manager._is_connected is False
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test envoi message."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            manager = ChatManager("chat123")
            await manager.connect(lambda x: x)
            
            result = await manager.send_message("Hello", "user")
            
            assert result is True
            # Message ajouté via callback + directement = 2 messages en fallback
            assert len(manager.get_messages()) >= 1
    
    @pytest.mark.asyncio
    async def test_handle_message(self):
        """Test réception message."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            manager = ChatManager("chat123")
            
            received = []
            def on_message(event):
                received.append(event)
            
            await manager.connect(on_message)
            
            # Simuler un message reçu
            test_event = {"payload": {"content": "Test"}}
            manager._handle_message(test_event)
            
            assert len(received) == 1
            assert len(manager.get_messages()) == 1
    
    def test_get_messages(self):
        """Test récupération historique."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            manager = ChatManager("chat123")
            # Simuler des messages
            manager._messages = [
                {"content": "Hello"},
                {"content": "World"}
            ]
            
            messages = manager.get_messages()
            
            assert len(messages) == 2
            assert messages[0]["content"] == "Hello"


class TestSupabaseRealtimeClientFactory:
    """Tests pour la factory."""
    
    def setup_method(self):
        reset_realtime_client()
    
    def test_singleton(self):
        """Test pattern singleton."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client1 = get_realtime_client()
            client2 = get_realtime_client()
            assert client1 is client2
    
    def test_reset(self):
        """Test reset du singleton."""
        with patch('frontend.utils.supabase_realtime.SUPABASE_AVAILABLE', False):
            client1 = get_realtime_client()
            reset_realtime_client()
            client2 = get_realtime_client()
            assert client1 is not client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

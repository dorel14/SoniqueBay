"""
Tests unitaires pour le service d'opérations bulk.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys

# Create proper mock for Base with metadata
mock_base = MagicMock()
mock_base.metadata = MagicMock()

# Patch SQLAlchemy avant import
with patch.dict('sys.modules', {
    'sqlalchemy': MagicMock(),
    'sqlalchemy.ext': MagicMock(),
    'sqlalchemy.ext.asyncio': MagicMock(),
    'sqlalchemy.orm': MagicMock(),
    'sqlalchemy.orm.decl_api': MagicMock(),
    'sqlalchemy.dialects': MagicMock(),
    'sqlalchemy.dialects.postgresql': MagicMock(),
    'backend_worker.models.base': MagicMock(Base=mock_base),
}):
    # Mock all model modules to avoid import issues
    sys.modules['backend_worker.models'] = MagicMock()
    sys.modules['backend_worker.models.covers_model'] = MagicMock()
    sys.modules['backend_worker.models.genres_model'] = MagicMock()
    sys.modules['backend_worker.models.artists_model'] = MagicMock()
    sys.modules['backend_worker.models.albums_model'] = MagicMock()
    sys.modules['backend_worker.models.tracks_model'] = MagicMock()
    sys.modules['backend_worker.models.track_embeddings_model'] = MagicMock()
    sys.modules['backend_worker.models.track_mir_scores_model'] = MagicMock()
    sys.modules['backend_worker.models.track_mir_raw_model'] = MagicMock()
    sys.modules['backend_worker.models.track_mir_normalized_model'] = MagicMock()
    sys.modules['backend_worker.models.track_mir_synthetic_tags_model'] = MagicMock()
    sys.modules['backend_worker.models.chat_models'] = MagicMock()
    sys.modules['backend_worker.models.user_model'] = MagicMock()
    sys.modules['backend_worker.models.conversation_model'] = MagicMock()
    sys.modules['backend_worker.models.settings_model'] = MagicMock()
    sys.modules['backend_worker.models.scan_sessions_model'] = MagicMock()
    sys.modules['backend_worker.models.artist_embeddings_model'] = MagicMock()
    sys.modules['backend_worker.models.artist_similar_model'] = MagicMock()
    sys.modules['backend_worker.models.agent_model'] = MagicMock()
    sys.modules['backend_worker.models.agent_score_model'] = MagicMock()
    
    from backend_worker.services.bulk_operations_service import (
        BulkOperationsService,
        reset_bulk_operations_service,
    )


class MockAsyncSession:
    """Mock pour AsyncSession."""
    def __init__(self):
        self.execute = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False


class MockResult:
    """Mock pour le résultat d'une requête."""
    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class TestBulkOperationsService:
    """Tests pour BulkOperationsService."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_bulk_operations_service()
        self.service = BulkOperationsService()
        
        # Mock des modèles
        self.mock_track = MagicMock()
        self.mock_album = MagicMock()
        self.mock_artist = MagicMock()
        self.mock_embeddings = MagicMock()
        self.mock_mir_scores = MagicMock()
        
        self.service.models = {
            'Track': self.mock_track,
            'Album': self.mock_album,
            'Artist': self.mock_artist,
            'TrackEmbeddings': self.mock_embeddings,
            'TrackMIRScores': self.mock_mir_scores,
        }
    
    @pytest.mark.asyncio
    async def test_bulk_insert_tracks_success(self):
        """Test insertion bulk de pistes."""
        tracks_data = [
            {"id": 1, "title": "Track 1", "artist_id": 1},
            {"id": 2, "title": "Track 2", "artist_id": 2},
        ]
        
        # Mock session
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=2)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.bulk_insert_tracks(tracks_data, batch_size=1000)
            
            assert len(result) == 2
            assert result == [1, 2]
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_insert_tracks_empty(self):
        """Test insertion bulk avec liste vide."""
        result = await self.service.bulk_insert_tracks([], batch_size=1000)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_bulk_insert_albums_success(self):
        """Test insertion bulk d'albums."""
        albums_data = [
            {"id": 1, "title": "Album 1", "artist_id": 1},
            {"id": 2, "title": "Album 2", "artist_id": 2},
        ]
        
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=2)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.bulk_insert_albums(albums_data, batch_size=500)
            
            assert len(result) == 2
            mock_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_insert_artists_success(self):
        """Test insertion bulk d'artistes."""
        artists_data = [
            {"id": 1, "name": "Artist 1"},
            {"id": 2, "name": "Artist 2"},
        ]
        
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=2)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.bulk_insert_artists(artists_data, batch_size=500)
            
            assert len(result) == 2
            mock_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_success(self):
        """Test insertion bulk d'embeddings."""
        embeddings_data = [
            {"track_id": 1, "embedding": [0.1, 0.2], "model_name": "test"},
            {"track_id": 2, "embedding": [0.3, 0.4], "model_name": "test"},
        ]
        
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=2)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.bulk_insert_embeddings(embeddings_data, batch_size=500)
            
            assert result == 2
            mock_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_insert_mir_scores_success(self):
        """Test insertion bulk de scores MIR."""
        scores_data = [
            {"track_id": 1, "energy_score": 0.8},
            {"track_id": 2, "energy_score": 0.6},
        ]
        
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=2)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.bulk_insert_mir_scores(scores_data, batch_size=1000)
            
            assert result == 2
            mock_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_track_metadata_success(self):
        """Test mise à jour batch des métadonnées."""
        updates = [
            {"id": 1, "title": "Updated Track 1"},
            {"id": 2, "title": "Updated Track 2"},
        ]
        
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=1)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.update_track_metadata(updates)
            
            assert result == 2  # 2 mises à jour
            assert mock_session.execute.call_count == 2
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_track_metadata_empty(self):
        """Test mise à jour batch avec liste vide."""
        result = await self.service.update_track_metadata([])
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_delete_orphaned_records_success(self):
        """Test suppression des enregistrements orphelins."""
        mock_session = MockAsyncSession()
        mock_session.execute.return_value = MockResult(rowcount=5)
        
        with patch('backend_worker.services.bulk_operations_service.get_async_session') as mock_get_session:
            mock_get_session.return_value = self._async_generator(mock_session)
            
            result = await self.service.delete_orphaned_records('tracks', {'album_id': None})
            
            assert result == 5
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_orphaned_records_invalid_table(self):
        """Test suppression avec table invalide."""
        with pytest.raises(ValueError):
            await self.service.delete_orphaned_records('invalid_table', {'id': 1})
    
    def _async_generator(self, session):
        """Helper pour créer un async generator."""
        async def gen():
            yield session
        return gen()


class TestBulkOperationsServiceFactory:
    """Tests pour la factory de service."""
    
    def setup_method(self):
        reset_bulk_operations_service()
    
    def test_singleton_pattern(self):
        """Test que le service est un singleton."""
        with patch.dict('sys.modules', {
            'sqlalchemy': MagicMock(),
            'sqlalchemy.ext': MagicMock(),
            'sqlalchemy.ext.asyncio': MagicMock(),
            'sqlalchemy.orm': MagicMock(),
            'sqlalchemy.dialects': MagicMock(),
            'sqlalchemy.dialects.postgresql': MagicMock(),
        }):
            from backend_worker.services.bulk_operations_service import get_bulk_operations_service
            
            service1 = get_bulk_operations_service()
            service2 = get_bulk_operations_service()
            assert service1 is service2
    
    def test_reset_singleton(self):
        """Test le reset du singleton."""
        with patch.dict('sys.modules', {
            'sqlalchemy': MagicMock(),
            'sqlalchemy.ext': MagicMock(),
            'sqlalchemy.ext.asyncio': MagicMock(),
            'sqlalchemy.orm': MagicMock(),
            'sqlalchemy.dialects': MagicMock(),
            'sqlalchemy.dialects.postgresql': MagicMock(),
        }):
            from backend_worker.services.bulk_operations_service import (
                get_bulk_operations_service,
                reset_bulk_operations_service,
            )
            
            service1 = get_bulk_operations_service()
            reset_bulk_operations_service()
            service2 = get_bulk_operations_service()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

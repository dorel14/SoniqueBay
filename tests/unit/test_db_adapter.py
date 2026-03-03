"""
Tests unitaires pour la couche d'abstraction database (Phase 3).
Vérifie que DatabaseAdapter et BaseRepository fonctionnent correctement.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.api.repositories.base_repository import BaseRepository
from backend.api.utils.db_adapter import DatabaseAdapter, get_adapter
from backend.api.utils.db_config import USE_SUPABASE, get_db_backend, is_migrated


class TestDbConfig:
    """Tests pour la configuration database."""
    
    def test_use_supabase_flag_exists(self):
        """Vérifie que le flag USE_SUPABASE existe."""
        assert isinstance(USE_SUPABASE, bool)
    
    def test_is_migrated_with_supabase_disabled(self):
        """Test is_migrated quand USE_SUPABASE=False."""
        with patch('backend.api.utils.db_config.USE_SUPABASE', False):
            assert is_migrated("tracks") is False
            assert is_migrated("albums") is False
    
    def test_is_migrated_with_supabase_enabled(self):
        """Test is_migrated quand USE_SUPABASE=True."""
        with patch('backend.api.utils.db_config.USE_SUPABASE', True):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', {"tracks", "albums"}):
                assert is_migrated("tracks") is True
                assert is_migrated("albums") is True
                assert is_migrated("artists") is False
    
    def test_get_db_backend(self):
        """Test get_db_backend."""
        with patch('backend.api.utils.db_config.USE_SUPABASE', True):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', {"tracks"}):
                assert get_db_backend("tracks") == "supabase"
                assert get_db_backend("albums") == "sqlalchemy"


class TestDatabaseAdapter:
    """Tests pour DatabaseAdapter."""
    
    def test_adapter_initialization_supabase(self):
        """Test initialisation avec backend Supabase."""
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            adapter = DatabaseAdapter("tracks")
            assert adapter.table_name == "tracks"
            assert adapter.backend == "supabase"
    
    def test_adapter_initialization_sqlalchemy(self):
        """Test initialisation avec backend SQLAlchemy."""
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="sqlalchemy"):
            adapter = DatabaseAdapter("tracks")
            assert adapter.table_name == "tracks"
            assert adapter.backend == "sqlalchemy"
    
    @pytest.mark.asyncio
    async def test_adapter_get_supabase(self):
        """Test get() avec backend Supabase."""
        # Mock du client Supabase
        mock_response = Mock()
        mock_response.data = {"id": 1, "title": "Test Track"}
        
        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value = mock_table
        
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            with patch('backend.api.utils.db_adapter.get_supabase_service_client', return_value=mock_supabase):
                adapter = DatabaseAdapter("tracks")
                result = await adapter.get(id=1)
                
                assert result == {"id": 1, "title": "Test Track"}
                mock_supabase.table.assert_called_with("tracks")
    
    @pytest.mark.asyncio
    async def test_adapter_get_all_supabase(self):
        """Test get_all() avec backend Supabase."""
        mock_response = Mock()
        mock_response.data = [
            {"id": 1, "title": "Track 1"},
            {"id": 2, "title": "Track 2"}
        ]
        
        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.select.return_value.limit.return_value.offset.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value = mock_table
        
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            with patch('backend.api.utils.db_adapter.get_supabase_service_client', return_value=mock_supabase):
                adapter = DatabaseAdapter("tracks")
                result = await adapter.get_all(limit=10, offset=0)
                
                assert len(result) == 2
                assert result[0]["title"] == "Track 1"
    
    @pytest.mark.asyncio
    async def test_adapter_create_supabase(self):
        """Test create() avec backend Supabase."""
        mock_response = Mock()
        mock_response.data = [{"id": 1, "title": "New Track"}]
        
        mock_supabase = Mock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            with patch('backend.api.utils.db_adapter.get_supabase_service_client', return_value=mock_supabase):
                adapter = DatabaseAdapter("tracks")
                result = await adapter.create({"title": "New Track"})
                
                assert result["id"] == 1
                assert result["title"] == "New Track"
    
    @pytest.mark.asyncio
    async def test_adapter_update_supabase(self):
        """Test update() avec backend Supabase."""
        mock_response = Mock()
        mock_response.data = [{"id": 1, "title": "Updated Track"}]
        
        mock_supabase = Mock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            with patch('backend.api.utils.db_adapter.get_supabase_service_client', return_value=mock_supabase):
                adapter = DatabaseAdapter("tracks")
                result = await adapter.update(1, {"title": "Updated Track"})
                
                assert result["title"] == "Updated Track"
    
    @pytest.mark.asyncio
    async def test_adapter_delete_supabase(self):
        """Test delete() avec backend Supabase."""
        mock_response = Mock()
        mock_response.data = [{"id": 1}]
        
        mock_supabase = Mock()
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            with patch('backend.api.utils.db_adapter.get_supabase_service_client', return_value=mock_supabase):
                adapter = DatabaseAdapter("tracks")
                result = await adapter.delete(1)
                
                assert result is True


class TestBaseRepository:
    """Tests pour BaseRepository."""
    
    @pytest.mark.asyncio
    async def test_repository_get_by_id(self):
        """Test get_by_id()."""
        mock_adapter = AsyncMock()
        mock_adapter.get.return_value = {"id": 1, "title": "Test"}
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            with patch('backend.api.repositories.base_repository.logging'):
                repo = BaseRepository("tracks")
                result = await repo.get_by_id(1)
                
                assert result["id"] == 1
                mock_adapter.get.assert_called_once_with(id=1)
    
    @pytest.mark.asyncio
    async def test_repository_get_all(self):
        """Test get_all()."""
        mock_adapter = AsyncMock()
        mock_adapter.get_all.return_value = [
            {"id": 1, "title": "Track 1"},
            {"id": 2, "title": "Track 2"}
        ]
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            with patch('backend.api.repositories.base_repository.logging'):
                repo = BaseRepository("tracks")
                result = await repo.get_all(limit=10)
                
                assert len(result) == 2
                mock_adapter.get_all.assert_called_once_with(
                    filters=None, limit=10, offset=None, order_by=None
                )
    
    @pytest.mark.asyncio
    async def test_repository_create(self):
        """Test create()."""
        mock_adapter = AsyncMock()
        mock_adapter.create.return_value = {"id": 1, "title": "New Track"}
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            with patch('backend.api.repositories.base_repository.logging'):
                repo = BaseRepository("tracks")
                result = await repo.create({"title": "New Track"})
                
                assert result["id"] == 1
                mock_adapter.create.assert_called_once_with({"title": "New Track"})
    
    @pytest.mark.asyncio
    async def test_repository_exists(self):
        """Test exists()."""
        mock_adapter = AsyncMock()
        mock_adapter.get.return_value = {"id": 1}
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            with patch('backend.api.repositories.base_repository.logging'):
                repo = BaseRepository("tracks")
                result = await repo.exists(1)
                
                assert result is True


class TestGetAdapter:
    """Tests pour la factory get_adapter."""
    
    def test_get_adapter_returns_instance(self):
        """Test que get_adapter retourne une instance de DatabaseAdapter."""
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="sqlalchemy"):
            adapter = get_adapter("tracks")
            assert isinstance(adapter, DatabaseAdapter)
            assert adapter.table_name == "tracks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

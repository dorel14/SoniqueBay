"""
Tests pour le nouveau worker covers amélioré
Teste les fonctionnalités avancées de priorisation et cache intelligent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from backend_worker.background_tasks.worker_cover_improved import (
    process_image_task,
    batch_process_images,
    refresh_missing_images,
    cleanup_expired_cache,
    get_processing_stats
)
from backend_worker.services.image_priority_service import (
    ImagePriorityService,
    PriorityLevel,
    ImageSource,
    ProcessingContext
)
from backend_worker.services.redis_cache import ImageCacheService  # ✅ CORRIGÉ: Import du service unifié


class TestProcessImageTask:
    """Tests pour la tâche principale de traitement d'image."""
    
    @pytest.fixture
    def mock_context(self):
        """Fixture pour le contexte de traitement."""
        context = Mock()
        context.image_type = "album_cover"
        context.entity_id = 123
        context.entity_path = "/path/to/album"
        context.task_type = "metadata_extraction"
        context.priority = "high"
        context.metadata = {"quality": "high"}
        return context
    
    def test_process_image_task_with_valid_params(self):
        """Test de la tâche avec paramètres valides."""
        result = process_image_task(
            image_type="album_cover",
            entity_id=123,
            entity_path="/path/to/album",
            task_type="metadata_extraction",
            priority="high",
            metadata={"quality": "high"}
        )
        
        # Vérifier que la tâche retourne un résultat
        assert isinstance(result, dict)
        assert "status" in result or "error" in result
    
    def test_process_image_task_with_missing_params(self):
        """Test de la tâche avec paramètres manquants."""
        result = process_image_task(
            image_type="",  # Paramètre manquant
            entity_id=123,
            task_type="metadata_extraction"
        )
        
        assert "error" in result
        assert "image_type et task_type sont requis" in result["error"]
    
    def test_batch_process_images_with_empty_batch(self):
        """Test du traitement de batch vide."""
        result = batch_process_images([], priority="normal")
        
        assert "error" in result
        assert "Batch vide" in result["error"]
    
    @patch('os.getenv')
    def test_batch_process_images_with_data(self, mock_env):
        """Test du traitement de batch avec données."""
        # Simuler le mode test
        mock_env.return_value = "true"
        
        image_batch = [
            {"image_type": "album_cover", "entity_id": 1},
            {"image_type": "artist_image", "entity_id": 2}
        ]
        
        result = batch_process_images(image_batch, priority="normal")
        
        assert "processed" in result
        assert "successful" in result
        assert "failed" in result
        assert "skipped" in result


class TestRefreshMissingImages:
    """Tests pour l'actualisation des images manquantes."""
    
    @patch('os.getenv')
    def test_refresh_missing_images_with_test_mode(self, mock_env):
        """Test de l'actualisation en mode test."""
        mock_env.return_value = "true"
        
        result = refresh_missing_images(["album_cover"], limit=50)
        
        assert "message" in result
        assert "Mode test" in result["message"]
    
    @patch('os.getenv')
    def test_refresh_missing_images_with_empty_types(self, mock_env):
        """Test avec types d'images vides."""
        mock_env.return_value = None  # Pas en mode test
        
        result = refresh_missing_images([], limit=50)
        
        assert "message" in result
        assert "count" in result
        assert result["count"] == 0


class TestMaintenanceTasks:
    """Tests pour les tâches de maintenance."""
    
    @patch('os.getenv')
    def test_cleanup_expired_cache_test_mode(self, mock_env):
        """Test du nettoyage en mode test."""
        mock_env.return_value = "true"
        
        result = cleanup_expired_cache(ttl_seconds=3600)
        
        assert "cleaned" in result
        assert "message" in result
        assert result["cleaned"] == 0
    
    @patch('os.getenv')
    def test_get_processing_stats_test_mode(self, mock_env):
        """Test de récupération des stats en mode test."""
        mock_env.return_value = "true"
        
        result = get_processing_stats()
        
        assert "total_processed" in result
        assert "success_rate" in result
        assert "average_processing_time" in result
        assert "cache_hit_rate" in result
        assert "queue_size" in result


class TestPriorityService:
    """Tests pour le service de priorisation."""
    
    @pytest.fixture
    def priority_service(self):
        """Fixture pour le service."""
        return ImagePriorityService()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, priority_service):
        """Test l'initialisation du service."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            await priority_service.initialize()
            
            assert priority_service.redis_client is not None
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_priority_critical(self, priority_service):
        """Test l'évaluation de priorité critique."""
        context = ProcessingContext(
            image_type="album_cover",
            entity_id=123,
            source=ImageSource.EMBEDDED,
            is_new=True,
            access_count=10
        )
        
        priority_level, score = await priority_service.evaluate_priority(context)
        
        assert priority_level == PriorityLevel.CRITICAL
        assert score >= 15.0
    
    @pytest.mark.asyncio
    async def test_evaluate_priority_low(self, priority_service):
        """Test l'évaluation de priorité faible."""
        context = ProcessingContext(
            image_type="fanart",
            entity_id=123,
            source=ImageSource.LASTFM,
            is_new=False,
            access_count=0
        )
        
        priority_level, score = await priority_service.evaluate_priority(context)
        
        assert priority_level in [PriorityLevel.LOW, PriorityLevel.DEFERRED]
        assert score < 5.0
    
    @pytest.mark.asyncio
    async def test_prioritize_batch(self, priority_service):
        """Test la priorisation d'un batch."""
        image_batch = [
            {
                "image_type": "fanart",
                "entity_id": 1,
                "source": "lastfm",
                "is_new": False
            },
            {
                "image_type": "album_cover",
                "entity_id": 2,
                "source": "embedded",
                "is_new": True
            }
        ]
        
        prioritized = await priority_service.prioritize_batch(image_batch)
        
        # Le deuxième élément doit être premier (album_cover plus prioritaire)
        assert prioritized[0]["image_type"] == "album_cover"
        assert prioritized[1]["image_type"] == "fanart"
    
    def test_should_process_critical(self, priority_service):
        """Test la décision de traitement pour priorité critique."""
        context = ProcessingContext(
            image_type="album_cover",
            entity_id=123,
            source=ImageSource.EMBEDDED,
            is_new=True
        )
        
        # Simuler l'évaluation
        with patch.object(priority_service, 'evaluate_priority') as mock_eval:
            mock_eval.return_value = (PriorityLevel.CRITICAL, 20.0)
            with patch.object(priority_service, '_check_priority_quotas', return_value=True):
                with patch.object(priority_service, '_check_processing_queue', return_value=True):
                    result = asyncio.run(priority_service.should_process(context))
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_get_processing_stats(self, priority_service):
        """Test la récupération des statistiques."""
        with patch.object(priority_service, 'redis_client') as mock_redis:
            # Mock correctement configuré pour async/await
            async def mock_get(key):
                if "critical" in key:
                    return b'{"processed": 10, "success_rate": 0.9}'
                elif "high" in key:
                    return b'{"processed": 5, "success_rate": 0.8}'
                elif "total" in key:
                    return b'{"processed": 100, "success_rate": 0.85}'
                else:
                    return b'{"processed": 0, "success_rate": 0.0}'
            
            mock_redis.get = mock_get
            
            stats = await priority_service.get_processing_stats()
            
            assert "total" in stats
            assert stats["total"]["processed"] == 100


class TestCacheService:
    """Tests pour le service de cache."""
    
    @pytest.fixture
    def cache_service(self):
        """Fixture pour le service."""
        return ImageCacheService()
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_service):
        """Test l'initialisation du cache."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            await cache_service.initialize()
            
            assert cache_service.redis_client is not None
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_result(self, cache_service):
        """Test la mise en cache d'un résultat."""
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            test_data = {
                "cover_data": "base64_encoded_data",
                "mime_type": "image/jpeg",
                "source": "embedded"
            }
            
            success = await cache_service.cache_result(
                cache_key="album_cover:123",
                data=test_data,
                ttl=3600
            )
            
            assert success is True
            mock_client.setex.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_cached_result_hit(self, cache_service):
        """Test la récupération d'un résultat en cache (hit)."""
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Mock cache hit
            cached_data = b'{"cover_data": "cached_image", "mime_type": "image/jpeg"}'
            mock_client.get.return_value = cached_data
            
            result = await cache_service.get_cached_result("album_cover:123")
            
            assert result is not None
            assert result["cover_data"] == "cached_image"
            mock_client.get.assert_called_with("album_cover:123")
    
    @pytest.mark.asyncio
    async def test_get_cached_result_miss(self, cache_service):
        """Test la récupération d'un résultat en cache (miss)."""
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Mock cache miss
            mock_client.get.return_value = None
            
            result = await cache_service.get_cached_result("album_cover:456")
            
            assert result is None
            mock_client.get.assert_called_with("album_cover:456")
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service):
        """Test la récupération des statistiques du cache."""
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Mock du scan pour retourner quelques clés
            mock_client.scan.side_effect = [
                (0, [b"img:data:album_cover:1", b"img:data:album_cover:2"]),
                (0, [])  # Fin du scan
            ]
            
            # Mock des données de statistiques
            mock_client.info.return_value = {
                "used_memory_human": "10MB",
                "connected_clients": "5",
                "total_commands_processed": "1000"
            }
            
            stats = await cache_service.get_stats()
            
            assert "redis_info" in stats
            assert "cache_metrics" in stats
            assert "performance_metrics" in stats
            assert "hit_rate" in stats
            assert "used_memory" in stats["redis_info"]
            assert stats["redis_info"]["used_memory"] == "10MB"


class TestImageCacheServiceIntegration:
    """Tests d'intégration pour le service de cache d'images."""
    
    @pytest.mark.asyncio
    async def test_cache_service_basic_operations(self):
        """Test des opérations de base du service de cache."""
        cache_service = ImageCacheService()
        
        # Test avec mock Redis
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Test de mise en cache
            test_data = {
                "cover_data": "base64_encoded_image",
                "mime_type": "image/jpeg",
                "source": "embedded"
            }
            
            success = await cache_service.cache_result(
                cache_key="album_cover:123",
                data=test_data,
                ttl=3600
            )
            
            assert success is True
            # Vérifier qu'il y a au moins un appel setex
            assert mock_client.setex.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_cache_service_stats_method_compatibility(self):
        """Test de compatibilité avec l'ancienne méthode get_stats."""
        cache_service = ImageCacheService()
        
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Mock des méthodes Redis
            mock_client.info.return_value = {
                "used_memory": 1048576,
                "used_memory_human": "1MB",
                "maxmemory": 1073741824
            }
            
            # Mock scan pour retourner quelques clés
            mock_client.scan.side_effect = [
                (0, [b"img:data:album_cover:1", b"img:data:album_cover:2"]),
                (0, [])  # Fin du scan
            ]
            
            # Test de la méthode get_stats
            stats = await cache_service.get_stats()
            
            # Vérifier la structure des statistiques
            assert "redis_info" in stats
            assert "cache_metrics" in stats
            assert "performance_metrics" in stats
            assert "hit_rate" in stats
            assert "used_memory" in stats["redis_info"]
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_integration(self):
        """Test d'intégration du nettoyage du cache."""
        cache_service = ImageCacheService()
        
        with patch.object(cache_service, 'redis_client'):
            mock_client = AsyncMock()
            cache_service.redis_client = mock_client
            
            # Mock du scan avec des clés expirées
            mock_client.scan.side_effect = [
                (0, [b"img:data:expired1", b"img:data:expired2"]),
                (0, [])  # Fin du scan - seulement 2 clés dans ce cas
            ]
            
            mock_client.ttl.side_effect = [-1, -1]  # Toutes expirées
            mock_client.delete.return_value = 1
            
            cleaned_count = await cache_service.cleanup_expired()
            
            assert cleaned_count == 2
            assert mock_client.delete.call_count == 2
"""
Test de synchronisation de configuration Celery via Redis.
Valide que le worker publie et que le backend lit correctement la configuration.
"""

import pytest
import redis
import json
import os
import time
from unittest.mock import patch, MagicMock

# Import des modules à tester
from backend_worker.celery_config_source import get_unified_queues, get_unified_task_routes, get_unified_celery_config
from backend_worker.utils.celery_config_publisher import (
    publish_celery_config_to_redis,
    clear_celery_config_from_redis,
    serialize_queues_for_redis,
    serialize_routes_for_redis,
    serialize_base_config_for_redis
)
from backend.api.utils.celery_config_loader import (
    load_celery_config_from_redis,
    deserialize_queues_from_redis,
    deserialize_routes_from_redis,
    deserialize_base_config_from_redis,
    get_fallback_config
)


@pytest.fixture
def redis_client():
    """Fixture pour créer un client Redis de test."""
    # Utiliser une base de données Redis différente pour les tests
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    if redis_url.endswith('/0'):
        redis_url = redis_url[:-1] + '15'  # Utiliser DB 15 pour les tests
    else:
        redis_url += '/15'
    
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    
    # Nettoyer avant le test
    client.flushdb()
    
    yield client
    
    # Nettoyer après le test
    client.flushdb()
    client.close()


@pytest.fixture
def mock_redis_connection():
    """Mock de la connexion Redis pour les tests unitaires."""
    with patch('backend_worker.utils.celery_config_publisher.get_redis_connection') as mock_pub:
        with patch('backend.api.utils.celery_config_loader.get_redis_connection') as mock_load:
            mock_client = MagicMock()
            mock_pub.return_value = mock_client
            mock_load.return_value = mock_client
            yield mock_client


class TestConfigSerialization:
    """Test de sérialisation/désérialisation de la configuration."""
    
    def test_serialize_queues_for_redis(self):
        """Test sérialisation des queues."""
        queues = get_unified_queues()
        serialized = serialize_queues_for_redis(queues)
        
        # Vérifier que toutes les queues sont sérialisées
        assert len(serialized) == len(queues)
        
        # Vérifier le contenu d'une queue
        scan_queue_data = json.loads(serialized['scan'])
        assert scan_queue_data['name'] == 'scan'
        assert scan_queue_data['routing_key'] == 'scan'
    
    def test_deserialize_queues_from_redis(self):
        """Test désérialisation des queues."""
        # Créer des données de test
        test_data = {
            'scan': json.dumps({'name': 'scan', 'routing_key': 'scan', 'exchange': ''}),
            'extract': json.dumps({'name': 'extract', 'routing_key': 'extract', 'exchange': ''})
        }
        
        queues = deserialize_queues_from_redis(test_data)
        
        # Vérifier que les queues sont correctement désérialisées
        assert len(queues) == 2
        queue_names = [q.name for q in queues]
        assert 'scan' in queue_names
        assert 'extract' in queue_names
    
    def test_serialize_routes_for_redis(self):
        """Test sérialisation des routes."""
        routes = get_unified_task_routes()
        serialized = serialize_routes_for_redis(routes)
        
        # Vérifier que toutes les routes sont sérialisées
        assert len(serialized) == len(routes)
        
        # Vérifier le contenu d'une route
        scan_route = json.loads(serialized['scan.discovery'])
        assert scan_route['queue'] == 'scan'
    
    def test_deserialize_routes_from_redis(self):
        """Test désérialisation des routes."""
        # Créer des données de test
        test_data = {
            'scan.discovery': json.dumps({'queue': 'scan'}),
            'metadata.extract_batch': json.dumps({'queue': 'extract'})
        }
        
        routes = deserialize_routes_from_redis(test_data)
        
        # Vérifier que les routes sont correctement désérialisées
        assert len(routes) == 2
        assert routes['scan.discovery']['queue'] == 'scan'
        assert routes['metadata.extract_batch']['queue'] == 'extract'
    
    def test_serialize_base_config_for_redis(self):
        """Test sérialisation de la config de base."""
        config = get_unified_celery_config()
        serialized = serialize_base_config_for_redis(config)
        
        # Vérifier que les objets complexes sont exclus
        assert 'task_routes' not in serialized
        assert 'task_queues' not in serialized
        
        # Vérifier que les valeurs simples sont présentes
        assert 'task_serializer' in serialized
        assert json.loads(serialized['task_serializer']) == 'json'


class TestRedisIntegration:
    """Test d'intégration avec Redis."""
    
    def test_publish_and_load_config(self, redis_client):
        """Test complet de publication et chargement."""
        # Mock des connexions pour utiliser notre client de test
        with patch('backend_worker.utils.celery_config_publisher.get_redis_connection', return_value=redis_client):
            with patch('backend.api.utils.celery_config_loader.get_redis_connection', return_value=redis_client):
                
                # 1. Publier la configuration
                publish_celery_config_to_redis()
                
                # 2. Vérifier que la configuration est dans Redis
                version = redis_client.get('celery_config:version')
                assert version is not None
                
                queues_data = redis_client.hgetall('celery_config:queues')
                assert len(queues_data) > 0
                
                routes_data = redis_client.hgetall('celery_config:routes')
                assert len(routes_data) > 0
                
                base_config_data = redis_client.hgetall('celery_config:base')
                assert len(base_config_data) > 0
                
                # 3. Charger la configuration
                loaded_config = load_celery_config_from_redis()
                
                # 4. Vérifier que la configuration chargée est valide
                assert 'task_routes' in loaded_config
                assert 'task_queues' in loaded_config
                assert 'task_serializer' in loaded_config
                
                # 5. Vérifier le contenu spécifique
                assert 'scan.discovery' in loaded_config['task_routes']
                assert loaded_config['task_routes']['scan.discovery']['queue'] == 'scan'
    
    def test_clear_config(self, redis_client):
        """Test d'effacement de la configuration."""
        with patch('backend_worker.utils.celery_config_publisher.get_redis_connection', return_value=redis_client):
            # Publier d'abord
            publish_celery_config_to_redis()
            
            # Vérifier que c'est bien publié
            assert redis_client.exists('celery_config:version')
            
            # Effacer
            clear_celery_config_from_redis()
            
            # Vérifier que c'est effacé
            assert not redis_client.exists('celery_config:version')
            assert not redis_client.exists('celery_config:queues')
            assert not redis_client.exists('celery_config:routes')
            assert not redis_client.exists('celery_config:base')
    
    def test_fallback_config(self, redis_client):
        """Test de la configuration de fallback."""
        with patch('backend.api.utils.celery_config_loader.get_redis_connection', return_value=redis_client):
            # S'assurer qu'il n'y a pas de config dans Redis
            redis_client.flushdb()
            
            # Charger la config (devrait utiliser le fallback)
            fallback_config = get_fallback_config()
            loaded_config = load_celery_config_from_redis()
            
            # Vérifier que le fallback est utilisé
            assert loaded_config == fallback_config
            
            # Vérifier le contenu du fallback
            assert 'task_routes' in loaded_config
            assert 'task_queues' in loaded_config
            assert loaded_config['task_serializer'] == 'json'


class TestConfigConsistency:
    """Test de cohérence entre source et loader."""
    
    def test_config_consistency(self):
        """Test que la configuration source et le loader sont cohérents."""
        # Charger la config depuis la source
        source_config = get_unified_celery_config()
        source_queues = get_unified_queues()
        source_routes = get_unified_task_routes()
        
        # Vérifier la cohérence
        assert len(source_config['task_queues']) == len(source_queues)
        assert source_config['task_routes'] == source_routes
        
        # Vérifier quelques éléments spécifiques
        queue_names = [q.name for q in source_queues]
        expected_queues = ['scan', 'extract', 'batch', 'insert', 'covers', 'audio_analysis']
        for expected_queue in expected_queues:
            assert expected_queue in queue_names
        
        # Vérifier quelques routes spécifiques
        expected_routes = ['scan.discovery', 'metadata.extract_batch', 'audio_analysis.extract_features']
        for expected_route in expected_routes:
            assert expected_route in source_routes


class TestErrorHandling:
    """Test de la gestion d'erreurs."""
    
    def test_redis_connection_error(self, mock_redis_connection):
        """Test de gestion d'erreur de connexion Redis."""
        # Simuler une erreur de connexion
        mock_redis_connection.ping.side_effect = Exception("Connection failed")
        
        # La publication devrait lever une exception
        with pytest.raises(Exception):
            publish_celery_config_to_redis()
        
        # Le chargement devrait utiliser le fallback
        config = load_celery_config_from_redis()
        assert config == get_fallback_config()
    
    def test_malformed_data_handling(self, mock_redis_connection):
        """Test de gestion de données malformées."""
        # Configurer des données malformées dans Redis
        mock_redis_connection.get.return_value = "123456"
        mock_redis_connection.hgetall.return_value = {
            'scan': '{"malformed": json}',  # JSON malformé
            'extract': 'not_json'  # Pas du tout du JSON
        }
        
        # Le chargement devrait continuer avec le fallback
        config = load_celery_config_from_redis()
        assert config == get_fallback_config()


if __name__ == '__main__':
    # Exécution des tests en mode standalone
    pytest.main([__file__, '-v'])
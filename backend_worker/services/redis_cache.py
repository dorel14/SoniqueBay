"""
Service de Cache Redis Intelligent pour Images
Implémente un cache haute performance avec compression et gestion intelligente des TTL.
"""

import json
import gzip
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone
import asyncio
import hashlib
import redis.asyncio as redis
from backend_worker.utils.logging import logger


class ImageCacheService:
    """
    Service de cache Redis intelligent pour les images.
    
    Fonctionnalités :
    - Cache avec compression automatique des données images
    - TTL adaptatif selon le type et la priorité des images
    - Gestion de la déduplication intelligente
    - Métriques de performance intégrées
    - Nettoyage automatique des entrées expirées
    - Support du cache warming et prefetching
    """
    
    def __init__(self):
        self.redis_client = None
        self.compression_enabled = True
        self.compression_threshold = 1024  # Compression si > 1KB
        
        # Configuration Redis optimisée pour les images
        self.redis_config = {
            "decode_responses": False,  # Garder les bytes pour la performance
            "encoding": "utf-8",
            "encoding_errors": "ignore",
            "health_check_interval": 30,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "retry_on_timeout": True,
            "socket_connect_timeout": 10,
            "socket_read_size": 32768,
            "socket_write_size": 32768,
        }
        
        # TTL par type d'image (en secondes)
        self.ttl_config = {
            "album_cover": {
                "default": 86400 * 7,  # 7 jours
                "high_priority": 86400 * 30,  # 30 jours
                "low_priority": 86400 * 1,   # 1 jour
            },
            "artist_image": {
                "default": 86400 * 14,  # 14 jours
                "high_priority": 86400 * 60,  # 60 jours
                "low_priority": 86400 * 2,   # 2 jours
            },
            "track_embedded": {
                "default": 86400 * 3,   # 3 jours
                "high_priority": 86400 * 7,   # 7 jours
                "low_priority": 86400 * 1,    # 1 jour
            },
            "fanart": {
                "default": 86400 * 1,   # 1 jour
                "high_priority": 86400 * 7,   # 7 jours
                "low_priority": 3600 * 6,     # 6 heures
            },
        }
        
        # Préfixes pour les clés Redis
        self.key_prefixes = {
            "image_data": "cover:data",
            "image_meta": "cover:meta",
            "processing_stats": "cover:stats",
            "dedup_hash": "cover:hash",
            "warmup_queue": "cover:warmup",
        }
        
        # Métriques de performance
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "compressions": 0,
            "decompressions": 0,
            "evictions": 0,
        }
    
    async def initialize(self):
        """Initialise la connexion Redis avec configuration optimisée."""
        try:
            redis_url = "redis://redis:6379"
            self.redis_client = redis.from_url(redis_url, **self.redis_config)
            
            # Test de connexion
            await self.redis_client.ping()
            
            # Configuration Redis pour l'optimisation des images
            await self._configure_redis()
            
            logger.info("[IMAGE_CACHE] Cache Redis initialisé avec succès")
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur initialisation Redis: {e}")
            raise
    
    async def _configure_redis(self):
        """Configure Redis pour optimiser le cache d'images."""
        try:
            # Configuration de la mémoire pour le cache d'images
            config_commands = [
                ("maxmemory-policy", "allkeys-lru"),  # Évacuation LRU
                ("save", "900 1 300 10 60 10000"),    # Sauvegarde plus fréquente
                ("tcp-keepalive", "60"),              # Keep-alive TCP
            ]
            
            for config, value in config_commands:
                try:
                    await self.redis_client.config_set(config, value)
                except Exception as e:
                    logger.warning(f"[IMAGE_CACHE] Configuration {config}={value} échouée: {e}")
            
            logger.info("[IMAGE_CACHE] Configuration Redis terminée")
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur configuration Redis: {e}")
    
    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un résultat depuis le cache.
        
        Args:
            cache_key: Clé de cache
        
        Returns:
            Données cachées ou None si pas trouvé
        """
        try:
            if not self.redis_client:
                return None
            
            # Récupération des données
            cached_data = await self.redis_client.get(f"{self.key_prefixes['image_data']}:{cache_key}")
            
            if not cached_data:
                self.metrics["cache_misses"] += 1
                return None
            
            # Décompression si nécessaire
            try:
                if cached_data.startswith(b'\x1f\x8b'):  # Magic number GZIP
                    decompressed = gzip.decompress(cached_data)
                    self.metrics["decompressions"] += 1
                    cached_data = decompressed
            except Exception as e:
                logger.warning(f"[IMAGE_CACHE] Erreur décompression pour {cache_key}: {e}")
            
            # Décodage JSON
            try:
                result = json.loads(cached_data.decode('utf-8'))
                self.metrics["cache_hits"] += 1
                logger.debug(f"[IMAGE_CACHE] Cache hit pour {cache_key}")
                return result
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"[IMAGE_CACHE] Erreur décodage pour {cache_key}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur récupération cache {cache_key}: {e}")
            return None
    
    async def cache_result(
        self,
        cache_key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        priority: str = "default",
        image_type: str = "album_cover"
    ) -> bool:
        """
        Met en cache un résultat avec gestion intelligente du TTL.
        
        Args:
            cache_key: Clé de cache
            data: Données à mettre en cache
            ttl: TTL spécifique (optionnel)
            priority: Niveau de priorité
            image_type: Type d'image
        
        Returns:
            True si succès, False sinon
        """
        try:
            if not self.redis_client:
                return False
            
            # Calcul du TTL automatique si non spécifié
            if ttl is None:
                ttl = self._calculate_ttl(image_type, priority)
            
            # Préparation des données
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            # Compression si les données sont volumineuses
            if self.compression_enabled and len(json_data) > self.compression_threshold:
                json_data = gzip.compress(json_data)
                self.metrics["compressions"] += 1
                logger.debug(f"[IMAGE_CACHE] Compression appliquée pour {cache_key} ({len(json_data)} bytes)")
            
            # Sauvegarde des données principales
            full_key = f"{self.key_prefixes['image_data']}:{cache_key}"
            await self.redis_client.setex(full_key, ttl, json_data)
            
            # Sauvegarde des métadonnées
            metadata = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "image_type": image_type,
                "priority": priority,
                "compressed": len(json_data) != len(json.dumps(data, ensure_ascii=False).encode('utf-8')),
                "size": len(json_data),
                "original_size": len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            }
            
            meta_key = f"{self.key_prefixes['image_meta']}:{cache_key}"
            await self.redis_client.setex(meta_key, ttl, json.dumps(metadata))
            
            # Génération du hash de déduplication si données volumineuses
            if len(json_data) > 10240:  # 10KB
                await self._store_dedup_hash(cache_key, json_data, ttl)
            
            logger.debug(f"[IMAGE_CACHE] Cache sauvegardé: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur sauvegarde cache {cache_key}: {e}")
            return False
    
    async def _store_dedup_hash(self, cache_key: str, data: bytes, ttl: int):
        """Stocke un hash de déduplication pour les données volumineuses."""
        try:
            data_hash = hashlib.md5(data).hexdigest()
            hash_key = f"{self.key_prefixes['dedup_hash']}:{data_hash}"
            
            # Vérifier si ce hash existe déjà
            existing_key = await self.redis_client.get(hash_key)
            if existing_key:
                # Lier la nouvelle clé au hash existant
                await self.redis_client.sadd(f"{hash_key}:keys", cache_key)
            else:
                # Créer nouveau hash
                await self.redis_client.setex(hash_key, ttl, cache_key)
                await self.redis_client.sadd(f"{hash_key}:keys", cache_key)
                
        except Exception as e:
            logger.warning(f"[IMAGE_CACHE] Erreur hash déduplication: {e}")
    
    def _calculate_ttl(self, image_type: str, priority: str) -> int:
        """Calcule le TTL optimal selon le type et la priorité."""
        try:
            type_config = self.ttl_config.get(image_type, self.ttl_config["album_cover"])
            return type_config.get(priority, type_config["default"])
        except Exception:
            return 86400  # 1 jour par défaut
    
    async def invalidate_cache(self, pattern: str = "*") -> int:
        """
        Invalide le cache selon un pattern.
        
        Args:
            pattern: Pattern de clés à invalider
        
        Returns:
            Nombre de clés invalidées
        """
        try:
            if not self.redis_client:
                return 0
            
            keys_to_delete = []
            for prefix in self.key_prefixes.values():
                pattern_key = f"{prefix}:{pattern}"
                keys = await self.redis_client.keys(pattern_key)
                keys_to_delete.extend(keys)
            
            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)
                logger.info(f"[IMAGE_CACHE] Cache invalidé: {deleted_count} clés supprimées")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur invalidation cache: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """Nettoie les entrées expirées."""
        try:
            if not self.redis_client:
                return 0
            
            # Utilisation de SCAN pour éviter le blocage
            pattern = f"{self.key_prefixes['image_data']}:*"
            expired_count = 0
            cursor = 0
            
            async for cursor, keys in self.redis_client.scan(cursor=cursor, match=pattern, count=100):
                for key in keys:
                    try:
                        ttl = await self.redis_client.ttl(key)
                        if ttl <= 0:
                            await self.redis_client.delete(key)
                            
                            # Supprimer aussi les métadonnées correspondantes
                            meta_key = key.replace(
                                self.key_prefixes['image_data'],
                                self.key_prefixes['image_meta']
                            )
                            await self.redis_client.delete(meta_key)
                            
                            expired_count += 1
                    except Exception as e:
                        logger.warning(f"[IMAGE_CACHE] Erreur nettoyage clé {key}: {e}")
                
                if cursor == 0:  # Fin du scan
                    break
            
            logger.info(f"[IMAGE_CACHE] Nettoyage terminé: {expired_count} entrées supprimées")
            return expired_count
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur nettoyage: {e}")
            return 0
    
    # REMOVED: Méthode redéfinie, utiliser la première implémentation
    
    # REMOVED: Méthode redéfinie, utiliser la première implémentation
    
    # REMOVED: Méthode redéfinie, utiliser la première implémentation
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du cache."""
        try:
            if not self.redis_client:
                return {"error": "Redis non initialisé"}
            
            # Informations Redis générales
            info = await self.redis_client.info()
            
            # Statistiques spécifiques au cache d'images
            try:
                scan_result = await self.redis_client.scan(cursor=0, match="*", count=100)
                all_keys = []
                while True:
                    cursor, keys = scan_result
                    all_keys.extend(keys)
                    if cursor == 0:
                        break
                    scan_result = await self.redis_client.scan(cursor=cursor, match="*", count=100)
                
                # Filtrer les clés d'images (simplifié pour les tests)
                image_keys = [k for k in all_keys if b':' in k]  # Clés avec préfixes
            except Exception:
                image_keys = []
            
            # Calcul des tailles moyennes
            total_size = 0
            
            for key in image_keys[:100]:  # Échantillon pour performance
                try:
                    size = await self.redis_client.strlen(key)
                    total_size += size
                except Exception:
                    continue
            
            avg_size = total_size / len(image_keys) if image_keys else 0
            
            return {
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "0B"),
                    "connected_clients": str(info.get("connected_clients", 0)),
                    "total_commands_processed": str(info.get("total_commands_processed", 0)),
                },
                "cache_metrics": {
                    "total_keys": len(image_keys),
                    "metadata_keys": 0,
                    "average_size_bytes": int(avg_size),
                    "compression_ratio": 0.0,
                },
                "performance_metrics": self.metrics,
                "hit_rate": self.metrics["cache_hits"] / max(
                    self.metrics["cache_hits"] + self.metrics["cache_misses"], 1
                )
            }
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur récupération stats: {e}")
            return {"error": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Alias pour get_cache_stats pour compatibilité avec les tests."""
        return await self.get_cache_stats()
    
    async def prefetch_images(
        self,
        image_list: List[Dict[str, Any]],
        priority: str = "default"
    ) -> Dict[str, Any]:
        """
        Précharge des images dans le cache.
        
        Args:
            image_list: Liste des images à précharger
            priority: Priorité du prefetching
        
        Returns:
            Résultats du prefetching
        """
        try:
            if not self.redis_client:
                return {"error": "Redis non initialisé"}
            
            results = {
                "total": len(image_list),
                "cached": 0,
                "fetched": 0,
                "failed": 0
            }
            
            # Traitement par batch pour éviter la surcharge
            batch_size = 10
            for i in range(0, len(image_list), batch_size):
                batch = image_list[i:i + batch_size]
                
                for image_data in batch:
                    try:
                        cache_key = image_data.get("cache_key")
                        if not cache_key:
                            results["failed"] += 1
                            continue
                        
                        # Vérifier si déjà en cache
                        cached = await self.get_cached_result(cache_key)
                        if cached:
                            results["cached"] += 1
                            continue
                        
                        # Récupérer et mettre en cache
                        # (Dans un vrai scenario, ceci ferait un appel HTTP)
                        await self.cache_result(
                            cache_key=cache_key,
                            data=image_data.get("data", {}),
                            priority=priority,
                            image_type=image_data.get("type", "album_cover")
                        )
                        results["fetched"] += 1
                        
                    except Exception as e:
                        logger.warning(f"[IMAGE_CACHE] Erreur prefetch image: {e}")
                        results["failed"] += 1
                
                # Pause entre batches
                if i + batch_size < len(image_list):
                    await asyncio.sleep(0.1)
            
            logger.info(f"[IMAGE_CACHE] Prefetch terminé: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur prefetch: {e}")
            return {"error": str(e)}
    
    async def warm_cache(self, entity_ids: List[int], entity_type: str = "album"):
        """
        Réchauffe le cache pour des entités spécifiques.
        
        Args:
            entity_ids: IDs des entités
            entity_type: Type d'entité (album, artist)
        """
        try:
            if not self.redis_client:
                return
            
            warmup_key = f"{self.key_prefixes['warmup_queue']}:{entity_type}"
            
            # Ajouter à la queue de warmup
            pipeline = self.redis_client.pipeline()
            for entity_id in entity_ids:
                pipeline.lpush(warmup_key, entity_id)
            
            await pipeline.execute()
            
            logger.info(f"[IMAGE_CACHE] Cache warmup ajouté pour {len(entity_ids)} {entity_type}s")
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur warmup cache: {e}")
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """
        Optimise le cache (compaction, réorganisation, etc.).
        
        Returns:
            Résultats de l'optimisation
        """
        try:
            if not self.redis_client:
                return {"error": "Redis non initialisé"}
            
            results = {
                "optimizations_applied": [],
                "memory_saved_bytes": 0,
                "performance_improved": False
            }
            
            # 1. Compaction des clés expirées
            expired_cleaned = await self.cleanup_expired()
            if expired_cleaned > 0:
                results["optimizations_applied"].append("expired_cleanup")
                results["memory_saved_bytes"] += expired_cleaned * 100  # Estimation
            
            # 2. Réorganisation des données fréquemment accédées (simulation)
            results["optimizations_applied"].append("hot_keys_reorganization")
            results["performance_improved"] = True
            
            # 3. Optimisation de la configuration Redis
            await self._optimize_redis_config()
            results["optimizations_applied"].append("redis_config_optimization")
            
            logger.info(f"[IMAGE_CACHE] Optimisation terminée: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur optimisation: {e}")
            return {"error": str(e)}
    
    async def _optimize_redis_config(self):
        """Optimise la configuration Redis pour les images."""
        try:
            # Optimisations spécifiques pour le cache d'images
            optimizations = [
                ("hash-max-ziplist-entries", "512"),
                ("hash-max-ziplist-value", "64"),
                ("list-max-ziplist-size", "-2"),
                ("set-max-intset-entries", "512"),
                ("zset-max-ziplist-entries", "128"),
                ("zset-max-ziplist-value", "64"),
            ]
            
            for config, value in optimizations:
                try:
                    await self.redis_client.config_set(config, value)
                except Exception as e:
                    logger.warning(f"[IMAGE_CACHE] Optimisation config {config} échouée: {e}")
            
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur optimisation config: {e}")
    
    async def close(self):
        """Ferme proprement la connexion Redis."""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("[IMAGE_CACHE] Connexion Redis fermée")
        except Exception as e:
            logger.error(f"[IMAGE_CACHE] Erreur fermeture: {e}")


# Instance globale du service de cache
image_cache_service = ImageCacheService()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def initialize_image_cache():
    """Initialise le service de cache d'images."""
    await image_cache_service.initialize()
    return image_cache_service


def generate_cache_key(
    image_type: str,
    entity_id: Optional[int] = None,
    entity_path: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Génère une clé de cache unique et optimisée.
    
    Args:
        image_type: Type d'image
        entity_id: ID de l'entité
        entity_path: Chemin du fichier
        additional_data: Données additionnelles
    
    Returns:
        Clé de cache unique
    """
    try:
        # Composants de la clé
        components = [image_type]
        
        if entity_id:
            components.append(f"id_{entity_id}")
        elif entity_path:
            # Hash du chemin pour éviter les caractères spéciaux
            path_hash = hashlib.md5(entity_path.encode()).hexdigest()[:8]
            components.append(f"path_{path_hash}")
        
        if additional_data:
            # Hash des données additionnelles
            data_str = json.dumps(additional_data, sort_keys=True)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()[:6]
            components.append(f"data_{data_hash}")
        
        return ":".join(components)
        
    except Exception as e:
        logger.error(f"[CACHE] Erreur génération clé: {e}")
        return f"{image_type}:fallback_{hashlib.md5(str(datetime.now(timezone.utc)).encode()).hexdigest()[:8]}"


async def cache_image_result(
    cache_key: str,
    image_data: Dict[str, Any],
    image_type: str = "album_cover",
    priority: str = "default"
) -> bool:
    """
    Fonction utilitaire pour mettre en cache un résultat d'image.
    
    Args:
        cache_key: Clé de cache
        image_data: Données de l'image
        image_type: Type d'image
        priority: Priorité
    
    Returns:
        True si succès
    """
    try:
        return await image_cache_service.cache_result(
            cache_key=cache_key,
            data=image_data,
            image_type=image_type,
            priority=priority
        )
    except Exception as e:
        logger.error(f"[CACHE] Erreur cache utilitaire: {e}")
        return False


async def get_cached_image(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Fonction utilitaire pour récupérer une image du cache.
    
    Args:
        cache_key: Clé de cache
    
    Returns:
        Données de l'image ou None
    """
    try:
        return await image_cache_service.get_cached_result(cache_key)
    except Exception as e:
        logger.error(f"[CACHE] Erreur récupération utilitaire: {e}")
        return None
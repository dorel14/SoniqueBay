"""
Service de Queue Hybride - Redis avec Fallback Local
Combine Redis (prioritaire) avec file locale SQLite en cas de défaillance.
Optimisé pour Raspberry Pi avec retry automatique et monitoring mémoire.
"""

import time
import threading
from typing import Dict, Any, Optional
from backend_worker.utils.logging import logger
from backend_worker.services.deferred_queue_service import deferred_queue_service
from backend_worker.services.local_fallback_queue_service import local_fallback_queue_service


class HybridQueueService:
    """
    Service de queue hybride Redis + Local avec fallback automatique.
    
    Stratégie :
    1. Tente Redis en premier (performance optimale)
    2. En cas d'échec, utilise le fallback local SQLite
    3. Retry automatique avec backoff exponentiel
    4. Migration automatique vers Redis quand disponible
    5. Monitoring mémoire et cleanup automatique
    """

    def __init__(self):
        """Initialise le service hybride."""
        self.redis_service = deferred_queue_service
        self.local_service = local_fallback_queue_service
        self.redis_available = self.redis_service.redis is not None
        self.fallback_active = False
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1,  # 1 seconde
            'max_delay': 60,  # 1 minute max
            'backoff_factor': 2
        }
        self.lock = threading.Lock()
        
        logger.info(f"[HYBRID_QUEUE] Service initialisé - Redis disponible: {self.redis_available}")

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calcule le délai de retry avec backoff exponentiel."""
        delay = self.retry_config['base_delay'] * (self.retry_config['backoff_factor'] ** attempt)
        return min(delay, self.retry_config['max_delay'])

    def _test_redis_connection(self) -> bool:
        """Teste la connexion Redis et met à jour le statut."""
        try:
            if self.redis_service.redis:
                self.redis_service.redis.ping()
                if not self.redis_available:
                    logger.info("[HYBRID_QUEUE] Redis reconnecté avec succès")
                    self.redis_available = True
                return True
        except Exception as e:
            if self.redis_available:
                logger.warning(f"[HYBRID_QUEUE] Redis déconnecté: {str(e)}")
                self.redis_available = False
        return False

    def enqueue_task(self, queue_name: str, task_data: Dict[str, Any],
                    priority: str = "normal", delay_seconds: int = 0,
                    max_retries: int = 3) -> bool:
        """
        Ajoute une tâche avec fallback automatique.

        Args:
            queue_name: Nom de la queue
            task_data: Données de la tâche
            priority: Priorité ('high', 'normal', 'low')
            delay_seconds: Délai avant traitement
            max_retries: Nombre maximum de tentatives

        Returns:
            True si ajout réussi (Redis ou local)
        """
        task_id = f"{queue_name}:{int(time.time())}:{hash(str(task_data))}"
        
        # DIAGNOSTIC: Log détaillé des tentatives
        logger.info(f"[HYBRID_QUEUE DIAGNOSTIC] Tentative enqueue tâche {task_id}")
        logger.info(f"[HYBRID_QUEUE DIAGNOSTIC] Redis disponible: {self.redis_available}")
        logger.info(f"[HYBRID_QUEUE DIAGNOSTIC] Fallback actif: {self.fallback_active}")
        logger.info(f"[HYBRID_QUEUE DIAGNOSTIC] Données: {task_data}")
        
        # Stratégie 1: Redis (si disponible et pas en fallback forcé)
        if self.redis_available and not self.fallback_active:
            for attempt in range(self.retry_config['max_retries']):
                try:
                    logger.debug(f"[HYBRID_QUEUE] Tentative Redis #{attempt + 1} pour {task_id}")
                    
                    # Test de connexion avant tentative
                    if not self._test_redis_connection():
                        logger.warning(f"[HYBRID_QUEUE] Redis non disponible, passage au fallback")
                        break
                    
                    success = self.redis_service.enqueue_task(
                        queue_name, task_data, priority, delay_seconds, max_retries
                    )
                    
                    if success:
                        logger.info(f"[HYBRID_QUEUE] ✅ Tâche enqueued avec succès via Redis: {task_id}")
                        return True
                    else:
                        logger.warning(f"[HYBRID_QUEUE] ❌ Échec Redis tentative #{attempt + 1} pour {task_id}")
                        
                        # Vérifier l'état de Redis après échec
                        if self.redis_service.redis:
                            try:
                                info = self.redis_service.redis.info()
                                used_memory = info.get('used_memory', 0)
                                logger.error(f"[HYBRID_QUEUE DIAGNOSTIC] État Redis après échec: used_memory={used_memory} bytes")
                                
                                # Si mémoire saturée, activer fallback
                                if used_memory > 100 * 1024 * 1024:  # 100MB
                                    logger.warning(f"[HYBRID_QUEUE] Mémoire Redis saturée, activation fallback forcé")
                                    self.fallback_active = True
                                    break
                            except Exception as info_error:
                                logger.error(f"[HYBRID_QUEUE DIAGNOSTIC] Impossible d'obtenir info Redis: {info_error}")
                        
                        # Attendre avant retry
                        if attempt < self.retry_config['max_retries'] - 1:
                            delay = self._calculate_retry_delay(attempt)
                            logger.info(f"[HYBRID_QUEUE] Attente {delay}s avant retry Redis pour {task_id}")
                            time.sleep(delay)
                            
                except Exception as e:
                    logger.error(f"[HYBRID_QUEUE] Exception Redis tentative #{attempt + 1}: {str(e)}")
                    if attempt < self.retry_config['max_retries'] - 1:
                        delay = self._calculate_retry_delay(attempt)
                        time.sleep(delay)

        # Stratégie 2: Fallback local
        logger.info(f"[HYBRID_QUEUE] Utilisation fallback local pour {task_id}")
        try:
            success = self.local_service.enqueue_task(
                queue_name, task_data, priority, delay_seconds, max_retries
            )
            
            if success:
                logger.info(f"[HYBRID_QUEUE] ✅ Tâche enqueued avec succès via fallback local: {task_id}")
                self.fallback_active = True  # Rester en fallback après succès local
                return True
            else:
                logger.error(f"[HYBRID_QUEUE] ❌ Échec total - impossible d'enqueue la tâche {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"[HYBRID_QUEUE] Erreur fallback local pour {task_id}: {str(e)}")
            return False

    def dequeue_task(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la prochaine tâche (Redis优先, puis local).

        Args:
            queue_name: Nom de la queue

        Returns:
            Tâche à traiter ou None
        """
        # Stratégie 1: Redis (si disponible)
        if self.redis_available and not self.fallback_active:
            try:
                if self._test_redis_connection():
                    task = self.redis_service.dequeue_task(queue_name)
                    if task:
                        logger.debug(f"[HYBRID_QUEUE] Tâche récupérée via Redis: {task.get('id', 'unknown')}")
                        return task
            except Exception as e:
                logger.warning(f"[HYBRID_QUEUE] Erreur Redis dequeue, fallback local: {str(e)}")

        # Stratégie 2: Fallback local
        try:
            task = self.local_service.dequeue_task(queue_name)
            if task:
                logger.debug(f"[HYBRID_QUEUE] Tâche récupérée via fallback local: {task.get('id', 'unknown')}")
                return task
        except Exception as e:
            logger.error(f"[HYBRID_QUEUE] Erreur fallback local dequeue: {str(e)}")

        return None

    def complete_task(self, queue_name: str, task_id: str, success: bool = True,
                     error_message: str = None) -> bool:
        """
        Marque une tâche comme terminée.

        Args:
            queue_name: Nom de la queue
            task_id: ID de la tâche
            success: True si succès
            error_message: Message d'erreur si échec

        Returns:
            True si mise à jour réussie
        """
        # Déterminer où se trouve la tâche (Redis ou local)
        # Pour simplifier, on essaie les deux
        redis_success = False
        local_success = False
        
        if self.redis_available and not self.fallback_active:
            try:
                if self._test_redis_connection():
                    redis_success = self.redis_service.complete_task(queue_name, task_id, success, error_message)
            except Exception as e:
                logger.warning(f"[HYBRID_QUEUE] Erreur completion Redis: {str(e)}")

        try:
            local_success = self.local_service.complete_task(queue_name, task_id, success, error_message)
        except Exception as e:
            logger.error(f"[HYBRID_QUEUE] Erreur completion local: {str(e)}")

        return redis_success or local_success

    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """
        Retourne les statistiques combinées.

        Args:
            queue_name: Nom de la queue

        Returns:
            Statistiques combinées Redis + Local
        """
        stats = {
            "queue_name": queue_name,
            "redis_available": self.redis_available,
            "fallback_active": self.fallback_active,
            "redis_stats": {},
            "local_stats": {}
        }

        # Stats Redis
        if self.redis_available:
            try:
                if self._test_redis_connection():
                    stats["redis_stats"] = self.redis_service.get_queue_stats(queue_name)
            except Exception as e:
                logger.warning(f"[HYBRID_QUEUE] Erreur stats Redis: {str(e)}")

        # Stats Local
        try:
            stats["local_stats"] = self.local_service.get_queue_stats(queue_name)
        except Exception as e:
            logger.error(f"[HYBRID_QUEUE] Erreur stats local: {str(e)}")

        return stats

    def attempt_redis_recovery(self) -> bool:
        """
        Tente de récupérer la connexion Redis.

        Returns:
            True si Redis est de nouveau disponible
        """
        logger.info("[HYBRID_QUEUE] Tentative de récupération Redis...")
        
        old_status = self.redis_available
        
        if self._test_redis_connection():
            self.redis_available = True
            self.fallback_active = False
            
            # Migrer les tâches locales vers Redis
            try:
                migrated = self.local_service.migrate_to_redis(self.redis_service)
                if migrated > 0:
                    logger.info(f"[HYBRID_QUEUE] {migrated} tâches migrées de local vers Redis")
            except Exception as e:
                logger.error(f"[HYBRID_QUEUE] Erreur migration vers Redis: {str(e)}")
            
            if not old_status:
                logger.info("[HYBRID_QUEUE] ✅ Redis récupéré avec succès")
            return True
        else:
            logger.warning("[HYBRID_QUEUE] ❌ Redis toujours indisponible")
            return False

    def get_system_health(self) -> Dict[str, Any]:
        """
        Retourne l'état de santé du système de queues.

        Returns:
            État de santé complet
        """
        health = {
            "timestamp": time.time(),
            "redis_available": self.redis_available,
            "fallback_active": self.fallback_active,
            "system_status": "healthy"
        }

        # Test Redis
        if self.redis_available:
            try:
                if self._test_redis_connection():
                    info = self.redis_service.redis.info()
                    health["redis_memory"] = {
                        "used": info.get('used_memory', 0),
                        "peak": info.get('used_memory_peak', 0),
                        "max": info.get('maxmemory', 0)
                    }
                    health["redis_connected_clients"] = info.get('connected_clients', 0)
                else:
                    health["redis_available"] = False
            except Exception as e:
                health["redis_available"] = False
                health["redis_error"] = str(e)

        # Test Local
        try:
            local_memory = self.local_service._get_memory_usage()
            health["local_memory"] = {
                "used": local_memory,
                "max": self.local_service.max_memory_usage
            }
            
            # Statut global
            if not health["redis_available"] and health["local_memory"]["used"] > health["local_memory"]["max"]:
                health["system_status"] = "critical"
            elif not health["redis_available"] or health["local_memory"]["used"] > health["local_memory"]["max"] * 0.8:
                health["system_status"] = "warning"
                
        except Exception as e:
            health["local_error"] = str(e)
            health["system_status"] = "critical"

        return health

    def cleanup_expired_tasks(self) -> Dict[str, Any]:
        """
        Nettoie les tâches expirées dans les deux systèmes.

        Returns:
            Résultats du cleanup
        """
        results = {"redis": {}, "local": {}}
        
        # Cleanup Redis
        if self.redis_available:
            try:
                if self._test_redis_connection():
                    results["redis"] = self.redis_service.cleanup_expired_tasks()
            except Exception as e:
                logger.warning(f"[HYBRID_QUEUE] Erreur cleanup Redis: {str(e)}")
                results["redis"]["error"] = str(e)

        # Cleanup Local
        try:
            results["local"] = self.local_service.cleanup_all()
        except Exception as e:
            logger.error(f"[HYBRID_QUEUE] Erreur cleanup local: {str(e)}")
            results["local"]["error"] = str(e)

        return results


# Instance globale du service hybride
hybrid_queue_service = HybridQueueService()
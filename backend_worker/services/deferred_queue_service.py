"""
Service de Queue Différée - Gestion des tâches lourdes différées
Utilise Redis pour stocker les tâches en attente et Celery Beat pour les traiter périodiquement.
"""

import json
import redis
import time
from typing import Dict, List, Any, Optional
from backend_worker.utils.logging import logger


class DeferredQueueService:
    """
    Service de gestion des queues différées avec Redis.

    Permet de différer les tâches lourdes (enrichissement, covers, vecteurs)
    pour éviter la surcharge lors des scans initiaux.
    """

    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        """Initialise le service avec Redis."""
        try:
            self.redis = redis.from_url(redis_url)
            self.redis.ping()  # Test de connexion
            logger.info("[DEFERRED_QUEUE] Connexion Redis établie")
        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur connexion Redis: {str(e)}")
            self.redis = None

    def enqueue_task(self, queue_name: str, task_data: Dict[str, Any],
                    priority: str = "normal", delay_seconds: int = 0,
                    max_retries: int = 3) -> bool:
        """
        Ajoute une tâche dans une queue différée.

        Args:
            queue_name: Nom de la queue (ex: 'deferred_enrichment')
            task_data: Données de la tâche
            priority: Priorité ('high', 'normal', 'low')
            delay_seconds: Délai avant traitement (0 = immédiat)
            max_retries: Nombre maximum de tentatives

        Returns:
            True si ajout réussi
        """
        if not self.redis:
            logger.error("[DEFERRED_QUEUE] Redis non disponible")
            return False

        try:
            # Clé Redis pour la queue
            queue_key = f"deferred_queue:{queue_name}"

            # Structure de la tâche
            task = {
                "id": f"{queue_name}:{int(time.time())}:{hash(str(task_data))}",
                "queue": queue_name,
                "data": task_data,
                "priority": priority,
                "created_at": time.time(),
                "process_at": time.time() + delay_seconds,
                "retries": 0,
                "max_retries": max_retries,
                "status": "pending"
            }

            # Score pour tri par priorité et timestamp
            priority_scores = {"high": 0, "normal": 1, "low": 2}
            score = priority_scores.get(priority, 1) * 1000000000 + task["process_at"]

            # Ajout dans Redis Sorted Set
            self.redis.zadd(queue_key, {json.dumps(task): score})

            logger.info(f"[DEFERRED_QUEUE] Tâche ajoutée: {queue_name} -> {task['id']}")
            return True

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur ajout tâche: {str(e)}")
            return False

    def dequeue_task(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère et marque comme 'processing' la prochaine tâche à traiter.

        Args:
            queue_name: Nom de la queue

        Returns:
            Tâche à traiter ou None
        """
        if not self.redis:
            return None

        try:
            queue_key = f"deferred_queue:{queue_name}"
            processing_key = f"deferred_processing:{queue_name}"

            # Récupère la tâche avec le score le plus bas (priorité + timestamp)
            tasks = self.redis.zrange(queue_key, 0, 0, withscores=True)

            if not tasks:
                return None

            task_json, score = tasks[0]
            task = json.loads(task_json)

            # Vérifie si c'est le moment de traiter
            if task["process_at"] > time.time():
                return None  # Pas encore le moment

            # Déplace vers processing
            self.redis.zrem(queue_key, task_json)
            task["status"] = "processing"
            task["processing_started_at"] = time.time()

            self.redis.setex(
                f"{processing_key}:{task['id']}",
                3600,  # Expire après 1 heure si pas terminé
                json.dumps(task)
            )

            logger.info(f"[DEFERRED_QUEUE] Tâche défilée: {queue_name} -> {task['id']}")
            return task

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur défilement tâche: {str(e)}")
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
        if not self.redis:
            return False

        try:
            processing_key = f"deferred_processing:{queue_name}:{task_id}"

            task_json = self.redis.get(processing_key)
            if not task_json:
                logger.warning(f"[DEFERRED_QUEUE] Tâche non trouvée: {task_id}")
                return False

            task = json.loads(task_json)

            # Met à jour le statut
            task["status"] = "completed" if success else "failed"
            task["completed_at"] = time.time()
            if error_message:
                task["error"] = error_message

            # Supprime de processing et archive
            self.redis.delete(processing_key)

            if success:
                # Archive les succès (expire après 7 jours)
                archive_key = f"deferred_archive:{queue_name}"
                self.redis.setex(f"{archive_key}:{task_id}", 604800, json.dumps(task))
            else:
                # Retry si possible
                if task["retries"] < task["max_retries"]:
                    task["retries"] += 1
                    task["status"] = "pending"
                    task["last_error"] = error_message
                    task["process_at"] = time.time() + (60 * task["retries"])  # Backoff

                    queue_key = f"deferred_queue:{queue_name}"
                    priority_scores = {"high": 0, "normal": 1, "low": 2}
                    score = priority_scores.get(task["priority"], 1) * 1000000000 + task["process_at"]
                    self.redis.zadd(queue_key, {json.dumps(task): score})

                    logger.info(f"[DEFERRED_QUEUE] Tâche retry: {task_id} (tentative {task['retries']})")
                else:
                    # Archive les échecs définitifs
                    failed_key = f"deferred_failed:{queue_name}"
                    self.redis.setex(f"{failed_key}:{task_id}", 2592000, json.dumps(task))  # 30 jours
                    logger.error(f"[DEFERRED_QUEUE] Tâche failed définitivement: {task_id}")

            return True

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur completion tâche: {str(e)}")
            return False

    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """
        Retourne les statistiques d'une queue.

        Args:
            queue_name: Nom de la queue

        Returns:
            Statistiques de la queue
        """
        if not self.redis:
            return {"error": "Redis non disponible"}

        try:
            queue_key = f"deferred_queue:{queue_name}"
            processing_key = f"deferred_processing:{queue_name}"
            archive_key = f"deferred_archive:{queue_name}"
            failed_key = f"deferred_failed:{queue_name}"

            # Compte les tâches en attente
            pending_count = self.redis.zcard(queue_key)

            # Compte les tâches en cours
            processing_keys = self.redis.keys(f"{processing_key}:*")
            processing_count = len(processing_keys) if processing_keys else 0

            # Compte les archives
            archive_keys = self.redis.keys(f"{archive_key}:*")
            archive_count = len(archive_keys) if archive_keys else 0

            failed_keys = self.redis.keys(f"{failed_key}:*")
            failed_count = len(failed_keys) if failed_keys else 0

            # Tâches les plus anciennes
            oldest_pending = None
            if pending_count > 0:
                oldest_tasks = self.redis.zrange(queue_key, 0, 0, withscores=True)
                if oldest_tasks:
                    oldest_task = json.loads(oldest_tasks[0][0])
                    oldest_pending = time.time() - oldest_task["created_at"]

            return {
                "queue_name": queue_name,
                "pending": pending_count,
                "processing": processing_count,
                "completed": archive_count,
                "failed": failed_count,
                "total": pending_count + processing_count + archive_count + failed_count,
                "oldest_pending_seconds": oldest_pending
            }

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur stats queue: {str(e)}")
            return {"error": str(e)}

    def cleanup_expired_tasks(self, max_age_seconds: int = 86400) -> Dict[str, int]:
        """
        Nettoie les tâches expirées dans toutes les queues.

        Args:
            max_age_seconds: Âge maximum en secondes (défaut: 24h)

        Returns:
            Nombre de tâches nettoyées par queue
        """
        if not self.redis:
            return {"error": "Redis non disponible"}

        try:
            cleaned = {}
            cutoff_time = time.time() - max_age_seconds

            # Nettoie toutes les queues deferred_*
            queue_keys = self.redis.keys("deferred_queue:*")

            for queue_key in queue_keys:
                queue_name = queue_key.decode().replace("deferred_queue:", "")

                # Récupère toutes les tâches
                tasks = self.redis.zrange(queue_key, 0, -1, withscores=True)
                expired_tasks = []

                for task_json, score in tasks:
                    task = json.loads(task_json)
                    if task["created_at"] < cutoff_time:
                        expired_tasks.append(task_json)

                if expired_tasks:
                    self.redis.zrem(queue_key, *expired_tasks)
                    cleaned[queue_name] = len(expired_tasks)
                    logger.info(f"[DEFERRED_QUEUE] Nettoyé {len(expired_tasks)} tâches expirées dans {queue_name}")

            return cleaned

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur nettoyage: {str(e)}")
            return {"error": str(e)}

    def get_failed_tasks(self, queue_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les tâches échouées pour analyse.

        Args:
            queue_name: Nom de la queue
            limit: Nombre maximum de tâches

        Returns:
            Liste des tâches échouées
        """
        if not self.redis:
            return []

        try:
            failed_key = f"deferred_failed:{queue_name}"
            failed_keys = self.redis.keys(f"{failed_key}:*")

            if not failed_keys:
                return []

            # Récupère les tâches (limité)
            failed_tasks = []
            for key in failed_keys[:limit]:
                task_json = self.redis.get(key)
                if task_json:
                    failed_tasks.append(json.loads(task_json))

            return failed_tasks

        except Exception as e:
            logger.error(f"[DEFERRED_QUEUE] Erreur récupération tâches échouées: {str(e)}")
            return []


# Instance globale du service
deferred_queue_service = DeferredQueueService()
"""
Service de File d'Attente Locale - Fallback en cas de défaillance Redis
Utilise SQLite pour stocker les tâches localement quand Redis n'est pas disponible.
Optimisé pour Raspberry Pi avec gestion mémoire limitée.
"""

import sqlite3
import json
import time
import threading
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from backend_worker.utils.logging import logger


class LocalFallbackQueueService:
    """
    Service de queue locale utilisant SQLite comme fallback.
    
    Fonctionnalités :
    - Stockage persistant SQLite
    - Thread-safe avec locks
    - Auto-cleanup des tâches expirées
    - Monitoring mémoire
    - Migration automatique vers Redis quand disponible
    """

    def __init__(self, db_path: str = "/app/data/local_deferred_queue.db"):
        """Initialise le service avec SQLite."""
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
        # Configuration RPi4
        self.max_memory_usage = 100 * 1024 * 1024  # 100MB max
        self.cleanup_threshold = 80 * 1024 * 1024   # 80MB cleanup trigger
        self.task_ttl = 7 * 24 * 3600  # 7 jours TTL
        
        logger.info(f"[LOCAL_QUEUE] Service initialisé avec base: {db_path}")

    def _init_database(self):
        """Initialise la base de données SQLite."""
        try:
            # Créer le répertoire si nécessaire
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS deferred_tasks (
                        id TEXT PRIMARY KEY,
                        queue_name TEXT NOT NULL,
                        task_data TEXT NOT NULL,
                        priority TEXT NOT NULL DEFAULT 'normal',
                        created_at REAL NOT NULL,
                        process_at REAL NOT NULL,
                        retries INTEGER NOT NULL DEFAULT 0,
                        max_retries INTEGER NOT NULL DEFAULT 3,
                        status TEXT NOT NULL DEFAULT 'pending',
                        error_message TEXT,
                        UNIQUE(id)
                    )
                """)
                
                # Index pour performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON deferred_tasks(queue_name, status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_process_at ON deferred_tasks(process_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON deferred_tasks(priority)")
                
                conn.commit()
                logger.info("[LOCAL_QUEUE] Base de données initialisée avec succès")
                
        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur initialisation DB: {str(e)}")
            raise

    def _get_memory_usage(self) -> int:
        """Retourne l'usage mémoire actuel de la base en bytes."""
        try:
            if os.path.exists(self.db_path):
                return os.path.getsize(self.db_path)
            return 0
        except Exception:
            return 0

    def _cleanup_expired_tasks(self):
        """Nettoie les tâches expirées pour économiser l'espace."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cutoff_time = time.time() - self.task_ttl
                    cursor = conn.execute(
                        "DELETE FROM deferred_tasks WHERE created_at < ? AND status IN ('completed', 'failed')",
                        (cutoff_time,)
                    )
                    deleted_count = cursor.rowcount
                    
                    if deleted_count > 0:
                        conn.commit()
                        logger.info(f"[LOCAL_QUEUE] Nettoyé {deleted_count} tâches expirées")
                        
        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur cleanup: {str(e)}")

    def enqueue_task(self, queue_name: str, task_data: Dict[str, Any],
                    priority: str = "normal", delay_seconds: int = 0,
                    max_retries: int = 3) -> bool:
        """
        Ajoute une tâche dans la queue locale.

        Args:
            queue_name: Nom de la queue
            task_data: Données de la tâche
            priority: Priorité ('high', 'normal', 'low')
            delay_seconds: Délai avant traitement
            max_retries: Nombre maximum de tentatives

        Returns:
            True si ajout réussi
        """
        try:
            # Vérifier mémoire avant ajout
            memory_usage = self._get_memory_usage()
            if memory_usage > self.max_memory_usage:
                logger.warning(f"[LOCAL_QUEUE] Mémoire limite atteinte ({memory_usage} bytes), cleanup...")
                self._cleanup_expired_tasks()
                
                # Vérifier à nouveau après cleanup
                memory_usage = self._get_memory_usage()
                if memory_usage > self.max_memory_usage:
                    logger.error(f"[LOCAL_QUEUE] Mémoire insuffisante même après cleanup")
                    return False

            # Générer ID unique
            task_id = f"{queue_name}:{int(time.time())}:{hash(str(task_data))}"
            
            # Préparer les données
            priority_scores = {"high": 0, "normal": 1, "low": 2}
            score = priority_scores.get(priority, 1) * 1000000000 + (time.time() + delay_seconds)
            
            task_record = {
                "id": task_id,
                "queue": queue_name,
                "data": task_data,
                "priority": priority,
                "created_at": time.time(),
                "process_at": time.time() + delay_seconds,
                "retries": 0,
                "max_retries": max_retries,
                "status": "pending"
            }

            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO deferred_tasks 
                        (id, queue_name, task_data, priority, created_at, process_at, retries, max_retries, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task_record["id"],
                        queue_name,
                        json.dumps(task_record),
                        priority,
                        task_record["created_at"],
                        task_record["process_at"],
                        task_record["retries"],
                        task_record["max_retries"],
                        task_record["status"]
                    ))
                    conn.commit()

            logger.info(f"[LOCAL_QUEUE] Tâche ajoutée: {queue_name} -> {task_id}")
            
            # Cleanup si nécessaire
            if memory_usage > self.cleanup_threshold:
                self._cleanup_expired_tasks()
                
            return True

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur ajout tâche: {str(e)}")
            return False

    def dequeue_task(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la prochaine tâche à traiter.

        Args:
            queue_name: Nom de la queue

        Returns:
            Tâche à traiter ou None
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Récupérer la tâche la plus prioritaire
                    cursor = conn.execute("""
                        SELECT task_data FROM deferred_tasks 
                        WHERE queue_name = ? AND status = 'pending' AND process_at <= ?
                        ORDER BY priority, process_at
                        LIMIT 1
                    """, (queue_name, time.time()))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    task_record = json.loads(row[0])
                    
                    # Marquer comme en cours
                    conn.execute("""
                        UPDATE deferred_tasks 
                        SET status = 'processing', 
                            processing_started_at = ?
                        WHERE id = ?
                    """, (time.time(), task_record["id"]))
                    conn.commit()
                    
                    logger.info(f"[LOCAL_QUEUE] Tâche défilée: {queue_name} -> {task_record['id']}")
                    return task_record

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur défilement tâche: {str(e)}")
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
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Récupérer la tâche
                    cursor = conn.execute(
                        "SELECT task_data, retries, max_retries FROM deferred_tasks WHERE id = ?",
                        (task_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        logger.warning(f"[LOCAL_QUEUE] Tâche non trouvée: {task_id}")
                        return False
                    
                    task_record = json.loads(row[0])
                    retries = row[1]
                    max_retries = row[2]
                    
                    if success:
                        # Marquer comme terminée
                        conn.execute("""
                            UPDATE deferred_tasks 
                            SET status = 'completed', completed_at = ?, error_message = ?
                            WHERE id = ?
                        """, (time.time(), error_message, task_id))
                        logger.info(f"[LOCAL_QUEUE] Tâche terminée: {task_id}")
                    else:
                        # Retry si possible
                        if retries < max_retries:
                            new_retries = retries + 1
                            next_attempt = time.time() + (60 * new_retries)  # Backoff
                            
                            conn.execute("""
                                UPDATE deferred_tasks 
                                SET retries = ?, process_at = ?, status = 'pending', error_message = ?
                                WHERE id = ?
                            """, (new_retries, next_attempt, error_message, task_id))
                            logger.info(f"[LOCAL_QUEUE] Tâche retry: {task_id} (tentative {new_retries})")
                        else:
                            # Échec définitif
                            conn.execute("""
                                UPDATE deferred_tasks 
                                SET status = 'failed', completed_at = ?, error_message = ?
                                WHERE id = ?
                            """, (time.time(), error_message, task_id))
                            logger.error(f"[LOCAL_QUEUE] Tâche échouée définitivement: {task_id}")
                    
                    conn.commit()
                    return True

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur completion tâche: {str(e)}")
            return False

    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """
        Retourne les statistiques d'une queue.

        Args:
            queue_name: Nom de la queue

        Returns:
            Statistiques de la queue
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Compter par statut
                    stats = {}
                    for status in ['pending', 'processing', 'completed', 'failed']:
                        cursor = conn.execute(
                            "SELECT COUNT(*) FROM deferred_tasks WHERE queue_name = ? AND status = ?",
                            (queue_name, status)
                        )
                        stats[status] = cursor.fetchone()[0]
                    
                    # Tâche la plus ancienne
                    cursor = conn.execute("""
                        SELECT created_at FROM deferred_tasks 
                        WHERE queue_name = ? AND status = 'pending'
                        ORDER BY created_at ASC LIMIT 1
                    """, (queue_name,))
                    row = cursor.fetchone()
                    oldest_pending = time.time() - row[0] if row else None
                    
                    # Mémoire utilisée
                    memory_usage = self._get_memory_usage()
                    
                    return {
                        "queue_name": queue_name,
                        "pending": stats.get('pending', 0),
                        "processing": stats.get('processing', 0),
                        "completed": stats.get('completed', 0),
                        "failed": stats.get('failed', 0),
                        "total": sum(stats.values()),
                        "oldest_pending_seconds": oldest_pending,
                        "memory_usage_bytes": memory_usage,
                        "memory_usage_mb": memory_usage / (1024 * 1024)
                    }

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur stats queue: {str(e)}")
            return {"error": str(e)}

    def migrate_to_redis(self, redis_service) -> int:
        """
        Migre les tâches vers Redis quand il devient disponible.

        Args:
            redis_service: Service Redis fonctionnel

        Returns:
            Nombre de tâches migrées
        """
        try:
            migrated = 0
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT id, queue_name, task_data, priority, created_at, process_at, retries, max_retries
                        FROM deferred_tasks WHERE status = 'pending'
                    """)
                    
                    for row in cursor.fetchall():
                        task_id, queue_name, task_data_json, priority, created_at, process_at, retries, max_retries = row
                        task_data = json.loads(task_data_json)
                        
                        # Calculer le délai restant
                        delay_seconds = max(0, int(process_at - time.time()))
                        
                        # Ajouter à Redis
                        success = redis_service.enqueue_task(
                            queue_name,
                            task_data,
                            priority=priority,
                            delay_seconds=delay_seconds,
                            max_retries=max_retries
                        )
                        
                        if success:
                            # Marquer comme migrée
                            conn.execute("""
                                UPDATE deferred_tasks 
                                SET status = 'migrated', migrated_at = ?
                                WHERE id = ?
                            """, (time.time(), task_id))
                            migrated += 1
                        else:
                            logger.warning(f"[LOCAL_QUEUE] Échec migration tâche {task_id}")
                    
                    conn.commit()
                    
            if migrated > 0:
                logger.info(f"[LOCAL_QUEUE] {migrated} tâches migrées vers Redis")
                
            return migrated

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur migration vers Redis: {str(e)}")
            return 0

    def cleanup_all(self) -> Dict[str, int]:
        """Nettoie toutes les tâches expirées."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cutoff_time = time.time() - self.task_ttl
                    
                    # Nettoyer par statut
                    cleaned = {}
                    for status in ['completed', 'failed', 'migrated']:
                        cursor = conn.execute(
                            "DELETE FROM deferred_tasks WHERE status = ? AND created_at < ?",
                            (status, cutoff_time)
                        )
                        cleaned[status] = cursor.rowcount
                    
                    conn.commit()
                    
                    # Vacuum pour réduire la taille du fichier
                    conn.execute("VACUUM")
                    
                    logger.info(f"[LOCAL_QUEUE] Cleanup terminé: {cleaned}")
                    return cleaned

        except Exception as e:
            logger.error(f"[LOCAL_QUEUE] Erreur cleanup global: {str(e)}")
            return {}


# Instance globale du service
local_fallback_queue_service = LocalFallbackQueueService()
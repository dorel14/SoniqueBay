"""
Service de messages de progression pour SoniqueBay.
Gère l'envoi de messages système via Redis pub/sub pour affichage dans le chat.
Auteur : Kilo Code
"""
import json
import time
from typing import Optional, Dict, Any
import redis
from frontend.utils.logging import logger


class ProgressMessageService:
    """Service pour envoyer des messages de progression via Redis pub/sub."""

    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.last_message_time = 0
        self.min_interval = 0.5  # Minimum 500ms entre messages pour éviter spam

    def _get_redis_client(self) -> redis.Redis:
        """Obtient ou crée une connexion Redis."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                logger.debug("Connexion Redis établie pour les messages de progression")
            except Exception as e:
                logger.error(f"Erreur connexion Redis: {e}")
                raise
        return self.redis_client

    def send_progress_message(self, task_type: str, message: str, current: Optional[int] = None,
                            total: Optional[int] = None, task_id: Optional[str] = None) -> None:
        """
        Envoie un message de progression via Redis pub/sub.

        Args:
            task_type: Type de tâche (scan, metadata, vectorization, etc.)
            message: Message descriptif
            current: Compteur actuel (optionnel)
            total: Total attendu (optionnel)
            task_id: ID de la tâche (optionnel)
        """
        try:
            # Rate limiting pour éviter spam sur RPi4
            current_time = time.time()
            if current_time - self.last_message_time < self.min_interval:
                return
            self.last_message_time = current_time

            # Construction du message
            progress_data = {
                "type": "system_progress",
                "task_type": task_type,
                "message": message,
                "timestamp": current_time
            }

            if current is not None:
                progress_data["current"] = current
            if total is not None:
                progress_data["total"] = total
            if task_id:
                progress_data["task_id"] = task_id

            # Formatage du message pour affichage
            display_message = self._format_display_message(progress_data)

            # Message complet pour SSE
            sse_message = {
                "type": "system_progress",
                "message": display_message,
                "data": progress_data
            }

            # Publication via Redis pub/sub
            redis_client = self._get_redis_client()
            redis_client.publish("soniquebay:progress", json.dumps(sse_message))

            logger.debug(f"Message progression envoyé: {task_type} - {message}")

        except Exception as e:
            logger.error(f"Erreur envoi message progression: {e}")

    def _format_display_message(self, data: Dict[str, Any]) -> str:
        """
        Formate le message pour affichage dans le chat.

        Args:
            data: Données du message de progression

        Returns:
            Message formaté pour l'affichage
        """
        task_type = data.get("task_type", "tâche")
        message = data.get("message", "")
        current = data.get("current")
        total = data.get("total")

        # Traduction des types de tâches
        task_labels = {
            "scan": "Scan",
            "metadata": "Métadonnées",
            "vectorization": "Vectorisation",
            "enrichment": "Enrichissement",
            "audio_analysis": "Analyse audio"
        }

        task_label = task_labels.get(task_type, task_type.capitalize())

        # Construction du message
        if current is not None and total is not None and total > 0:
            percentage = int((current / total) * 100)
            return f"{task_label}: {message} ({current}/{total} - {percentage}%)"
        elif current is not None:
            return f"{task_label}: {message} ({current})"
        else:
            return f"{task_label}: {message}"

    def send_completion_message(self, task_type: str, success: bool = True,
                              task_id: Optional[str] = None) -> None:
        """
        Envoie un message de fin de tâche.

        Args:
            task_type: Type de tâche terminée
            success: True si succès, False si échec
            task_id: ID de la tâche (optionnel)
        """
        status = "terminée avec succès" if success else "échouée"
        message = f"Tâche {status}"

        self.send_progress_message(
            task_type=task_type,
            message=message,
            task_id=task_id
        )


# Instance globale du service
progress_service = ProgressMessageService()
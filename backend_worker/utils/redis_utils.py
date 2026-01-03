"""
Utils Redis - PubSub générique et robuste pour SoniqueBay

Fournit des fonctions pour publier et écouter des événements Redis
de manière asynchrone et thread-safe.

Optimisé pour Raspberry Pi :
- Connexions Redis limitées
- Reconnexion automatique
- Timeouts courts
- Gestion d'erreurs robuste

Conventions :
- Logs via backend_worker.utils.logging
- Docstrings pour toutes fonctions
- Annotations de type
- Imports absolus
"""

import asyncio
import json
import redis.asyncio as redis
from typing import Dict, Any, Callable, Optional, List
from backend_worker.utils.logging import logger


class RedisManager:
    """
    Gestionnaire Redis singleton pour PubSub et opérations de cache.

    Optimisé pour Raspberry Pi avec reconnexion automatique et timeouts courts.
    """

    _instance: Optional['RedisManager'] = None
    _redis_client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_client(self) -> redis.Redis:
        """
        Récupère ou crée une connexion Redis.

        Returns:
            Client Redis configuré
        """
        if self._redis_client is None:
            try:
                # Configuration Redis robuste pour éviter les erreurs PubSub
                self._redis_client = redis.Redis(
                    host='redis',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_timeout=5.0,  # Timeout court pour Raspberry Pi
                    socket_connect_timeout=5.0,
                    retry_on_timeout=True,
                    max_connections=10,  # Limité pour Raspberry Pi
                    # Configurations spécifiques pour PubSub
                    health_check_interval=30,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                )
                # Test de connexion
                await self._redis_client.ping()
                logger.info("[REDIS] Connexion Redis établie")
                
                # Configurer la connexion pour PubSub
                await self._ensure_pubsub_ready()
                
            except Exception as e:
                logger.error(f"[REDIS] Erreur connexion Redis: {e}")
                self._redis_client = None
                raise

        return self._redis_client
    
    async def _ensure_pubsub_ready(self):
        """
        S'assure que la connexion est prête pour PubSub.
        Évite l'erreur 'pubsub connection not set'.
        """
        try:
            # Test simple pour vérifier que PubSub fonctionne
            test_client = self._redis_client
            pubsub = test_client.pubsub()
            # Ne pas s'abonner, juste vérifier que l'objet peut être créé
            await pubsub.get_message(timeout=0.1)
            await pubsub.close()
            logger.debug("[REDIS] PubSub prêt")
        except Exception as e:
            logger.warning(f"[REDIS] Problème PubSub détecté: {e}")

    async def close(self):
        """Ferme la connexion Redis proprement."""
        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("[REDIS] Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"[REDIS] Erreur fermeture connexion: {e}")
            finally:
                self._redis_client = None


# Instance singleton
redis_manager = RedisManager()


async def publish_event(channel: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Publie un événement dans Redis.

    Args:
        channel: Canal Redis
        event_type: Type d'événement
        payload: Données de l'événement

    Returns:
        True si succès, False sinon
    """
    try:
        client = await redis_manager.get_client()
        message = {
            "type": event_type,
            "timestamp": asyncio.get_event_loop().time(),
            **payload
        }

        result = await client.publish(channel, json.dumps(message))
        logger.debug(f"[REDIS] Événement publié sur {channel}: {event_type}")
        return result > 0

    except Exception as e:
        logger.error(f"[REDIS] Erreur publication {channel}: {e}")
        return False


async def listen_events(channel: str, callback: Callable[[Dict[str, Any]], None],
                       event_types: Optional[List[str]] = None) -> None:
    """
    Écoute les événements Redis de manière asynchrone avec gestion robuste des erreurs.

    Args:
        channel: Canal Redis à écouter
        callback: Fonction appelée pour chaque événement
        event_types: Types d'événements à filtrer (None = tous)
    """
    pubsub = None
    try:
        client = await redis_manager.get_client()
        
        # Créer et configurer le PubSub de manière robuste
        pubsub = client.pubsub()
        
        # S'abonner au canal avec gestion d'erreur
        try:
            await pubsub.subscribe(channel)
            logger.info(f"[REDIS] Abonnement réussi au canal: {channel}")
        except Exception as e:
            logger.error(f"[REDIS] Échec abonnement {channel}: {e}")
            raise

        logger.info(f"[REDIS] Écoute démarrée sur canal: {channel}")

        # Boucle d'écoute avec gestion robuste des erreurs
        try:
            while True:
                try:
                    # Attendre les messages avec timeout pour permettre la reconnexion
                    message = await pubsub.get_message(timeout=1.0)
                    
                    if message is None:
                        continue
                        
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])

                            # Filtrage par type d'événement
                            if event_types and data.get('type') not in event_types:
                                continue

                            # Gestion flexible des callbacks sync/async
                            import inspect
                            if inspect.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)

                        except json.JSONDecodeError as e:
                            logger.error(f"[REDIS] Erreur décodage JSON: {e}")
                        except Exception as e:
                            logger.error(f"[REDIS] Erreur callback: {e}")
                    
                    elif message['type'] == 'subscribe':
                        logger.debug(f"[REDIS] Confirmation abonnement: {message}")
                    
                    elif message['type'] == 'unsubscribe':
                        logger.info(f"[REDIS] Désabonnement: {message}")
                        break
                        
                except asyncio.TimeoutError:
                    # Timeout normal, continuer la boucle
                    continue
                except Exception as e:
                    logger.error(f"[REDIS] Erreur traitement message: {e}")
                    # Continuer même en cas d'erreur sur un message
                    continue

        except Exception as e:
            logger.error(f"[REDIS] Erreur boucle écoute {channel}: {e}")
            raise
        finally:
            # Nettoyage propre du PubSub
            try:
                if pubsub:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                logger.info(f"[REDIS] Écoute arrêtée proprement sur canal: {channel}")
            except Exception as e:
                logger.warning(f"[REDIS] Erreur nettoyage PubSub: {e}")

    except Exception as e:
        logger.error(f"[REDIS] Erreur initialisation écoute {channel}: {e}")
        # Tentative de nettoyage en cas d'erreur
        try:
            if pubsub:
                await pubsub.close()
        except Exception:
            pass
        raise


class VectorizationEventListener:
    """
    Listener spécialisé pour les événements de vectorisation.

    Écoute le canal 'tracks.to_vectorize' et déclenche les tâches Celery
    pour le calcul des vecteurs selon le schéma du prompt.
    """

    def __init__(self):
        self.celery_app = None

    async def start_listening(self):
        """
        Démarre l'écoute des événements de vectorisation.
        """
        logger.info("[VECTOR_LISTENER] Démarrage du listener de vectorisation")

        def handle_vectorization_event(event_data: Dict[str, Any]):
            """Gère un événement de vectorisation selon le schéma du prompt."""
            try:
                track_id = event_data.get('track_id')

                if track_id:
                    logger.info(f"[VECTOR_LISTENER] Track à vectoriser: {track_id}")

                    # Import ici pour éviter les imports circulaires
                    from backend_worker.celery_app import celery

                    # Déclencher la tâche Celery avec le payload Redis
                    celery.send_task(
                        'calculate_vector',
                        args=[track_id, event_data],
                        queue='vectorization',
                        priority=5
                    )

            except Exception as e:
                logger.error(f"[VECTOR_LISTENER] Erreur traitement événement: {e}")

        # Démarrer l'écoute sur le canal spécifié
        await listen_events('tracks.to_vectorize', handle_vectorization_event, ['track_created', 'track_updated'])

    async def stop_listening(self):
        """Arrête l'écoute."""
        await redis_manager.close()
        logger.info("[VECTOR_LISTENER] Listener de vectorisation arrêté")


# Instance singleton du listener
vectorization_listener = VectorizationEventListener()


async def publish_vectorization_event(track_id: int, metadata: Dict[str, Any],
                                    event_type: str = 'track_created') -> bool:
    """
    Publie un événement de vectorisation selon le schéma du prompt.

    Args:
        track_id: ID de la track
        metadata: Métadonnées de la track (artist, genres, moods, bpm, duration)
        event_type: Type d'événement ('track_created', 'track_updated')

    Returns:
        True si succès
    """
    # Adapter le payload au schéma spécifié
    vectorization_payload = {
        'track_id': str(track_id),
        'artist': metadata.get('artist'),
        'genres': metadata.get('genre_tags', []) if isinstance(metadata.get('genre_tags'), list) else [metadata.get('genre', '')],
        'moods': metadata.get('mood_tags', []) if isinstance(metadata.get('mood_tags'), list) else [],
        'bpm': metadata.get('bpm'),
        'duration': metadata.get('duration')
    }

    return await publish_event(
        'tracks.to_vectorize',
        event_type,
        vectorization_payload
    )


async def publish_progress_event(task_id: str, step: str, current: int, total: int,
                               percent: float, **kwargs) -> bool:
    """
    Publie un événement de progression.

    Args:
        task_id: ID de la tâche
        step: Étape actuelle
        current: Valeur actuelle
        total: Valeur totale
        percent: Pourcentage
        **kwargs: Données supplémentaires

    Returns:
        True si succès
    """
    return await publish_event(
        'progress',
        'progress_update',
        {
            'task_id': task_id,
            'step': step,
            'current': current,
            'total': total,
            'percent': percent,
            **kwargs
        }
    )
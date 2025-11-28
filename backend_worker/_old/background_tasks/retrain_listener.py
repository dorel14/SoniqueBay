"""
Listener Redis pour les demandes de retrain du recommender_api.

Architecture :
- Recommender API publie dans Redis
- Backend Worker écoute Redis et exécute les retrains

Optimisé pour RPi4 :
- Délai configurable avant retrain (éviter surcharge CPU)
- Gestion des priorités (high/medium/low)
- Retard différé pour éviter conflits avec scans actifs

Auteur : Kilo Code
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis.asyncio as redis

from backend_worker.services.vectorization_service import OptimizedVectorizationService
from backend_worker.services.model_persistence_service import ModelVersioningService
from backend_worker.utils.logging import logger


class RetrainRequest:
    """Représente une demande de retrain."""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialise la demande."""
        self.trigger_reason = data.get('trigger_reason', 'unknown')
        self.priority = data.get('priority', 'medium')
        self.delay_minutes = data.get('delay_minutes', 120)
        self.message = data.get('message', '')
        self.details = data.get('details', {})
        self.timestamp = datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
        
        # Calculer l'heure d'exécution
        self.execute_at = self.timestamp + timedelta(minutes=self.delay_minutes)
    
    def should_execute(self) -> bool:
        """Vérifie si la demande doit être exécutée."""
        return datetime.now() >= self.execute_at
    
    def get_priority_score(self) -> int:
        """Retourne un score de priorité (plus haut = plus prioritaire)."""
        scores = {
            'critical': 100,
            'high': 80,
            'medium': 50,
            'low': 20,
            'none': 0
        }
        return scores.get(self.priority, 50)


class RetrainExecutor:
    """Exécuteur des retrains avec gestion des priorités."""
    
    def __init__(self):
        """Initialise l'exécuteur."""
        self.vectorization_service = None
        self.versioning_service = None
        self.pending_requests = []
        self.is_processing = False
        
        logger.info("RetrainExecutor initialisé")
    
    async def execute_retrain(self, request: RetrainRequest) -> Dict[str, Any]:
        """
        Exécute un retrain selon les paramètres de la demande.
        
        Args:
            request: Demande de retrain à exécuter
            
        Returns:
            Résultat de l'exécution
        """
        if self.is_processing:
            logger.warning("Retrain déjà en cours, demande mise en attente")
            return {
                'status': 'delayed',
                'reason': 'retrain_in_progress',
                'message': 'Retrain en cours, sera re-essayé plus tard'
            }
        
        try:
            self.is_processing = True
            logger.info(f"[RETRAIN] Exécution retrain: {request.message}")
            
            # Initialiser les services si nécessaire
            if not self.vectorization_service:
                self.vectorization_service = OptimizedVectorizationService()
            
            if not self.versioning_service:
                self.versioning_service = ModelVersioningService()
            
            # Exécuter le retrain avec versioning
            result = await self.versioning_service.retrain_with_versioning(force=True)
            
            # Ajouter les métadonnées de l'exécution
            result['execution_info'] = {
                'trigger_reason': request.trigger_reason,
                'priority': request.priority,
                'delay_applied': request.delay_minutes,
                'execute_at': request.execute_at.isoformat(),
                'executed_at': datetime.now().isoformat()
            }
            
            logger.info(f"[RETRAIN] Retrain terminé: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"[RETRAIN] Erreur execution retrain: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'execution_info': {
                    'trigger_reason': request.trigger_reason,
                    'priority': request.priority,
                    'error_at': datetime.now().isoformat()
                }
            }
        finally:
            self.is_processing = False
    
    def add_request(self, request: RetrainRequest):
        """Ajoute une demande à la file d'attente."""
        self.pending_requests.append(request)
        self.pending_requests.sort(key=lambda r: r.execute_at)
        
        logger.info(f"[RETRAIN] Demande ajoutée: {request.priority} ({len(self.pending_requests)} en attente)")
    
    def get_next_request(self) -> Optional[RetrainRequest]:
        """Récupère la prochaine demande à exécuter."""
        datetime.now()
        
        # Filtrer les demandes prêtes
        ready_requests = [r for r in self.pending_requests if r.should_execute()]
        
        if not ready_requests:
            return None
        
        # Trier par priorité
        ready_requests.sort(key=lambda r: r.get_priority_score(), reverse=True)
        
        # Retourner la demande la plus prioritaire
        request = ready_requests[0]
        self.pending_requests.remove(request)
        
        return request
    
    def cleanup_old_requests(self):
        """Nettoie les anciennes demandes expirées."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        original_count = len(self.pending_requests)
        
        self.pending_requests = [
            r for r in self.pending_requests 
            if r.execute_at > cutoff_time
        ]
        
        cleaned = original_count - len(self.pending_requests)
        if cleaned > 0:
            logger.info(f"[RETRAIN] Nettoyage: {cleaned} anciennes demandes supprimées")


class RedisRetrainListener:
    """Listener Redis pour les demandes de retrain."""
    
    def __init__(self):
        """Initialise le listener."""
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.pubsub = None
        self.redis_client = None
        self.executor = RetrainExecutor()
        self.is_running = False
        self.check_interval = 30  # Vérification toutes les 30 secondes
        
        logger.info("RedisRetrainListener initialisé")
    
    async def start_listening(self):
        """Démarre l'écoute Redis."""
        try:
            self.is_running = True
            logger.info("[REDIS_LISTENER] Démarrage écoute Redis")
            
            # Se connecter à Redis
            self.redis_client = redis.from_url(self.redis_url)
            self.pubsub = self.redis_client.pubsub()
            
            # S'abonner au canal de vectorisation
            await self.pubsub.subscribe('vectorization_events')
            
            # Démarrer les tâches
            listen_task = asyncio.create_task(self._listen_messages())
            process_task = asyncio.create_task(self._process_requests())
            cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Attendre que l'une des tâches se termine
            try:
                await asyncio.gather(listen_task, process_task, cleanup_task)
            except asyncio.CancelledError:
                logger.info("[REDIS_LISTENER] Arrêt demandé")
            finally:
                await self._cleanup()
                
        except Exception as e:
            logger.error(f"[REDIS_LISTENER] Erreur démarrage: {e}")
            self.is_running = False
    
    async def _listen_messages(self):
        """Écoute les messages Redis."""
        try:
            while self.is_running:
                try:
                    message = await self.pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        await self._handle_message(message)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"[REDIS_LISTENER] Erreur réception message: {e}")
                    await asyncio.sleep(5)  # Attendre avant retry
                    
        except Exception as e:
            logger.error(f"[REDIS_LISTENER] Erreur écoute: {e}")
    
    async def _handle_message(self, message):
        """Traite un message reçu."""
        try:
            data = json.loads(message['data'])
            
            if data.get('type') == 'vectorizer_retrain_request':
                request = RetrainRequest(data)
                
                # Vérifier les règles de santé RPi4
                if await self._should_delay_for_health(request):
                    logger.info(f"[REDIS_LISTENER] Retrain différé pour santé RPi4: {request.priority}")
                    # Ajouter avec délai supplémentaire
                    request.execute_at = datetime.now() + timedelta(hours=2)
                
                self.executor.add_request(request)
                logger.info(f"[REDIS_LISTENER] Demande retrain reçue: {request.priority}")
            
        except Exception as e:
            logger.error(f"[REDIS_LISTENER] Erreur traitement message: {e}")
    
    async def _should_delay_for_health(self, request: RetrainRequest) -> bool:
        """
        Vérifie si le retrain doit être différé pour la santé RPi4.
        
        Args:
            request: Demande de retrain
            
        Returns:
            True si retrain doit être différé
        """
        try:
            # Vérifier si un scan est en cours (charge CPU élevée)
            # TODO: Intégrer avec le système de scan existant
            
            # Vérifier la priorité
            if request.priority in ['critical', 'high']:
                return False  # Ne pas différer les priorités hautes
            
            # Vérifier l'heure (éviter retrain en journée sur RPi4)
            now = datetime.now()
            hour = now.hour
            
            # Ne pas retrain entre 8h et 22h (heures d'utilisation)
            if 8 <= hour <= 22 and request.priority != 'critical':
                logger.info(f"[RPI4_HEALTH] Retrain différé (heure active: {hour}h)")
                return True
            
            # Vérifier le jour (éviter weekend)
            if now.weekday() >= 5:  # Samedi=5, Dimanche=6
                if request.priority != 'critical':
                    logger.info("[RPI4_HEALTH] Retrain différé (weekend)")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"[RPI4_HEALTH] Erreur vérification: {e}")
            return False
    
    async def _process_requests(self):
        """Traite les demandes en attente."""
        try:
            while self.is_running:
                try:
                    # Nettoyer les anciennes demandes
                    self.executor.cleanup_old_requests()
                    
                    # Traiter la prochaine demande
                    request = self.executor.get_next_request()
                    if request:
                        logger.info(f"[RETRAIN_PROCESS] Traitement demande: {request.priority}")
                        
                        result = await self.executor.execute_retrain(request)
                        
                        # Log du résultat
                        status = result.get('status', 'unknown')
                        if status == 'success':
                            logger.info(f"[RETRAIN_PROCESS] Retrain réussi: {request.trigger_reason}")
                        else:
                            logger.warning(f"[RETRAIN_PROCESS] Retrain échoué: {status}")
                    
                    # Attendre avant prochain cycle
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"[RETRAIN_PROCESS] Erreur traitement: {e}")
                    await asyncio.sleep(10)  # Attendre en cas d'erreur
                    
        except Exception as e:
            logger.error(f"[RETRAIN_PROCESS] Erreur boucle: {e}")
    
    async def _cleanup_loop(self):
        """Boucle de nettoyage périodique."""
        try:
            while self.is_running:
                await asyncio.sleep(3600)  # Chaque heure
                
                # Nettoyer les demandes expirées
                self.executor.cleanup_old_requests()
                
                # TODO: Nettoyer les logs anciens
                
        except Exception as e:
            logger.error(f"[CLEANUP] Erreur nettoyage: {e}")
    
    async def _cleanup(self):
        """Nettoie les ressources."""
        try:
            self.is_running = False
            
            if self.pubsub:
                await self.pubsub.unsubscribe('vectorization_events')
                await self.pubsub.close()
            
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("[REDIS_LISTENER] Ressources nettoyées")
            
        except Exception as e:
            logger.error(f"[REDIS_LISTENER] Erreur nettoyage: {e}")
    
    async def stop_listening(self):
        """Arrête l'écoute."""
        self.is_running = False
        logger.info("[REDIS_LISTENER] Arrêt demandé")


# === FONCTIONS UTILITAIRES ===

async def start_retrain_listener():
    """Démarre le listener de retrain."""
    listener = RedisRetrainListener()
    await listener.start_listening()
    return listener


async def test_retrain_listener():
    """Test du listener de retrain."""
    print("=== TEST RETRAIN LISTENER ===")
    
    # Simuler une demande de retrain
    test_request = {
        'type': 'vectorizer_retrain_request',
        'trigger_reason': 'new_genres',
        'priority': 'high',
        'delay_minutes': 1,
        'message': '5 nouveaux genres détectés',
        'details': {'new_genres': ['House', 'Techno', 'Ambient', 'Drum & Bass', 'Breakbeat']},
        'timestamp': datetime.now().isoformat()
    }
    
    # Tester l'exécuteur
    RetrainExecutor()
    retrain_request = RetrainRequest(test_request)
    
    print(f"\nDemande de retrain: {retrain_request.priority}")
    print(f"Message: {retrain_request.message}")
    print(f"Exécutable: {retrain_request.should_execute()}")
    print(f"Score priorité: {retrain_request.get_priority_score()}")
    
    # Test du listener Redis (sans connexion réelle)
    print("\nTest listener configuré pour Redis")
    print(f"URL Redis: {os.getenv('REDIS_URL', 'redis://redis:6379')}")
    
    print("\n=== TEST TERMINÉ ===")


if __name__ == "__main__":
    """Point d'entrée principal."""
    import os
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # Test standalone
    asyncio.run(test_retrain_listener())
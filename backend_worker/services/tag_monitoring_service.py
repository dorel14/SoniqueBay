"""
Service de monitoring des tags pour déclenchement automatique du retrain.

Surveille les changements dans genres, mood_tags, genre_tags et déclenche
des réentraînements si nécessaire.

Architecture optimisée RPi4 :
- Backend Worker : écoute Redis et exécute tâches de retrain
- Déclenchement différé pour éviter surcharge CPU

Auteur : Kilo Code
"""

import asyncio
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Set
import os
import redis.asyncio as redis
import httpx

from backend_worker.utils.logging import logger


class TagChangeDetector:
    """Détecteur de changements dans les tags."""
    
    def __init__(self):
        """Initialise le détecteur."""
        self.library_api_url = os.getenv("API_URL", "http://api:8001")
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.last_check = None
        self.cached_tags = {}
    
    async def get_current_tags(self) -> Dict[str, Set[str]]:
        """
        Récupère les tags actuels depuis library_api.
        
        Returns:
            Dictionnaire des tags par catégorie
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Récupérer genres
                genres_response = await client.get(f"{self.library_api_url}/api/genres/")
                genres = set()
                if genres_response.status_code == 200:
                    genres_data = await genres_response.json()
                    genres = {genre.get('name', '') for genre in genres_data if genre.get('name')}
                
                # Récupérer mood_tags
                moods_response = await client.get(f"{self.library_api_url}/api/tags/?type=mood")
                mood_tags = set()
                if moods_response.status_code == 200:
                    moods_data = await moods_response.json()
                    mood_tags = {tag.get('name', '') for tag in moods_data if tag.get('name')}
                
                # Récupérer genre_tags
                genre_tags_response = await client.get(f"{self.library_api_url}/api/tags/?type=genre")
                genre_tags = set()
                if genre_tags_response.status_code == 200:
                    genre_tags_data = await genre_tags_response.json()
                    genre_tags = {tag.get('name', '') for tag in genre_tags_data if tag.get('name')}
                
                # Récupérer nombre de tracks
                tracks_response = await client.get(f"{self.library_api_url}/api/tracks/count")
                tracks_count = 0
                if tracks_response.status_code == 200:
                    tracks_count = (await tracks_response.json()).get('count', 0)
                
                current_tags = {
                    'genres': genres,
                    'mood_tags': mood_tags,
                    'genre_tags': genre_tags,
                    'tracks_count': tracks_count
                }
                
                logger.info(f"Tags actuels: {len(genres)} genres, {len(mood_tags)} moods, "
                           f"{len(genre_tags)} genre_tags, {tracks_count} tracks")
                
                return current_tags
                
        except Exception as e:
            logger.error(f"Erreur récupération tags: {e}")
            return {'genres': set(), 'mood_tags': set(), 'genre_tags': set(), 'tracks_count': 0}
    
    def calculate_tags_signature(self, tags: Dict[str, Set[str]]) -> str:
        """
        Calcule une signature des tags pour détecter les changements.
        
        Args:
            tags: Dictionnaire des tags
            
        Returns:
            Signature hash des tags
        """
        # Créer une representation stable des tags
        tag_data = {
            'genres': sorted(list(tags['genres'])),
            'mood_tags': sorted(list(tags['mood_tags'])),
            'genre_tags': sorted(list(tags['genre_tags'])),
            'tracks_count': tags['tracks_count']
        }
        
        tag_string = json.dumps(tag_data, sort_keys=True)
        return hashlib.sha256(tag_string.encode()).hexdigest()
    
    async def detect_changes(self) -> Dict[str, Any]:
        """
        Détecte les changements dans les tags.
        
        Returns:
            Détails des changements détectés
        """
        try:
            current_tags = await self.get_current_tags()
            current_signature = self.calculate_tags_signature(current_tags)
            
            if self.last_check is None:
                # Première vérification
                self.last_check = {
                    'tags': current_tags,
                    'signature': current_signature,
                    'timestamp': datetime.now()
                }
                return {
                    'has_changes': True,
                    'reason': 'first_check',
                    'message': 'Première vérification - retrain recommandé',
                    'details': {
                        'new_genres': len(current_tags['genres']),
                        'new_moods': len(current_tags['mood_tags']),
                        'new_genre_tags': len(current_tags['genre_tags']),
                        'tracks_count': current_tags['tracks_count']
                    }
                }
            
            previous_tags = self.last_check['tags']
            
            # Détecter les changements
            changes = {}
            
            # Nouveaux genres
            new_genres = current_tags['genres'] - previous_tags['genres']
            if new_genres:
                changes['new_genres'] = list(new_genres)
            
            # Genres supprimés
            removed_genres = previous_tags['genres'] - current_tags['genres']
            if removed_genres:
                changes['removed_genres'] = list(removed_genres)
            
            # Nouveaux mood_tags
            new_moods = current_tags['mood_tags'] - previous_tags['mood_tags']
            if new_moods:
                changes['new_moods'] = list(new_moods)
            
            # Nouveaux genre_tags
            new_genre_tags = current_tags['genre_tags'] - previous_tags['genre_tags']
            if new_genre_tags:
                changes['new_genre_tags'] = list(new_genre_tags)
            
            # Nouvelles tracks
            new_tracks = current_tags['tracks_count'] - previous_tags['tracks_count']
            if new_tracks > 0:
                changes['new_tracks'] = new_tracks
            
            # Vérifier si signature a changé
            has_changes = bool(changes) or current_signature != self.last_check['signature']
            
            # Mettre à jour le cache
            self.last_check = {
                'tags': current_tags,
                'signature': current_signature,
                'timestamp': datetime.now()
            }
            
            if has_changes:
                message = f"Changements détectés: {len(changes)} types de modifications"

                # Debug: Log des types et valeurs avant utilisation
                logger.debug(f"[DEBUG] changes dict: {changes}")
                if 'new_tracks' in changes:
                    logger.debug(f"[DEBUG] new_tracks type: {type(changes['new_tracks'])}, value: {changes['new_tracks']}")
                    # new_tracks est un entier, pas une liste - ne pas utiliser len()
                    message += f", {changes['new_tracks']} nouvelles tracks"
                if 'new_genres' in changes:
                    logger.debug(f"[DEBUG] new_genres type: {type(changes['new_genres'])}, value: {changes['new_genres']}")
                    # new_genres est une liste - utiliser len() est correct
                    if isinstance(changes['new_genres'], (list, set)):
                        message += f", {len(changes['new_genres'])} nouveaux genres"
                    else:
                        message += f", {changes['new_genres']} nouveaux genres"
                if 'new_moods' in changes:
                    logger.debug(f"[DEBUG] new_moods type: {type(changes['new_moods'])}, value: {changes['new_moods']}")
                    # new_moods est une liste - utiliser len() est correct
                    if isinstance(changes['new_moods'], (list, set)):
                        message += f", {len(changes['new_moods'])} nouveaux moods"
                    else:
                        message += f", {changes['new_moods']} nouveaux moods"

                logger.info(f"[TAG_MONITOR] {message}")
                
                return {
                    'has_changes': True,
                    'reason': 'tags_modified',
                    'message': message,
                    'details': changes
                }
            else:
                return {
                    'has_changes': False,
                    'reason': 'no_changes',
                    'message': 'Aucun changement détecté'
                }
                
        except Exception as e:
            logger.error(f"Erreur détection changements: {e}")
            return {
                'has_changes': True,
                'reason': 'error',
                'message': f'Erreur détection: {str(e)}'
            }
    
    def should_trigger_retrain(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détermine si les changements justifient un retrain.
        
        Args:
            changes: Détails des changements détectés
            
        Returns:
            Décision de retrain avec priorité et délai
        """
        if not changes.get('has_changes', False):
            return {
                'should_retrain': False,
                'priority': 'none',
                'reason': 'no_changes',
                'message': 'Aucun retrain nécessaire'
            }
        
        # Classification de la priorité
        details = changes.get('details', {})
        
        # Priorité critique : nouveaux genres
        if 'new_genres' in details:
            # Handle both list and integer cases
            if isinstance(details['new_genres'], int):
                # First check scenario - already a count
                genre_count = details['new_genres']
            elif isinstance(details['new_genres'], (list, set)):
                # Change detection scenario - need to count
                genre_count = len(details['new_genres'])
            else:
                # Unexpected type - log warning and treat as 0
                logger.warning(f"[TYPE_SAFETY] new_genres type inattendu: {type(details['new_genres'])}")
                genre_count = 0
            
            if genre_count > 0:
                return {
                    'should_retrain': True,
                    'priority': 'high',
                    'reason': 'new_genres',
                    'message': f"{genre_count} nouveaux genres détectés",
                    'delay_minutes': 15,  # Délai court pour nouveaux genres
                    'details': details
                }
        
        # Priorité moyenne : nouvelles tracks importantes
        if 'new_tracks' in details and details['new_tracks'] > 100:
            return {
                'should_retrain': True,
                'priority': 'medium',
                'reason': 'significant_new_tracks',
                'message': f"{details['new_tracks']} nouvelles tracks (≥100)",
                'delay_minutes': 120,  # Délai moyen
                'details': details
            }
        
        # Priorité basse : nouveaux mood_tags
        if 'new_moods' in details or 'new_genre_tags' in details:
            # Vérification de type et conversion sécurisée
            new_moods = details.get('new_moods', [])
            new_genre_tags = details.get('new_genre_tags', [])

            # Gestion sécurisée des types - conversion en liste si nécessaire
            if isinstance(new_moods, int):
                mood_count = new_moods
                logger.warning(f"[TYPE_SAFETY] new_moods est un int: {new_moods}, conversion en count")
            elif isinstance(new_moods, (list, set)):
                mood_count = len(new_moods)
            else:
                mood_count = 0
                logger.warning(f"[TYPE_SAFETY] new_moods type inattendu: {type(new_moods)}")

            if isinstance(new_genre_tags, int):
                genre_tag_count = new_genre_tags
                logger.warning(f"[TYPE_SAFETY] new_genre_tags est un int: {new_genre_tags}, conversion en count")
            elif isinstance(new_genre_tags, (list, set)):
                genre_tag_count = len(new_genre_tags)
            else:
                genre_tag_count = 0
                logger.warning(f"[TYPE_SAFETY] new_genre_tags type inattendu: {type(new_genre_tags)}")

            total_new = mood_count + genre_tag_count

            if total_new > 5:  # Seuil pour éviter retrain pour quelques tags
                return {
                    'should_retrain': True,
                    'priority': 'low',
                    'reason': 'new_tags',
                    'message': f"{total_new} nouveaux tags détectés",
                    'delay_minutes': 480,  # Délai long (8h)
                    'details': details
                }
        
        return {
            'should_retrain': False,
            'priority': 'none',
            'reason': 'insignificant_changes',
            'message': 'Changements insuffisants pour retrain',
            'details': details
        }


class CeleryTaskPublisher:  # Alias pour compatibilité avec tests
    """Publieur pour déclencher les tâches Celery de retrain."""
    
    def __init__(self):
        """Initialise le publieur Celery."""
        from backend_worker.celery_app import celery
        self.celery = celery
    
    async def trigger_retrain_task(self, trigger_info: Dict[str, Any]) -> bool:
        """
        Déclenche une tâche Celery de retrain et publie les notifications SSE.
        
        Args:
            trigger_info: Informations sur le déclencheur
            
        Returns:
            True si déclenchement réussi
        """
        try:
            # Préparer les arguments pour la tâche Celery
            task_args = {
                'trigger_reason': trigger_info['reason'],
                'priority': trigger_info['priority'],
                'message': trigger_info['message'],
                'changes_details': trigger_info['details'],
                'estimated_delay': trigger_info.get('delay_minutes', 0)
            }
            
            # Déclencher la tâche Celery de retrain
            task_result = self.celery.send_task(
                'trigger_vectorizer_retrain',
                args=[task_args],
                queue='vectorization_monitoring',
                priority=self._get_priority_level(trigger_info['priority'])
            )
            
            logger.info(f"[CELERY_TASK] Retrain déclenché: {trigger_info['reason']} (Task ID: {task_result.id})")
            
            # Publier les notifications SSE pour l'UI
            await self._publish_sse_notifications(trigger_info, task_result.id)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur déclenchement retrain: {e}")
            return False
    
    def _get_priority_level(self, priority: str) -> int:
        """Convertit la priorité en niveau Celery."""
        priority_map = {
            'high': 9,
            'medium': 6, 
            'low': 3,
            'none': 1
        }
        return priority_map.get(priority, 5)
    
    async def _publish_sse_notifications(self, trigger_info: Dict[str, Any], task_id: str):
        """Publie les notifications SSE pour l'UI."""
        try:
            async with redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379")) as redis_client:
                # Message pour notifications
                notification_message = {
                    'type': 'vectorization_monitor',
                    'event': 'retrain_requested',
                    'timestamp': datetime.now().isoformat(),
                    'trigger_reason': trigger_info['reason'],
                    'priority': trigger_info['priority'],
                    'message': trigger_info['message'],
                    'details': trigger_info['details'],
                    'task_id': task_id,
                    'worker_info': {
                        'service': 'tag_monitoring_celery',
                        'version': '2.0',
                        'optimized_for': 'RPi4'
                    }
                }
                
                # Message pour progress
                progress_message = {
                    'type': 'vectorization_progress',
                    'stage': 'monitoring_check',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'retrain_triggered',
                    'message': f"Retrain déclenché: {trigger_info['message']}",
                    'priority': trigger_info['priority'],
                    'estimated_delay': trigger_info.get('delay_minutes', 0),
                    'task_id': task_id
                }
                
                # Publier sur les canaux SSE
                await redis_client.publish('notifications', json.dumps(notification_message))
                await redis_client.publish('progress', json.dumps(progress_message))
                
                logger.info(f"[SSE_PUBLISH] Notifications envoyées pour task {task_id}")
                
        except Exception as e:
            logger.error(f"Erreur publication SSE: {e}")
    



class TagMonitoringService:
    """Service principal de monitoring des tags."""
    
    def __init__(self):
        """Initialise le service de monitoring."""
        self.detector = TagChangeDetector()
        self.publisher = CeleryTaskPublisher()
        self.check_interval_minutes = 60  # Vérification toutes les heures
        self.is_running = False
        
        logger.info("TagMonitoringService initialisé")
    
    async def check_and_publish_if_needed(self) -> Dict[str, Any]:
        """
        Vérifie les changements et publie si nécessaire.
        
        Returns:
            Résultat de la vérification
        """
        try:
            logger.info("[TAG_MONITOR] Vérification des changements de tags...")
            
            # Détecter les changements
            changes = await self.detector.detect_changes()
            
            if not changes.get('has_changes', False):
                return {
                    'status': 'no_action',
                    'message': changes.get('message', 'Aucun changement'),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Déterminer si retrain nécessaire
            retrain_decision = self.detector.should_trigger_retrain(changes)
            
            if retrain_decision['should_retrain']:
                logger.info(f"[TAG_MONITOR] Retrain nécessaire: {retrain_decision['message']}")
                
                # Déclencher la tâche Celery de retrain
                celery_success = await self.publisher.trigger_retrain_task(retrain_decision)
                
                return {
                    'status': 'retrain_requested',
                    'message': retrain_decision['message'],
                    'priority': retrain_decision['priority'],
                    'delay_minutes': retrain_decision['delay_minutes'],
                    'celery_triggered': celery_success,
                    'timestamp': datetime.now().isoformat(),
                    'details': retrain_decision['details']
                }
            else:
                logger.info(f"[TAG_MONITOR] Retrain non nécessaire: {retrain_decision['message']}")
                return {
                    'status': 'retrain_not_needed',
                    'message': retrain_decision['message'],
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Erreur monitoring tags: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def start_monitoring(self):
        """Démarre le monitoring continu."""
        self.is_running = True
        logger.info("[TAG_MONITOR] Démarrage du monitoring des tags")
        
        try:
            while self.is_running:
                try:
                    await self.check_and_publish_if_needed()
                    
                    # Attendre avant prochaine vérification
                    await asyncio.sleep(self.check_interval_minutes * 60)
                    
                except Exception as e:
                    logger.error(f"Erreur cycle monitoring: {e}")
                    await asyncio.sleep(300)  # Attendre 5 minutes en cas d'erreur
                    
        except asyncio.CancelledError:
            logger.info("[TAG_MONITOR] Monitoring arrêté")
        finally:
            self.is_running = False
    
    async def stop_monitoring(self):
        """Arrête le monitoring."""
        self.is_running = False
        logger.info("[TAG_MONITOR] Arrêt du monitoring demandé")
    
    async def manual_check(self) -> Dict[str, Any]:
        """
        Effectue une vérification manuelle immédiate.
        
        Returns:
            Résultat de la vérification manuelle
        """
        logger.info("[TAG_MONITOR] Vérification manuelle demandée")
        return await self.check_and_publish_if_needed()


# === FONCTIONS UTILITAIRES ===

async def start_tag_monitoring():
    """Démarre le service de monitoring."""
    service = TagMonitoringService()
    await service.start_monitoring()
    return service


async def check_tags_once():
    """Effectue une vérification unique des tags."""
    service = TagMonitoringService()
    result = await service.check_and_publish_if_needed()
    await service.stop_monitoring()
    return result


if __name__ == "__main__":
    """Test du service de monitoring."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def test_monitoring():
        """Test du monitoring des tags."""
        print("=== TEST MONITORING TAGS ===")
        
        # Test vérification unique
        print("\n1. Test vérification unique...")
        result = await check_tags_once()
        print(f"Résultat: {result['status']}")
        print(f"Message: {result['message']}")
        
        # Test service complet
        print("\n2. Test service monitoring (30 secondes)...")
        service = TagMonitoringService()
        service.check_interval_minutes = 0.5  # 30 secondes pour test
        
        # Démarrer monitoring en arrière-plan
        monitoring_task = asyncio.create_task(service.start_monitoring())
        
        try:
            # Attendre 35 secondes
            await asyncio.sleep(35)
        except KeyboardInterrupt:
            pass
        finally:
            await service.stop_monitoring()
            monitoring_task.cancel()
        
        print("\n=== TEST TERMINÉ ===")
    
    # Exécuter les tests
    asyncio.run(test_monitoring())
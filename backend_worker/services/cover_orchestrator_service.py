"""
Service d'orchestration des covers.
Coordonne le traitement des images en utilisant les services spécialisés.
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from backend_worker.utils.logging import logger
from backend_worker.services.redis_cache import image_cache_service  # ✅ CORRIGÉ: Import du cache unifié
from backend_worker.services.image_processing_service import image_processing_service
from backend_worker.services.image_priority_service import ImagePriorityService, ProcessingContext, ImageSource
from backend_worker.services.cover_types import CoverProcessingContext, ImageType, TaskType
from backend_worker.services.entity_manager import create_or_update_cover


class CoverOrchestratorService:
    """
    Service d'orchestration pour le traitement intelligent des images.
    
    Coordonne :
    - Le cache d'images (ImageCacheService)
    - Le traitement d'images (ImageProcessingService) 
    - La gestion des priorités (ImagePriorityService)
    - Les retries et fallbacks
    - La validation et les métriques
    """
    
    def __init__(self):
        self.cache_service = image_cache_service
        self.processing_service = image_processing_service
        self.priority_service = ImagePriorityService()
        
        # Configuration des retries
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 1.0,  # secondes
            "backoff_multiplier": 2.0
        }
        
        # Configuration des timeouts
        self.timeout_config = {
            "cache_lookup": 2.0,
            "image_processing": 10.0,
            "external_api": 15.0
        }
        
        logger.info("[COVER_ORCHESTRATOR] Service initialisé")
    
    async def process_image(self, context: CoverProcessingContext) -> Dict[str, Any]:
        """
        Traite une image selon son contexte et les priorités.
        
        Args:
            context: Contexte de traitement de l'image
            
        Returns:
            Résultat du traitement
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[COVER_ORCHESTRATOR] Début traitement image: {context.image_type.value}")
            
            # 1. Vérification du cache avec timeout
            cached_result = await asyncio.wait_for(
                self.cache_service.get_cached_result(context.cache_key),
                timeout=self.timeout_config["cache_lookup"]
            )
            
            if cached_result:
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"[COVER_ORCHESTRATOR] Cache hit pour {context.cache_key}")
                
                return {
                    "status": "cached",
                    "data": cached_result,
                    "processing_time": processing_time,
                    "source": "cache"
                }
            
            # 2. Évaluation des priorités
            priority_context = self._convert_to_priority_context(context)
            should_process = await self.priority_service.should_process(priority_context)
            
            if not should_process:
                logger.info(f"[COVER_ORCHESTRATOR] Traitement ignoré par priorité: {context.cache_key}")
                return {
                    "status": "skipped",
                    "reason": "priority_filter",
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # 3. Traitement avec retry
            result = await self._process_with_retry(context)
            
            # 4. Enregistrement dans la base de données si succès
            if result.get("status") == "success":
                logger.info(f"[COVER_ORCHESTRATOR] Enregistrement de la cover dans la DB pour {context.image_type.value} {context.entity_id}")
                await self._save_to_database(context, result)
                
                # Mise en cache du résultat
                await self.cache_service.cache_result(
                    context.cache_key, 
                    result["data"]
                )
                logger.debug(f"[COVER_ORCHESTRATOR] Résultat mis en cache: {context.cache_key}")
            
            # 5. Enrichissement du résultat
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.update({
                "processing_time": processing_time,
                "cache_key": context.cache_key,
                "image_type": context.image_type.value,
                "entity_id": context.entity_id
            })
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"[COVER_ORCHESTRATOR] Timeout traitement image: {context.cache_key}")
            return {
                "status": "timeout",
                "error": "Traitement timeout",
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur traitement image: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def process_batch(self, contexts: List[CoverProcessingContext]) -> Dict[str, Any]:
        """
        Traite un batch d'images de manière optimisée.
        
        Args:
            contexts: Liste des contextes de traitement
            
        Returns:
            Résultats agrégés
        """
        try:
            logger.info(f"[COVER_ORCHESTRATOR] Début traitement batch: {len(contexts)} images")
            
            # Groupement par type d'image pour optimisation
            grouped_contexts = self._group_by_image_type(contexts)
            
            results = {
                "total": len(contexts),
                "successful": 0,
                "failed": 0,
                "cached": 0,
                "skipped": 0,
                "timeout": 0,
                "processing_details": []
            }
            
            # Traitement par groupes avec concurrence limitée
            semaphore = asyncio.Semaphore(5)  # Maximum 5 images simultanément
            
            for image_type, type_contexts in grouped_contexts.items():
                logger.debug(f"[COVER_ORCHESTRATOR] Traitement groupe {image_type}: {len(type_contexts)} images")
                
                tasks = [
                    self._process_with_semaphore(semaphore, context) 
                    for context in type_contexts
                ]
                
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Agrégation des résultats
                for i, result in enumerate(group_results):
                    context = type_contexts[i]
                    
                    if isinstance(result, Exception):
                        logger.error(f"[COVER_ORCHESTRATOR] Erreur batch contexte {i}: {result}")
                        results["failed"] += 1
                        results["processing_details"].append({
                            "context": context.cache_key,
                            "status": "exception",
                            "error": str(result)
                        })
                    else:
                        status = result.get("status", "unknown")
                        results[status] = results.get(status, 0) + 1
                        results["processing_details"].append({
                            "context": context.cache_key,
                            "status": status,
                            "processing_time": result.get("processing_time", 0)
                        })
            
            # Mise à jour des statistiques de priorité
            await self._update_batch_statistics(results)
            
            logger.info(f"[COVER_ORCHESTRATOR] Batch terminé: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur traitement batch: {str(e)}")
            return {"error": str(e), "total": len(contexts)}
    
    async def refresh_image(
        self, 
        cache_key: str, 
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Force le rafraîchissement d'une image en cache.
        
        Args:
            cache_key: Clé de cache de l'image
            force_refresh: Force le rafraîchissement même si en cache
            
        Returns:
            Résultat du rafraîchissement
        """
        try:
            logger.info(f"[COVER_ORCHESTRATOR] Rafraîchissement image: {cache_key}")
            
            # Invalidation du cache
            if force_refresh:
                await self.cache_service.invalidate_cache(cache_key)
                logger.debug(f"[COVER_ORCHESTRATOR] Cache invalidé: {cache_key}")
            
            # Re-traitement (le cache sera automatiquement mis à jour)
            # Note: Cette méthode nécessiterait de reconstruire le contexte
            # Pour l'instant, on retourne un message informatif
            
            return {
                "status": "refresh_initiated",
                "cache_key": cache_key,
                "force_refresh": force_refresh,
                "message": "Rafraîchissement initié - l'image sera re-traitée à la prochaine demande"
            }
            
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur rafraîchissement: {str(e)}")
            return {"error": str(e)}
    
    async def get_processing_status(self, cache_keys: List[str]) -> Dict[str, Any]:
        """
        Vérifie le statut de traitement pour plusieurs images.
        
        Args:
            cache_keys: Liste des clés de cache
            
        Returns:
            Statut de chaque image
        """
        try:
            status_report = {
                "total_checked": len(cache_keys),
                "cached": 0,
                "processing": 0,
                "failed": 0,
                "not_found": 0,
                "details": {}
            }
            
            for cache_key in cache_keys:
                # Vérification cache
                cached_result = await self.cache_service.get_cached_result(cache_key)
                
                if cached_result:
                    status_report["cached"] += 1
                    status_report["details"][cache_key] = {
                        "status": "cached",
                        "available": True
                    }
                else:
                    status_report["not_found"] += 1
                    status_report["details"][cache_key] = {
                        "status": "not_cached",
                        "available": False
                    }
            
            return status_report
            
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur vérification statut: {str(e)}")
            return {"error": str(e)}
    
    async def _process_with_retry(self, context: CoverProcessingContext) -> Dict[str, Any]:
        """Traite une image avec système de retry."""
        last_exception = None
        
        for attempt in range(self.retry_config["max_retries"] + 1):
            try:
                if attempt > 0:
                    delay = self.retry_config["retry_delay"] * (
                        self.retry_config["backoff_multiplier"] ** (attempt - 1)
                    )
                    logger.info(f"[COVER_ORCHESTRATOR] Retry {attempt}/{self.retry_config['max_retries']} après {delay}s")
                    await asyncio.sleep(delay)
                
                # Traitement principal avec timeout
                result = await asyncio.wait_for(
                    self._process_single_image(context),
                    timeout=self.timeout_config["image_processing"]
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"[COVER_ORCHESTRATOR] Tentative {attempt + 1} échouée: {str(e)}")
                
                if attempt == self.retry_config["max_retries"]:
                    logger.error("[COVER_ORCHESTRATOR] Toutes les tentatives ont échoué")
                    break
        
        # Si on arrive ici, toutes les tentatives ont échoué
        return {
            "status": "failed",
            "error": str(last_exception),
            "attempts": self.retry_config["max_retries"] + 1
        }
    
    async def _process_single_image(self, context: CoverProcessingContext) -> Dict[str, Any]:
        """Traite une image unique."""
        try:
            # Extraction des paramètres de recherche
            search_params = self._extract_search_parameters(context)
            
            # Recherche et traitement via le service de traitement
            result = await self.processing_service.find_and_process_image(
                image_type=context.image_type.value,
                entity_id=context.entity_id,
                entity_path=context.entity_path,
                **search_params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur traitement unique: {str(e)}")
            return {"error": str(e)}
    
    async def _process_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore, 
        context: CoverProcessingContext
    ) -> Dict[str, Any]:
        """Traite une image avec limitation de concurrence."""
        async with semaphore:
            return await self.process_image(context)
    
    def _convert_to_priority_context(self, cover_context: CoverProcessingContext) -> ProcessingContext:
        """Convertit un contexte CoverProcessingContext en ProcessingContext."""
        return ProcessingContext(
            image_type=cover_context.image_type.value,
            entity_id=cover_context.entity_id,
            entity_path=cover_context.entity_path,
            source=ImageSource.LOCAL,  # Correction: utiliser l'enum au lieu de la chaîne
            is_new=True,  # Par défaut, à adapter selon les besoins
            access_count=0,
            metadata=cover_context.metadata
        )
    
    def _group_by_image_type(self, contexts: List[CoverProcessingContext]) -> Dict[str, List[CoverProcessingContext]]:
        """Groupe les contextes par type d'image."""
        grouped = {}
        for context in contexts:
            image_type = context.image_type.value
            if image_type not in grouped:
                grouped[image_type] = []
            grouped[image_type].append(context)
        return grouped
    
    def _extract_search_parameters(self, context: CoverProcessingContext) -> Dict[str, Any]:
        """Extrait les paramètres de recherche depuis le contexte."""
        params = {}
        
        # Extraction depuis les métadonnées
        metadata = context.metadata or {}
        
        if "mb_release_id" in metadata:
            params["mb_release_id"] = metadata["mb_release_id"]
        if "artist_name" in metadata:
            params["artist_name"] = metadata["artist_name"]
        if "album_title" in metadata:
            params["album_title"] = metadata["album_title"]
        
        return params
    
    async def _update_batch_statistics(self, results: Dict[str, Any]):
        """Met à jour les statistiques après un batch."""
        try:
            total_time = sum(
                detail.get("processing_time", 0) 
                for detail in results.get("processing_details", [])
            )
            
            if results["total"] > 0:
                avg_time = total_time / results["total"]
                success_rate = results["successful"] / results["total"]
                
                logger.info(f"[COVER_ORCHESTRATOR] Stats batch - "
                          f"Succès: {success_rate:.2%}, "
                          f"Temps moyen: {avg_time:.2f}s")
                
        except Exception as e:
            logger.warning(f"[COVER_ORCHESTRATOR] Erreur mise à jour stats: {e}")
    
    async def _save_to_database(self, context: CoverProcessingContext, result: Dict[str, Any]):
        """
        Sauvegarde le résultat du traitement dans la base de données.
        
        Args:
            context: Contexte de traitement de l'image
            result: Résultat du traitement
        """
        try:
            logger.info(f"[COVER_ORCHESTRATOR] Début sauvegarde DB - Context: {context.image_type.value} ID: {context.entity_id}")
            logger.info(f"[COVER_ORCHESTRATOR] Résultat traitement: {result.get('status')}")
            
            if not context.entity_id:
                logger.warning(f"[COVER_ORCHESTRATOR] Impossible de sauvegarder - pas d'entity_id: {context.cache_key}")
                return
                
            # Convertir le type d'image pour la base de données
            entity_type = self._convert_image_type_to_entity_type(context.image_type)
            
            logger.info(f"[COVER_ORCHESTRATOR] Sauvegarde dans la DB: {entity_type} {context.entity_id}")
            logger.info(f"[COVER_ORCHESTRATOR] Cover data présent: {result.get('data') is not None}")
            logger.info(f"[COVER_ORCHESTRATOR] Mime type: {result.get('mime_type')}")
            
            # Créer un client HTTP asynchrone
            import os
            api_url = os.getenv("API_URL", "http://localhost:8001")
            logger.info(f"[COVER_ORCHESTRATOR] API URL pour sauvegarde: {api_url}")
            
            async with httpx.AsyncClient() as client:
                await create_or_update_cover(
                    client=client,
                    entity_type=entity_type,
                    entity_id=context.entity_id,
                    cover_data=result.get("data"),
                    mime_type=result.get("mime_type"),
                    url=context.entity_path
                )
                
            logger.info(f"[COVER_ORCHESTRATOR] Sauvegarde DB réussie pour {entity_type} {context.entity_id}")
                
        except Exception as e:
            logger.error(f"[COVER_ORCHESTRATOR] Erreur sauvegarde DB: {str(e)}")
            import traceback
            logger.error(f"[COVER_ORCHESTRATOR] Traceback: {traceback.format_exc()}")
    
    def _convert_image_type_to_entity_type(self, image_type: ImageType) -> str:
        """
        Convertit ImageType en type d'entité pour la base de données.
        
        Args:
            image_type: Type d'image
            
        Returns:
            Type d'entité pour la base de données
        """
        type_mapping = {
            ImageType.ALBUM_COVER: "album",
            ImageType.ARTIST_IMAGE: "artist",
            ImageType.TRACK_EMBEDDED: "track",
            ImageType.LOCAL_COVER: "album",  # Par défaut pour les covers locales
            ImageType.FANART: "artist"       # Fanart est généralement associé à un artiste
        }
        
        return type_mapping.get(image_type, "album")  # Valeur par défaut


# Instance globale du service
cover_orchestrator_service = CoverOrchestratorService()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def initialize_cover_orchestrator():
    """Initialise le service d'orchestration."""
    return cover_orchestrator_service


def create_orchestrator_context(
    image_type: str,
    entity_id: Optional[int] = None,
    entity_path: Optional[str] = None,
    task_type: str = "normal",
    metadata: Optional[Dict[str, Any]] = None
) -> CoverProcessingContext:
    """
    Factory function pour créer un contexte d'orchestration.
    
    Args:
        image_type: Type d'image
        entity_id: ID de l'entité
        entity_path: Chemin du fichier
        task_type: Type de tâche
        metadata: Métadonnées additionnelles
        
    Returns:
        Contexte de traitement
    """
    return CoverProcessingContext(
        image_type=ImageType(image_type),
        entity_id=entity_id,
        entity_path=entity_path,
        task_type=TaskType(task_type),
        metadata=metadata or {}
    )
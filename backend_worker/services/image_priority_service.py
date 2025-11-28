"""
Service de Gestion des Priorités d'Images
Implémente un système intelligent de priorisation des tâches de traitement d'images.
"""

import json
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import redis.asyncio as redis
from backend_worker.utils.logging import logger


class PriorityLevel(Enum):
    """Niveaux de priorité pour le traitement des images."""
    CRITICAL = "critical"      # Images en cours de lecture/affichage
    HIGH = "high"              # Images récemment ajoutées
    NORMAL = "normal"          # Images standards
    LOW = "low"                # Images en arrière-plan
    DEFERRED = "deferred"      # Images différées


class ImageSource(Enum):
    """Sources d'images pour la priorisation."""
    EMBEDDED = "embedded"      # Intégrées aux fichiers audio
    LOCAL = "local"            # Fichiers locaux (cover.jpg, etc.)
    LASTFM = "lastfm"          # API Last.fm
    COVERART = "coverart"      # Cover Art Archive
    MANUAL = "manual"          # Ajout manuel utilisateur


class ProcessingContext:
    """Contexte de traitement pour l'évaluation des priorités."""
    
    def __init__(
        self,
        image_type: str,
        entity_id: Optional[int] = None,
        entity_path: Optional[str] = None,
        source: Optional[ImageSource] = None,
        is_new: bool = False,
        access_count: int = 0,
        last_accessed: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.image_type = image_type
        self.entity_id = entity_id
        self.entity_path = entity_path
        self.source = source or ImageSource.LOCAL
        self.is_new = is_new
        self.access_count = access_count
        self.last_accessed = last_accessed or datetime.now(timezone.utc)
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)


class ImagePriorityService:
    """
    Service intelligent de gestion des priorités d'images.
    
    Fonctionnalités :
    - Évaluation dynamique des priorités basée sur le contexte
    - Système de scoring avec pondération
    - Cache Redis pour la performance
    - Support de la déduplication intelligente
    - Gestion des quotas et rate limiting
    """
    
    def __init__(self):
        self.redis_client = None
        self.priority_weights = {
            # Poids pour l'évaluation des priorités
            "is_new": 10.0,           # Nouvelles images = très prioritaire
            "access_frequency": 5.0,  # Fréquence d'accès
            "source_priority": {
                ImageSource.EMBEDDED.value: 8.0,   # Source la plus fiable
                ImageSource.LOCAL.value: 7.0,      # Local = bon
                ImageSource.COVERART.value: 6.0,   # Cover Art Archive = moyen
                ImageSource.LASTFM.value: 4.0,     # Last.fm = variable
                ImageSource.MANUAL.value: 9.0      # Manuel = prioritaire
            },
            "image_type_priority": {
                "album_cover": 8.0,    # Covers d'albums prioritaires
                "artist_image": 6.0,   # Images d'artistes normales
                "track_embedded": 7.0, # Images intégrées prioritaires
                "fanart": 3.0          # Fanart = moins prioritaire
            },
            "time_decay": 0.1         # Décroissance temporelle
        }
        
        # Configuration Redis
        self.redis_config = {
            "priority_cache_ttl": 3600,  # 1 heure
            "processing_queue_ttl": 1800,  # 30 minutes
            "max_queue_size": 1000
        }
    
    async def initialize(self):
        """Initialise la connexion Redis."""
        try:
            self.redis_client = redis.from_url("redis://redis:6379")
            await self.redis_client.ping()
            logger.info("[PRIORITY_SERVICE] Connexion Redis établie")
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur connexion Redis: {e}")
            raise
    
    async def evaluate_priority(self, context: ProcessingContext) -> Tuple[PriorityLevel, float]:
        """
        Évalue la priorité d'une image selon son contexte.
        
        Args:
            context: Contexte de traitement de l'image
        
        Returns:
            Tuple (PriorityLevel, score) avec le niveau de priorité et le score
        """
        try:
            # Calcul du score de base
            score = 0.0
            
            # Bonus pour les nouvelles images
            if context.is_new:
                score += self.priority_weights["is_new"]
            
            # Bonus pour la fréquence d'accès
            score += min(context.access_count * 0.5, 5.0)
            
            # Bonus selon la source (LASTFM = très peu fiable)
            if context.source == ImageSource.LASTFM:
                source_weight = 1.0  # Très peu fiable
            else:
                source_weight = self.priority_weights["source_priority"].get(
                    context.source.value, 2.0
                )
            score += source_weight
            
            # Bonus selon le type d'image
            type_weight = self.priority_weights["image_type_priority"].get(
                context.image_type, 3.0
            )
            score += type_weight
            
            # Pénalité pour les images anciennes
            age_days = (datetime.now(timezone.utc) - context.created_at).days
            if age_days > 0:
                decay_factor = max(0.1, 1.0 - (age_days * self.priority_weights["time_decay"]))
                score *= decay_factor
            
            # Pénalité pour les images non accédées récemment
            days_since_access = (datetime.now(timezone.utc) - context.last_accessed).days
            if days_since_access > 30:
                score *= 0.5
            
            # Bonus pour les images avec métadonnées complètes
            metadata_completeness = self._calculate_metadata_completeness(context.metadata)
            score *= (1.0 + metadata_completeness * 0.2)
            
            # Score minimum pour éviter les trop bas scores
            score = max(score, 1.0)
            
            # Classification en niveau de priorité
            priority_level = self._score_to_priority_level(score)
            
            logger.debug(f"[PRIORITY_SERVICE] Image {context.image_type} (ID: {context.entity_id}) - "
                        f"Score: {score:.2f}, Priority: {priority_level.value}")
            
            return priority_level, score
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur évaluation priorité: {str(e)}")
            return PriorityLevel.NORMAL, 5.0  # Valeur par défaut
    
    async def prioritize_batch(self, image_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Trie un batch d'images par ordre de priorité.
        
        Args:
            image_batch: Liste des données d'images à prioriser
        
        Returns:
            Liste triée par ordre de priorité décroissante
        """
        try:
            # Évaluation de la priorité pour chaque image
            prioritized_images = []
            
            for image_data in image_batch:
                try:
                    # Validation des données d'entrée
                    if not isinstance(image_data, dict):
                        logger.warning(f"[PRIORITY_SERVICE] Données invalides dans batch: {type(image_data)}")
                        continue
                    
                    image_type = image_data.get("image_type")
                    if not image_type or not isinstance(image_type, str):
                        logger.warning(f"[PRIORITY_SERVICE] Type d'image invalide: {image_type}")
                        continue
                    
                    source_str = image_data.get("source", "local")
                    try:
                        source = ImageSource(source_str)
                    except ValueError:
                        logger.warning(f"[PRIORITY_SERVICE] Source invalide: {source_str}, utilisation de 'local'")
                        source = ImageSource.LOCAL
                    
                    access_count = image_data.get("access_count", 0)
                    if not isinstance(access_count, int) or access_count < 0:
                        access_count = 0
                    
                    context = ProcessingContext(
                        image_type=image_type,
                        entity_id=image_data.get("entity_id"),
                        entity_path=image_data.get("entity_path"),
                        source=source,
                        is_new=image_data.get("is_new", False),
                        access_count=access_count,
                        metadata=image_data.get("metadata", {})
                    )
                    
                    priority_level, score = await self.evaluate_priority(context)
                    
                    # Ajout du score et niveau aux données
                    prioritized_data = image_data.copy()
                    prioritized_data["priority_level"] = priority_level.value
                    prioritized_data["priority_score"] = float(score)  # Conversion explicite
                    
                    prioritized_images.append(prioritized_data)
                
                except Exception as e:
                    logger.error(f"[PRIORITY_SERVICE] Erreur traitement image: {str(e)}")
                    continue
            
            # Tri par score décroissant
            prioritized_images.sort(key=lambda x: x["priority_score"], reverse=True)
            
            logger.info(f"[PRIORITY_SERVICE] Batch priorisé: {len(prioritized_images)} images")
            return prioritized_images
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur priorisation batch: {str(e)}")
            return image_batch  # Retourner le batch original en cas d'erreur
    
    async def should_process(self, context: ProcessingContext) -> bool:
        """
        Détermine si une image doit être traitée selon sa priorité et les quotas.
        
        Args:
            context: Contexte de traitement
        
        Returns:
            True si l'image doit être traitée, False sinon
        """
        try:
            priority_level, score = await self.evaluate_priority(context)
            
            # Vérification des quotas par niveau de priorité
            quota_ok = await self._check_priority_quotas(priority_level)
            if not quota_ok:
                logger.debug(f"[PRIORITY_SERVICE] Quota atteint pour niveau {priority_level.value}")
                return False
            
            # Vérification de la queue de traitement
            queue_ok = await self._check_processing_queue(context)
            if not queue_ok:
                logger.debug("[PRIORITY_SERVICE] Queue de traitement pleine")
                return False
            
            # Seuil minimum pour éviter le traitement des images très basses priorités
            min_score_threshold = 2.0
            if score < min_score_threshold:
                logger.debug(f"[PRIORITY_SERVICE] Score trop faible: {score:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur vérification traitement: {str(e)}")
            return True  # Par défaut, traiter
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de traitement par niveau de priorité.
        
        Returns:
            Statistiques de performance
        """
        try:
            if not self.redis_client:
                return {"error": "Redis non initialisé"}
            
            stats = {}
            
            # Statistiques par niveau de priorité
            for priority in PriorityLevel:
                key = f"cover_priority:{priority.value}:stats"
                data = await self.redis_client.get(key)
                if data:
                    try:
                        # Les données peuvent être déjà décodées ou en bytes
                        if isinstance(data, bytes):
                            stats_data = json.loads(data.decode('utf-8'))
                        else:
                            stats_data = json.loads(data)
                        stats[priority.value] = stats_data
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"[PRIORITY_SERVICE] Erreur parsing JSON {priority.value}: {e}")
                        stats[priority.value] = {"processed": 0, "success_rate": 0.0}
                else:
                    stats[priority.value] = {"processed": 0, "success_rate": 0.0}
            
            # Statistiques globales
            total_key = "cover_priority:total:stats"
            total_data = await self.redis_client.get(total_key)
            if total_data:
                try:
                    if isinstance(total_data, bytes):
                        stats["total"] = json.loads(total_data.decode('utf-8'))
                    else:
                        stats["total"] = json.loads(total_data)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"[PRIORITY_SERVICE] Erreur parsing JSON total: {e}")
                    stats["total"] = {"processed": 0, "success_rate": 0.0}
            else:
                stats["total"] = {"processed": 0, "success_rate": 0.0}
            
            return stats
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur récupération stats: {str(e)}")
            return {"error": str(e)}
    
    async def update_processing_stats(
        self,
        priority_level: PriorityLevel,
        success: bool,
        processing_time: float
    ):
        """Met à jour les statistiques de traitement."""
        try:
            if not self.redis_client:
                return
            
            key = f"cover_priority:{priority_level.value}:stats"
            
            # Récupération des stats actuelles
            current_data = await self.redis_client.get(key)
            if current_data:
                stats = json.loads(current_data)
            else:
                stats = {"processed": 0, "success": 0, "total_time": 0.0}
            
            # Mise à jour
            stats["processed"] += 1
            if success:
                stats["success"] += 1
            stats["total_time"] += processing_time
            
            # Calculs sécurisés contre la division par zéro
            if stats["processed"] > 0:
                stats["success_rate"] = stats["success"] / stats["processed"]
                stats["average_time"] = stats["total_time"] / stats["processed"]
            else:
                stats["success_rate"] = 0.0
                stats["average_time"] = 0.0
            
            # Sauvegarde avec TTL
            try:
                await self.redis_client.setex(
                    key,
                    self.redis_config["priority_cache_ttl"],
                    json.dumps(stats)
                )
            except (TypeError, ValueError) as e:
                logger.error(f"[PRIORITY_SERVICE] Erreur sérialisation JSON stats: {e}")
                # Fallback avec stats basiques
                basic_stats = {"processed": stats.get("processed", 0), "success": stats.get("success", 0)}
                await self.redis_client.setex(
                    key,
                    self.redis_config["priority_cache_ttl"],
                    json.dumps(basic_stats)
                )
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur mise à jour stats: {str(e)}")
    
    def _calculate_metadata_completeness(self, metadata: Dict[str, Any]) -> float:
        """Calcule le pourcentage de complétude des métadonnées."""
        if not metadata:
            return 0.0
        
        required_fields = [
            "title", "artist", "album", "year", "genre"
        ]
        
        present_fields = sum(1 for field in required_fields if field in metadata and metadata[field])
        return present_fields / len(required_fields)
    
    def _score_to_priority_level(self, score: float) -> PriorityLevel:
        """Convertit un score en niveau de priorité."""
        if score >= 15.0:
            return PriorityLevel.CRITICAL
        elif score >= 10.0:
            return PriorityLevel.HIGH
        elif score >= 5.0:
            return PriorityLevel.NORMAL
        elif score >= 2.0:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.DEFERRED
    
    async def _check_priority_quotas(self, priority_level: PriorityLevel) -> bool:
        """Vérifie si les quotas pour un niveau de priorité sont respectés."""
        try:
            if not self.redis_client:
                return True  # Pas de vérification sans Redis
            
            # Quotas par niveau de priorité (images par heure)
            quotas = {
                PriorityLevel.CRITICAL: 100,
                PriorityLevel.HIGH: 50,
                PriorityLevel.NORMAL: 20,
                PriorityLevel.LOW: 10,
                PriorityLevel.DEFERRED: 5
            }
            
            quota = quotas.get(priority_level, 10)
            key = f"cover_quota:{priority_level.value}"
            
            # Récupération du compteur actuel
            current_count = await self.redis_client.get(key)
            try:
                current_count = int(current_count) if current_count else 0
            except (ValueError, TypeError):
                logger.warning(f"[PRIORITY_SERVICE] Valeur Redis invalide pour {key}: {current_count}")
                current_count = 0
            
            # Vérification du quota
            if current_count >= quota:
                return False
            
            # Incrémentation du compteur
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 3600)  # Reset après 1 heure
            await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur vérification quota: {str(e)}")
            return True  # Par défaut, autoriser
    
    async def _check_processing_queue(self, context: ProcessingContext) -> bool:
        """Vérifie si la queue de traitement n'est pas pleine."""
        try:
            if not self.redis_client:
                return True
            
            queue_key = "cover_processing_queue"
            queue_size = await self.redis_client.llen(queue_key)
            
            max_size = self.redis_config["max_queue_size"]
            return queue_size < max_size
            
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur vérification queue: {str(e)}")
            return True  # Par défaut, autoriser
    
    async def cleanup(self):
        """Nettoie les ressources du service."""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("[PRIORITY_SERVICE] Nettoyage terminé")
        except Exception as e:
            logger.error(f"[PRIORITY_SERVICE] Erreur nettoyage: {str(e)}")


# Instance globale du service
priority_service = ImagePriorityService()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def initialize_priority_service():
    """Initialise le service de priorités."""
    await priority_service.initialize()
    return priority_service


def create_processing_context(
    image_type: str,
    entity_id: Optional[int] = None,
    entity_path: Optional[str] = None,
    source: str = "local",
    is_new: bool = False,
    access_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> ProcessingContext:
    """
    Factory function pour créer un contexte de traitement.
    
    Args:
        image_type: Type d'image
        entity_id: ID de l'entité
        entity_path: Chemin du fichier
        source: Source de l'image
        is_new: Si l'image est nouvelle
        access_count: Nombre d'accès
        metadata: Métadonnées
    
    Returns:
        Contexte de traitement
    """
    return ProcessingContext(
        image_type=image_type,
        entity_id=entity_id,
        entity_path=entity_path,
        source=ImageSource(source),
        is_new=is_new,
        access_count=access_count,
        metadata=metadata
    )
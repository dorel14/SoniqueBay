"""
Service de recherche vectorielle V2 pour Supabase.
Utilise pgvector via Supabase pour les recherches de similarité.
"""

from typing import List, Dict, Any, Optional, Tuple
from backend.api.utils.logging import logger
from backend.api.utils.db_config import is_migrated, USE_SUPABASE
from backend.api.utils.db_adapter import get_adapter


class VectorSearchServiceV2:
    """
    Service de recherche vectorielle utilisant Supabase pgvector.
    
    Architecture:
    - Mode Supabase: Requêtes directes via DatabaseAdapter avec pgvector
    - Fallback: VectorSearchService legacy (SQLAlchemy)
    """
    
    def __init__(self):
        self.use_supabase = USE_SUPABASE and is_migrated("track_embeddings")
        self._legacy_service = None
        self._embeddings_adapter = None
        
        if not self.use_supabase:
            logger.info("VectorSearchServiceV2 initialisé avec SQLAlchemy (fallback)")
        else:
            logger.info("VectorSearchServiceV2 initialisé avec Supabase")
    
    @property
    def embeddings_adapter(self):
        """Lazy loading de l'adapter track_embeddings."""
        if self._embeddings_adapter is None and self.use_supabase:
            self._embeddings_adapter = get_adapter("track_embeddings")
        return self._embeddings_adapter
    
    def _get_legacy_service(self, db_session=None):
        """Get or create legacy service."""
        if self._legacy_service is None and db_session is not None:
            from backend.api.services.vector_search_service import VectorSearchService
            self._legacy_service = VectorSearchService(db_session)
        return self._legacy_service
    
    async def find_similar_tracks(
        self,
        query_embedding: List[float],
        limit: int = 10,
        embedding_type: str = "semantic",
        min_similarity: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche de tracks similaires par vecteur.
        
        Args:
            query_embedding: Vecteur de requête
            limit: Nombre max de résultats
            embedding_type: Type d'embedding (semantic, audio, text)
            min_similarity: Similarité minimale (optionnel)
            
        Returns:
            Liste des tracks similaires avec métadonnées
        """
        if self.use_supabase:
            return await self._find_similar_tracks_supabase(
                query_embedding, limit, embedding_type, min_similarity
            )
        else:
            raise RuntimeError("VectorSearchServiceV2 requires Supabase mode or db_session for fallback")
    
    async def _find_similar_tracks_supabase(
        self,
        query_embedding: List[float],
        limit: int,
        embedding_type: str,
        min_similarity: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Recherche vectorielle via Supabase pgvector."""
        try:
            # Convertir l'embedding en format string pour pgvector
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            # Requête avec opérateur pgvector <-> (distance L2)
            # ou <=> (cosine similarity) selon le besoin
            filters = {
                "embedding_type": embedding_type,
                "vector": {"isnot": None}  # Vecteur non null
            }
            
            # Récupérer tous les embeddings avec leur vecteur
            # Note: La recherche vectorielle exacte nécessite une RPC Supabase
            # ou une requête SQL directe avec pgvector
            results = await self.embeddings_adapter.get_all(
                filters=filters,
                limit=100  # Récupérer plus pour filtrer par similarité
            )
            
            # Calculer les similarités et trier
            scored_results = []
            for result in results:
                if result.get("vector"):
                    # Calculer similarité cosinus
                    similarity = self._cosine_similarity(query_embedding, result["vector"])
                    
                    if min_similarity is None or similarity >= min_similarity:
                        scored_results.append({
                            "track_id": result.get("track_id"),
                            "similarity": similarity,
                            "embedding_type": result.get("embedding_type"),
                            "embedding_source": result.get("embedding_source"),
                            "embedding_model": result.get("embedding_model"),
                            "calculated_at": result.get("calculated_at")
                        })
            
            # Trier par similarité décroissante et limiter
            scored_results.sort(key=lambda x: x["similarity"], reverse=True)
            return scored_results[:limit]
            
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle Supabase: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def add_track_embedding(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str = "semantic",
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Ajoute ou met à jour un embedding de track.
        
        Args:
            track_id: ID de la track
            embedding: Vecteur d'embedding
            embedding_type: Type d'embedding
            embedding_source: Source de vectorisation
            embedding_model: Modèle utilisé
            
        Returns:
            True si succès
        """
        if self.use_supabase:
            return await self._add_embedding_supabase(
                track_id, embedding, embedding_type, embedding_source, embedding_model
            )
        else:
            raise RuntimeError("VectorSearchServiceV2 requires Supabase mode")
    
    async def _add_embedding_supabase(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str,
        embedding_source: Optional[str],
        embedding_model: Optional[str]
    ) -> bool:
        """Ajoute un embedding via Supabase."""
        try:
            # Vérifier si l'embedding existe déjà
            existing = await self.embeddings_adapter.get_all(
                filters={
                    "track_id": track_id,
                    "embedding_type": embedding_type
                },
                limit=1
            )
            
            data = {
                "track_id": track_id,
                "vector": embedding,
                "embedding_type": embedding_type,
                "embedding_source": embedding_source,
                "embedding_model": embedding_model
            }
            
            if existing:
                # Mettre à jour
                await self.embeddings_adapter.update(
                    existing[0]["id"],
                    data
                )
                logger.debug(f"Embedding mis à jour pour track_id: {track_id}")
            else:
                # Créer
                await self.embeddings_adapter.create(data)
                logger.debug(f"Embedding créé pour track_id: {track_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout embedding Supabase: {e}")
            return False
    
    async def get_track_embedding(
        self,
        track_id: int,
        embedding_type: str = "semantic"
    ) -> Optional[List[float]]:
        """
        Récupère l'embedding d'une track.
        
        Args:
            track_id: ID de la track
            embedding_type: Type d'embedding
            
        Returns:
            Vecteur d'embedding ou None
        """
        if self.use_supabase:
            try:
                results = await self.embeddings_adapter.get_all(
                    filters={
                        "track_id": track_id,
                        "embedding_type": embedding_type
                    },
                    limit=1
                )
                
                if results and results[0].get("vector"):
                    return results[0]["vector"]
                return None
                
            except Exception as e:
                logger.error(f"Erreur récupération embedding Supabase: {e}")
                return None
        else:
            raise RuntimeError("VectorSearchServiceV2 requires Supabase mode")
    
    async def find_similar_by_track_id(
        self,
        track_id: int,
        limit: int = 10,
        embedding_type: str = "semantic"
    ) -> List[Dict[str, Any]]:
        """
        Trouve des tracks similaires à une track de référence.
        
        Args:
            track_id: ID de la track de référence
            limit: Nombre max de résultats
            embedding_type: Type d'embedding
            
        Returns:
            Liste des tracks similaires
        """
        # Récupérer l'embedding de la track de référence
        reference_embedding = await self.get_track_embedding(track_id, embedding_type)
        
        if reference_embedding is None:
            logger.warning(f"Pas d'embedding trouvé pour track_id: {track_id}")
            return []
        
        # Rechercher des tracks similaires
        similar = await self.find_similar_tracks(
            query_embedding=reference_embedding,
            limit=limit + 1,  # +1 pour exclure la track elle-même
            embedding_type=embedding_type
        )
        
        # Exclure la track de référence des résultats
        return [s for s in similar if s.get("track_id") != track_id][:limit]
    
    async def batch_add_embeddings(
        self,
        embeddings_data: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        Ajoute plusieurs embeddings en batch.
        
        Args:
            embeddings_data: Liste de dicts avec track_id, vector, embedding_type, etc.
            
        Returns:
            Tuple (succès, échecs)
        """
        if not self.use_supabase:
            raise RuntimeError("VectorSearchServiceV2 requires Supabase mode")
        
        success = 0
        failed = 0
        
        for data in embeddings_data:
            try:
                result = await self.add_track_embedding(
                    track_id=data["track_id"],
                    embedding=data["vector"],
                    embedding_type=data.get("embedding_type", "semantic"),
                    embedding_source=data.get("embedding_source"),
                    embedding_model=data.get("embedding_model")
                )
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Erreur batch embedding track_id {data.get('track_id')}: {e}")
                failed += 1
        
        logger.info(f"Batch embeddings: {success} succès, {failed} échecs")
        return success, failed


# Singleton instance
_vector_search_service_v2: Optional[VectorSearchServiceV2] = None


def get_vector_search_service_v2() -> VectorSearchServiceV2:
    """Factory pour VectorSearchServiceV2."""
    global _vector_search_service_v2
    if _vector_search_service_v2 is None:
        _vector_search_service_v2 = VectorSearchServiceV2()
    return _vector_search_service_v2


def reset_vector_search_service_v2():
    """Reset du singleton (utile pour tests)."""
    global _vector_search_service_v2
    _vector_search_service_v2 = None

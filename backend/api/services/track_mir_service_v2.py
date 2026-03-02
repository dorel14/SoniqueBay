"""
Service MIR (Music Information Retrieval) V2 pour Supabase.
Gère les métadonnées musicales extraites : scores MIR, tags synthétiques, etc.
"""

from typing import List, Dict, Any, Optional
from backend.api.utils.logging import logger
from backend.api.utils.db_config import is_migrated, USE_SUPABASE
from backend.api.utils.db_adapter import get_adapter


class TrackMIRServiceV2:
    """
    Service MIR V2 pour gestion des métadonnées musicales.
    
    Tables concernées:
    - track_mir_scores: Scores normalisés (energy, danceability, etc.)
    - track_mir_synthetic_tags: Tags générés par IA
    - track_mir_normalized: Données MIR normalisées
    - track_mir_raw: Données MIR brutes
    """
    
    def __init__(self):
        self.use_supabase = USE_SUPABASE and is_migrated("track_mir_scores")
        self._scores_adapter = None
        self._tags_adapter = None
        self._normalized_adapter = None
        self._raw_adapter = None
        
        if not self.use_supabase:
            logger.info("TrackMIRServiceV2 initialisé avec SQLAlchemy (fallback)")
        else:
            logger.info("TrackMIRServiceV2 initialisé avec Supabase")
    
    @property
    def scores_adapter(self):
        if self._scores_adapter is None and self.use_supabase:
            self._scores_adapter = get_adapter("track_mir_scores")
        return self._scores_adapter
    
    @property
    def tags_adapter(self):
        if self._tags_adapter is None and self.use_supabase:
            self._tags_adapter = get_adapter("track_mir_synthetic_tags")
        return self._tags_adapter
    
    @property
    def normalized_adapter(self):
        if self._normalized_adapter is None and self.use_supabase:
            self._normalized_adapter = get_adapter("track_mir_normalized")
        return self._normalized_adapter
    
    @property
    def raw_adapter(self):
        if self._raw_adapter is None and self.use_supabase:
            self._raw_adapter = get_adapter("track_mir_raw")
        return self._raw_adapter
    
    # ==================== SCORES MIR ====================
    
    async def get_track_scores(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les scores MIR d'une track.
        
        Args:
            track_id: ID de la track
            
        Returns:
            Dict avec les scores ou None
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            results = await self.scores_adapter.get_all(
                filters={"track_id": track_id},
                limit=1
            )
            
            if results:
                return {
                    "track_id": track_id,
                    "energy_score": results[0].get("energy_score"),
                    "danceability_score": results[0].get("danceability_score"),
                    "acousticness_score": results[0].get("acousticness_score"),
                    "valence_score": results[0].get("valence_score"),
                    "instrumentalness_score": results[0].get("instrumentalness_score"),
                    "calculated_at": results[0].get("calculated_at"),
                    "calculation_version": results[0].get("calculation_version")
                }
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération scores MIR: {e}")
            return None
    
    async def save_track_scores(
        self,
        track_id: int,
        scores: Dict[str, float],
        calculation_version: str = "1.0"
    ) -> bool:
        """
        Sauvegarde les scores MIR d'une track.
        
        Args:
            track_id: ID de la track
            scores: Dict avec energy_score, danceability_score, etc.
            calculation_version: Version du calcul
            
        Returns:
            True si succès
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            # Vérifier si existe déjà
            existing = await self.scores_adapter.get_all(
                filters={"track_id": track_id},
                limit=1
            )
            
            data = {
                "track_id": track_id,
                "energy_score": scores.get("energy_score"),
                "danceability_score": scores.get("danceability_score"),
                "acousticness_score": scores.get("acousticness_score"),
                "valence_score": scores.get("valence_score"),
                "instrumentalness_score": scores.get("instrumentalness_score"),
                "calculation_version": calculation_version
            }
            
            if existing:
                await self.scores_adapter.update(existing[0]["id"], data)
                logger.debug(f"Scores MIR mis à jour pour track_id: {track_id}")
            else:
                await self.scores_adapter.create(data)
                logger.debug(f"Scores MIR créés pour track_id: {track_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde scores MIR: {e}")
            return False
    
    async def find_tracks_by_score_range(
        self,
        score_type: str,
        min_value: float,
        max_value: float,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Recherche de tracks par plage de score MIR.
        
        Args:
            score_type: Type de score (energy_score, danceability_score, etc.)
            min_value: Valeur minimale
            max_value: Valeur maximale
            limit: Nombre max de résultats
            
        Returns:
            Liste des tracks avec leurs scores
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            # Construire les filtres pour la plage
            filters = {
                score_type: {
                    "gte": min_value,
                    "lte": max_value
                }
            }
            
            results = await self.scores_adapter.get_all(
                filters=filters,
                limit=limit
            )
            
            return [
                {
                    "track_id": r.get("track_id"),
                    "score": r.get(score_type),
                    "calculated_at": r.get("calculated_at")
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Erreur recherche par score MIR: {e}")
            return []
    
    # ==================== TAGS SYNTHÉTIQUES ====================
    
    async def get_track_synthetic_tags(self, track_id: int) -> List[str]:
        """
        Récupère les tags synthétiques d'une track.
        
        Args:
            track_id: ID de la track
            
        Returns:
            Liste des tags
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            results = await self.tags_adapter.get_all(
                filters={"track_id": track_id},
                limit=1
            )
            
            if results and results[0].get("synthetic_tags"):
                return results[0]["synthetic_tags"]
            return []
            
        except Exception as e:
            logger.error(f"Erreur récupération tags synthétiques: {e}")
            return []
    
    async def save_track_synthetic_tags(
        self,
        track_id: int,
        tags: List[str],
        generation_method: str = "llm",
        confidence_score: Optional[float] = None
    ) -> bool:
        """
        Sauvegarde les tags synthétiques d'une track.
        
        Args:
            track_id: ID de la track
            tags: Liste des tags générés
            generation_method: Méthode de génération (llm, heuristic, etc.)
            confidence_score: Score de confiance (optionnel)
            
        Returns:
            True si succès
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            existing = await self.tags_adapter.get_all(
                filters={"track_id": track_id},
                limit=1
            )
            
            data = {
                "track_id": track_id,
                "synthetic_tags": tags,
                "generation_method": generation_method,
                "confidence_score": confidence_score
            }
            
            if existing:
                await self.tags_adapter.update(existing[0]["id"], data)
            else:
                await self.tags_adapter.create(data)
            
            logger.debug(f"Tags synthétiques sauvegardés pour track_id: {track_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde tags synthétiques: {e}")
            return False
    
    # ==================== DONNÉES NORMALISÉES ====================
    
    async def get_normalized_data(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données MIR normalisées d'une track.
        
        Args:
            track_id: ID de la track
            
        Returns:
            Dict avec les données normalisées ou None
        """
        if not self.use_supabase:
            raise RuntimeError("TrackMIRServiceV2 requires Supabase mode")
        
        try:
            results = await self.normalized_adapter.get_all(
                filters={"track_id": track_id},
                limit=1
            )
            
            if results:
                return {
                    "track_id": track_id,
                    "normalized_features": results[0].get("normalized_features"),
                    "feature_version": results[0].get("feature_version"),
                    "calculated_at": results[0].get("calculated_at")
                }
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération données normalisées: {e}")
            return None
    
    # ==================== RECHERCHE AVANCÉE ====================
    
    async def find_similar_by_mood(
        self,
        track_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Trouve des tracks avec une ambiance similaire.
        
        Args:
            track_id: ID de la track de référence
            limit: Nombre max de résultats
            
        Returns:
            Liste des tracks similaires avec scores
        """
        # Récupérer les scores de la track de référence
        reference_scores = await self.get_track_scores(track_id)
        
        if not reference_scores:
            return []
        
        # Construire une requête pour trouver des tracks avec des scores proches
        # C'est une simplification - en production, on utiliserait une distance euclidienne
        energy = reference_scores.get("energy_score", 0.5)
        valence = reference_scores.get("valence_score", 0.5)
        danceability = reference_scores.get("danceability_score", 0.5)
        
        # Plages de tolérance
        tolerance = 0.2
        
        try:
            # Recherche par plages
            filters = {
                "energy_score": {"gte": energy - tolerance, "lte": energy + tolerance},
                "valence_score": {"gte": valence - tolerance, "lte": valence + tolerance},
                "danceability_score": {"gte": danceability - tolerance, "lte": danceability + tolerance}
            }
            
            results = await self.scores_adapter.get_all(
                filters=filters,
                limit=limit + 1  # +1 pour exclure la track elle-même
            )
            
            # Exclure la track de référence et formater
            similar = []
            for r in results:
                if r.get("track_id") != track_id:
                    similar.append({
                        "track_id": r.get("track_id"),
                        "energy_score": r.get("energy_score"),
                        "valence_score": r.get("valence_score"),
                        "danceability_score": r.get("danceability_score"),
                        "similarity": self._calculate_mood_similarity(
                            reference_scores, r
                        )
                    })
            
            # Trier par similarité
            similar.sort(key=lambda x: x["similarity"], reverse=True)
            return similar[:limit]
            
        except Exception as e:
            logger.error(f"Erreur recherche par ambiance: {e}")
            return []
    
    def _calculate_mood_similarity(
        self,
        ref_scores: Dict[str, Any],
        compare_scores: Dict[str, Any]
    ) -> float:
        """Calcule une similarité d'ambiance entre deux tracks."""
        import math
        
        # Extraire les scores
        ref_energy = ref_scores.get("energy_score", 0.5) or 0.5
        ref_valence = ref_scores.get("valence_score", 0.5) or 0.5
        ref_dance = ref_scores.get("danceability_score", 0.5) or 0.5
        
        comp_energy = compare_scores.get("energy_score", 0.5) or 0.5
        comp_valence = compare_scores.get("valence_score", 0.5) or 0.5
        comp_dance = compare_scores.get("danceability_score", 0.5) or 0.5
        
        # Distance euclidienne normalisée
        distance = math.sqrt(
            (ref_energy - comp_energy) ** 2 +
            (ref_valence - comp_valence) ** 2 +
            (ref_dance - comp_dance) ** 2
        )
        
        # Convertir en similarité (0-1)
        max_distance = math.sqrt(3)  # Distance max dans un cube 3D
        similarity = 1 - (distance / max_distance)
        
        return max(0, min(1, similarity))


# Singleton instance
_mir_service_v2: Optional[TrackMIRServiceV2] = None


def get_track_mir_service_v2() -> TrackMIRServiceV2:
    """Factory pour TrackMIRServiceV2."""
    global _mir_service_v2
    if _mir_service_v2 is None:
        _mir_service_v2 = TrackMIRServiceV2()
    return _mir_service_v2


def reset_track_mir_service_v2():
    """Reset du singleton (utile pour tests)."""
    global _mir_service_v2
    _mir_service_v2 = None

"""Orchestrateur du pipeline MIR complet.

Ce service orchestre le pipeline complet de traitement MIR pour une track:
1. Extraction des tags bruts (AcoustID + standards)
2. Normalisation des features
3. Calcul des scores globaux
4. Fusion des taxonomies de genres
5. Génération des tags synthétiques
6. Stockage des résultats

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import os
import httpx
import asyncio
from typing import Optional
from backend_worker.utils.logging import logger


class MIRPipelineService:
    """Service pour l'orchestration du pipeline MIR.
    
    Ce service coordonne tous les services MIR pour traiter une track de manière
    complète et cohérente. Il:
    
    1. Récupère les tags bruts (AcoustID + standards)
    2. Normalise les features avec MIRNormalizationService
    3. Calcule les scores avec MIRScoringService
    4. Fusionne les genres avec GenreTaxonomyService
    5. Génère les tags synthétiques avec SyntheticTagsService
    6. Stocke tous les résultats via l'API
    
    Attributes:
        normalization_service: Service de normalisation des features
        scoring_service: Service de calcul des scores
        taxonomy_service: Service de fusion des genres
        synthetic_tags_service: Service de génération des tags synthétiques
    """
    
    def __init__(self) -> None:
        """Initialise le pipeline MIR avec tous les services."""
        logger.info("[MIRPipeline] Initialisation du pipeline MIR")
        
        # Initialiser les services
        from backend_worker.services.mir_normalization_service import MIRNormalizationService
        from backend_worker.services.mir_scoring_service import MIRScoringService
        from backend_worker.services.genre_taxonomy_service import GenreTaxonomyService
        from backend_worker.services.synthetic_tags_service import SyntheticTagsService
        
        self.normalization_service = MIRNormalizationService()
        self.scoring_service = MIRScoringService()
        self.taxonomy_service = GenreTaxonomyService()
        self.synthetic_tags_service = SyntheticTagsService()
        
        # Configuration API
        self.api_url = os.getenv("API_URL", "http://api:8001")
        
        logger.info("[MIRPipeline] Pipeline MIR initialisé avec succès")
    
    async def process_track_mir(
        self,
        track_id: int,
        file_path: str,
        tags: dict | None = None
    ) -> dict:
        """Exécute le pipeline MIR complet pour une track.
        
        Args:
            track_id: ID de la track
            file_path: Chemin vers le fichier audio
            tags: Dictionnaire optionnel des tags bruts
            
        Returns:
            Dictionnaire complet avec tous les résultats MIR
        """
        logger.info(f"[MIRPipeline] Début du traitement MIR pour track {track_id}")
        
        pipeline_result = {
            'track_id': track_id,
            'file_path': file_path,
            'success': False,
            'steps_completed': [],
            'raw_features': {},
            'normalized_features': {},
            'scores': {},
            'genre_taxonomy': {},
            'synthetic_tags': {},
            'storage_results': {},
            'error': None,
        }
        
        try:
            # ÉTAPE 1: Extraction des tags bruts
            logger.info(f"[MIRPipeline] Étape 1: Extraction des tags bruts pour track {track_id}")
            raw_features = await self._extract_raw_features(track_id, file_path, tags or {})
            pipeline_result['raw_features'] = raw_features
            pipeline_result['steps_completed'].append('raw_extraction')
            
            if not raw_features:
                logger.warning(f"[MIRPipeline] Aucun tag brut extrait pour track {track_id}")
            
            # ÉTAPE 2: Normalisation des features
            logger.info(f"[MIRPipeline] Étape 2: Normalisation des features pour track {track_id}")
            normalized_features = self.normalization_service.normalize_all_features(raw_features)
            pipeline_result['normalized_features'] = normalized_features
            pipeline_result['steps_completed'].append('normalization')
            
            # ÉTAPE 3: Calcul des scores globaux
            logger.info(f"[MIRPipeline] Étape 3: Calcul des scores pour track {track_id}")
            scores = self.scoring_service.calculate_all_scores(normalized_features)
            pipeline_result['scores'] = scores
            pipeline_result['steps_completed'].append('scoring')
            
            # ÉTAPE 4: Fusion des taxonomies de genres
            logger.info(f"[MIRPipeline] Étape 4: Fusion des genres pour track {track_id}")
            genre_taxonomy = self.taxonomy_service.process_genre_taxonomy(raw_features)
            pipeline_result['genre_taxonomy'] = genre_taxonomy
            pipeline_result['steps_completed'].append('genre_taxonomy')
            
            # ÉTAPE 5: Génération des tags synthétiques
            logger.info(f"[MIRPipeline] Étape 5: Génération des tags synthétiques pour track {track_id}")
            synthetic_tags = self.synthetic_tags_service.generate_all_synthetic_tags(
                normalized_features, scores
            )
            pipeline_result['synthetic_tags'] = synthetic_tags
            pipeline_result['steps_completed'].append('synthetic_tags')
            
            # ÉTAPE 6: Stockage des résultats
            logger.info(f"[MIRPipeline] Étape 6: Stockage des résultats pour track {track_id}")
            storage_results = await self._store_results(track_id, pipeline_result)
            pipeline_result['storage_results'] = storage_results
            pipeline_result['steps_completed'].append('storage')
            
            pipeline_result['success'] = all(storage_results.values()) if storage_results else True
            
            logger.info(f"[MIRPipeline] Pipeline MIR terminé pour track {track_id}: success={pipeline_result['success']}")
            
        except Exception as e:
            pipeline_result['error'] = str(e)
            logger.error(f"[MIRPipeline] Erreur pipeline MIR pour track {track_id}: {e}")
        
        return pipeline_result
    
    async def process_batch_mir(self, tracks_data: list) -> dict:
        """Exécute le pipeline MIR en lot pour plusieurs tracks.
        
        Args:
            tracks_data: Liste de dictionnaires avec track_id et file_path
            
        Returns:
            Résultats du traitement batch
        """
        logger.info(f"[MIRPipeline] Début du traitement batch MIR: {len(tracks_data)} tracks")
        
        successful = 0
        failed = 0
        results = []
        
        # Traitement séquentiel pour éviter la surcharge
        for track_data in tracks_data:
            track_id = track_data.get('track_id') or track_data.get('id')
            file_path = track_data.get('file_path') or track_data.get('path')
            tags = track_data.get('tags', {})
            
            if not track_id or not file_path:
                logger.warning(f"[MIRPipeline] Données track invalides: {track_data}")
                failed += 1
                continue
            
            try:
                result = await self.process_track_mir(track_id, file_path, tags)
                if result['success']:
                    successful += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as e:
                logger.error(f"[MIRPipeline] Erreur batch track {track_id}: {e}")
                failed += 1
                results.append({
                    'track_id': track_id,
                    'success': False,
                    'error': str(e)
                })
        
        logger.info(f"[MIRPipeline] Batch MIR terminé: {successful} succès, {failed} échecs")
        
        return {
            'total': len(tracks_data),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    async def _extract_raw_features(
        self,
        track_id: int,
        file_path: str,
        tags: dict
    ) -> dict:
        """Extrait les features brutes depuis les tags.
        
        Args:
            track_id: ID de la track
            file_path: Chemin vers le fichier audio
            tags: Tags existants
            
        Returns:
            Dictionnaire des features brutes
        """
        raw_features = dict(tags)
        
        # Ajouter les tags depuis audio_features_service si disponible
        try:
            from backend_worker.services.audio_features_service import (
                _extract_features_from_standard_tags,
                _extract_features_from_acoustid_tags
            )
            
            # Extraire depuis les tags AcoustID
            acoustid_features = _extract_features_from_acoustid_tags(tags)
            for key, value in acoustid_features.items():
                if value is not None and value != []:
                    raw_features[key] = value
            
            # Extraire depuis les tags standards
            standard_features = _extract_features_from_standard_tags(tags)
            for key, value in standard_features.items():
                if value is not None and value != []:
                    raw_features[key] = value
            
        except ImportError as e:
            logger.warning(f"[MIRPipeline] Impossible d'importer les extracteurs de tags: {e}")
        
        logger.debug(f"[MIRPipeline] Features brutes extraites: {len(raw_features)} clés")
        return raw_features
    
    async def _store_results(self, track_id: int, pipeline_result: dict) -> dict:
        """Stocke tous les résultats MIR via l'API.
        
        Args:
            track_id: ID de la track
            pipeline_result: Résultats du pipeline
            
        Returns:
            Dictionnaire des résultats de stockage
        """
        storage_results = {
            'normalized': False,
            'scores': False,
            'genre': False,
            'synthetic_tags': False,
        }
        
        normalized = pipeline_result.get('normalized_features', {})
        scores = pipeline_result.get('scores', {})
        genre = pipeline_result.get('genre_taxonomy', {})
        synthetic_tags = pipeline_result.get('synthetic_tags', {})
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Stocker les features normalisées
                if normalized:
                    response = await client.put(
                        f"{self.api_url}/api/tracks/{track_id}/audio-features",
                        json=normalized
                    )
                    storage_results['normalized'] = response.status_code == 200
                    if not storage_results['normalized']:
                        logger.warning(f"[MIRPipeline] Échec stockage normalized: {response.status_code}")
                
                # Stocker les scores
                if scores:
                    response = await client.post(
                        f"{self.api_url}/api/tracks/{track_id}/mir/scores",
                        json=scores
                    )
                    storage_results['scores'] = response.status_code == 200
                    if not storage_results['scores']:
                        logger.warning(f"[MIRPipeline] Échec stockage scores: {response.status_code}")
                
                # Stocker la taxonomie de genres
                if genre:
                    response = await client.post(
                        f"{self.api_url}/api/tracks/{track_id}/mir/genre",
                        json=genre
                    )
                    storage_results['genre'] = response.status_code == 200
                    if not storage_results['genre']:
                        logger.warning(f"[MIRPipeline] Échec stockage genre: {response.status_code}")
                
                # Stocker les tags synthétiques
                if synthetic_tags:
                    response = await client.post(
                        f"{self.api_url}/api/tracks/{track_id}/mir/synthetic-tags",
                        json=synthetic_tags
                    )
                    storage_results['synthetic_tags'] = response.status_code == 200
                    if not storage_results['synthetic_tags']:
                        logger.warning(f"[MIRPipeline] Échec stockage synthetic_tags: {response.status_code}")
                
        except Exception as e:
            logger.error(f"[MIRPipeline] Erreur stockage résultats pour track {track_id}: {e}")
        
        stored_count = sum(1 for v in storage_results.values() if v)
        logger.info(f"[MIRPipeline] Stockage terminé: {stored_count}/{len(storage_results)} résultats stockés")
        
        return storage_results
    
    async def reprocess_track_mir(self, track_id: int, file_path: str) -> dict:
        """Re-traite complètement les tags MIR d'une track.
        
        Args:
            track_id: ID de la track
            file_path: Chemin vers le fichier audio
            
        Returns:
            Résultats du re-traitement
        """
        logger.info(f"[MIRPipeline] Re-traitement MIR pour track {track_id}")
        
        # Récupérer les tags existants via l'API
        tags = await self._fetch_existing_tags(track_id)
        
        # Exécuter le pipeline complet
        result = await self.process_track_mir(track_id, file_path, tags)
        
        return result
    
    async def _fetch_existing_tags(self, track_id: int) -> dict:
        """Récupère les tags existants d'une track via l'API.
        
        Args:
            track_id: ID de la track
            
        Returns:
            Dictionnaire des tags existants
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/api/tracks/{track_id}/tags"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"[MIRPipeline] Impossible de récupérer les tags pour track {track_id}: {e}")
        
        return {}
    
    def get_pipeline_status(self) -> dict:
        """Retourne l'état du pipeline pour monitoring.
        
        Returns:
            État du pipeline avec les versions des services
        """
        return {
            'pipeline_version': '1.0.0',
            'normalization_service': self.normalization_service.__class__.__name__,
            'scoring_service': self.scoring_service.__class__.__name__,
            'taxonomy_service': self.taxonomy_service.__class__.__name__,
            'synthetic_tags_service': self.synthetic_tags_service.__class__.__name__,
            'api_url': self.api_url,
        }

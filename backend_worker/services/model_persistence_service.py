"""
Service de persistance et versioning des modèles de vectorisation.

Gère :
- Sauvegarde/chargement des modèles entraînés
- Versioning des modèles (v1, v2, etc.)
- Base de données des métadonnées des modèles
- Rollback vers version précédente

Auteur : Kilo Code
Optimisé pour : Raspberry Pi 4
"""

import asyncio
import joblib
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx
import os

from backend_worker.services.vectorization_service import (
    OptimizedVectorizationService
)
from backend_worker.services.data_directory_initializer import data_directory_initializer, initialize_data_directories
from backend_worker.utils.logging import logger


class ModelVersion:
    """Représente une version de modèle."""
    
    def __init__(self, version_id: str, created_at: datetime, model_data: Dict[str, Any]):
        """
        Initialise une version de modèle.
        
        Args:
            version_id: Identifiant de la version
            created_at: Date de création
            model_data: Données du modèle
        """
        self.version_id = version_id
        self.created_at = created_at
        self.model_data = model_data
        self.checksum = self._calculate_checksum(model_data)
    
    def _calculate_checksum(self, model_data: Dict[str, Any]) -> str:
        """Calcule un checksum pour vérifier l'intégrité."""
        data_str = json.dumps(model_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]


class ModelPersistenceService:
    """Service pour persister et gérer les versions des modèles."""
    
    def __init__(self):
        """Initialise le service de persistance."""
        self.models_dir = Path("/app/data/models")
        
        # Initialiser les répertoires de données avant utilisation
        logger.info("[MODEL_PERSISTENCE] Initialisation des répertoires de données...")
        if not initialize_data_directories():
            logger.error("[MODEL_PERSISTENCE] Échec de l'initialisation des répertoires")
            # Tentative de création directe du répertoire models
            try:
                self.models_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"[MODEL_PERSISTENCE] Répertoire {self.models_dir} créé directement")
            except Exception as e:
                logger.error(f"[MODEL_PERSISTENCE] Impossible de créer {self.models_dir}: {e}")
                raise PermissionError(f"Impossible d'initialiser le répertoire des modèles: {e}")
        
        # Vérifier l'accès en écriture
        try:
            test_file = self.models_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            logger.info(f"[MODEL_PERSISTENCE] Accès en écriture vérifié: {self.models_dir}")
        except Exception as e:
            logger.error(f"[MODEL_PERSISTENCE] Pas d'accès en écriture à {self.models_dir}: {e}")
            raise PermissionError(f"Pas d'accès en écriture au répertoire des modèles: {e}")
        
        self.library_api_url = os.getenv("LIBRARY_API_URL", "http://library-api:8001")
        self.current_version = None
        
        logger.info(f"ModelPersistenceService initialisé avec succès: {self.models_dir}")
    
    async def save_model_version(self, service: OptimizedVectorizationService, 
                                version_name: str = None) -> ModelVersion:
        """
        Sauvegarde une version du modèle.
        
        Args:
            service: Service de vectorisation entraîné
            version_name: Nom de version (auto-généré si None)
            
        Returns:
            Version du modèle sauvegardée
        """
        try:
            # Générer ID de version si nécessaire
            if version_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                version_name = f"v{timestamp}"
            
            version_id = version_name
            
            # Préparer les données du modèle
            model_data = {
                "version_id": version_id,
                "created_at": datetime.now().isoformat(),
                "text_vectorizer": {
                    "pipeline": service.text_vectorizer.pipeline,
                    "vector_dimension": service.text_vectorizer.vector_dimension,
                    "is_fitted": service.text_vectorizer.is_fitted
                },
                "audio_vectorizer": {
                    "scaler": service.audio_vectorizer.scaler,
                    "key_encoder": service.audio_vectorizer.key_encoder,
                    "scale_encoder": service.audio_vectorizer.scale_encoder,
                    "camelot_encoder": service.audio_vectorizer.camelot_encoder,
                    "is_fitted": service.audio_vectorizer.is_fitted
                },
                "tag_classifier": {
                    "genre_classifier": service.tag_classifier.genre_classifier,
                    "mood_classifier": service.tag_classifier.mood_classifier,
                    "genre_classes": getattr(service.tag_classifier, 'genre_classes', []),
                    "mood_classes": getattr(service.tag_classifier, 'mood_classes', []),
                    "is_fitted": service.tag_classifier.is_fitted
                },
                "metadata": {
                    "vector_dimension": service.vector_dimension,
                    "model_type": "scikit-learn_optimized",
                    "optimized_for": "RPi4",
                    "text_features": service.text_vectorizer.extract_text_features.__code__.co_varnames,
                    "audio_features": service.audio_vectorizer.feature_names
                }
            }
            
            # Sauvegarder avec joblib (plus efficace que pickle pour sklearn)
            model_file = self.models_dir / f"{version_id}.joblib"
            
            # Séparer les modèles sklearn pour joblib
            sklearn_models = {
                "text_vectorizer": service.text_vectorizer.pipeline,
                "audio_vectorizer": service.audio_vectorizer.scaler,
                "key_encoder": service.audio_vectorizer.key_encoder,
                "scale_encoder": service.audio_vectorizer.scale_encoder,
                "camelot_encoder": service.audio_vectorizer.camelot_encoder,
                "genre_classifier": service.tag_classifier.genre_classifier,
                "mood_classifier": service.tag_classifier.mood_classifier
            }
            
            joblib.dump(sklearn_models, model_file)
            
            # Sauvegarder les métadonnées JSON
            metadata_file = self.models_dir / f"{version_id}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(model_data, f, indent=2, default=str)
            
            # Créer l'objet version
            version = ModelVersion(version_id, datetime.now(), model_data)
            
            # Mettre à jour la version courante
            self.current_version = version
            
            logger.info(f"Modèle sauvegardé: version {version_id}")
            logger.info(f"Fichiers: {model_file}, {metadata_file}")
            
            # Sauvegarder en base via API (si disponible)
            await self._save_version_metadata(version)
            
            return version
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde modèle: {e}")
            raise
    
    async def load_model_version(self, version_id: str) -> OptimizedVectorizationService:
        """
        Charge une version du modèle.
        
        Args:
            version_id: ID de la version à charger
            
        Returns:
            Service de vectorisation avec le modèle chargé
        """
        try:
            # Vérifier existence des fichiers
            model_file = self.models_dir / f"{version_id}.joblib"
            metadata_file = self.models_dir / f"{version_id}_metadata.json"
            
            if not model_file.exists() or not metadata_file.exists():
                raise FileNotFoundError(f"Version {version_id} non trouvée")
            
            # Charger les métadonnées
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Charger les modèles sklearn
            sklearn_models = joblib.load(model_file)
            
            # Recréer le service
            service = OptimizedVectorizationService()
            
            # Restaurer les vectoriseurs
            service.text_vectorizer.pipeline = sklearn_models["text_vectorizer"]
            service.audio_vectorizer.scaler = sklearn_models["audio_vectorizer"]
            service.audio_vectorizer.key_encoder = sklearn_models["key_encoder"]
            service.audio_vectorizer.scale_encoder = sklearn_models["scale_encoder"]
            service.audio_vectorizer.camelot_encoder = sklearn_models["camelot_encoder"]
            service.audio_vectorizer.is_fitted = True
            
            service.tag_classifier.genre_classifier = sklearn_models["genre_classifier"]
            service.tag_classifier.mood_classifier = sklearn_models["mood_classifier"]
            service.tag_classifier.genre_classes = metadata["tag_classifier"]["genre_classes"]
            service.tag_classifier.mood_classes = metadata["tag_classifier"]["mood_classes"]
            service.tag_classifier.is_fitted = True
            
            service.vector_dimension = metadata["metadata"]["vector_dimension"]
            service.is_trained = True
            
            # Mettre à jour la version courante
            self.current_version = ModelVersion(version_id, datetime.now(), metadata)
            
            logger.info(f"Modèle chargé: version {version_id}")
            return service
            
        except Exception as e:
            logger.error(f"Erreur chargement modèle {version_id}: {e}")
            raise
    
    async def list_model_versions(self) -> List[ModelVersion]:
        """
        Liste toutes les versions de modèles disponibles.
        
        Returns:
            Liste des versions triées par date décroissante
        """
        try:
            versions = []
            
            # Scanner le répertoire des modèles
            for model_file in self.models_dir.glob("*.joblib"):
                version_id = model_file.stem
                metadata_file = self.models_dir / f"{version_id}_metadata.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        created_at = datetime.fromisoformat(metadata["created_at"])
                        version = ModelVersion(version_id, created_at, metadata)
                        versions.append(version)
                    except Exception as e:
                        logger.warning(f"Erreur lecture métadonnées {version_id}: {e}")
                        continue
            
            # Trier par date décroissante
            versions.sort(key=lambda v: v.created_at, reverse=True)
            
            logger.info(f"Trouvé {len(versions)} versions de modèles")
            return versions
            
        except Exception as e:
            logger.error(f"Erreur listage versions: {e}")
            return []
    
    async def delete_model_version(self, version_id: str) -> bool:
        """
        Supprime une version de modèle.
        
        Args:
            version_id: ID de la version à supprimer
            
        Returns:
            True si succès, False sinon
        """
        try:
            model_file = self.models_dir / f"{version_id}.joblib"
            metadata_file = self.models_dir / f"{version_id}_metadata.json"
            
            # Supprimer les fichiers
            deleted = False
            if model_file.exists():
                model_file.unlink()
                deleted = True
            
            if metadata_file.exists():
                metadata_file.unlink()
                deleted = True
            
            if deleted:
                logger.info(f"Version {version_id} supprimée")
                # TODO: Supprimer aussi de la base via API
            else:
                logger.warning(f"Version {version_id} non trouvée")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Erreur suppression version {version_id}: {e}")
            return False
    
    async def get_current_version(self) -> Optional[ModelVersion]:
        """
        Récupère la version courante du modèle.
        
        Returns:
            Version courante ou None
        """
        if self.current_version:
            return self.current_version
        
        # Charger la dernière version
        versions = await self.list_model_versions()
        if versions:
            self.current_version = versions[0]
            return self.current_version
        
        return None
    
    async def _save_version_metadata(self, version: ModelVersion):
        """Sauvegarde les métadonnées de version en base."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                metadata = {
                    "version_id": version.version_id,
                    "created_at": version.created_at.isoformat(),
                    "checksum": version.checksum,
                    "model_info": version.model_data
                }
                
                response = await client.post(
                    f"{self.library_api_url}/api/model-versions",
                    json=metadata
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Métadonnées version sauvegardées: {version.version_id}")
                else:
                    logger.warning(f"Erreur sauvegarde métadonnées: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Impossible sauvegarder métadonnées: {e}")


class ModelVersioningService:
    """Service pour gérer le versioning intelligent des modèles."""
    
    def __init__(self):
        """Initialise le service de versioning."""
        self.persistence_service = ModelPersistenceService()
        self.retrain_threshold_days = 7  # Seuil pour réentraînement automatique
        self.version_history_limit = 10  # Limiter l'historique
        
    async def should_retrain(self) -> Dict[str, Any]:
        """
        Détermine si un réentraînement est nécessaire.
        
        Returns:
            Statut et raison du réentraînement
        """
        try:
            current_version = await self.persistence_service.get_current_version()
            
            if not current_version:
                return {
                    "should_retrain": True,
                    "reason": "no_model_found",
                    "message": "Aucun modèle existant"
                }
            
            # Vérifier l'âge du modèle
            age_days = (datetime.now() - current_version.created_at).days
            
            if age_days >= self.retrain_threshold_days:
                return {
                    "should_retrain": True,
                    "reason": "model_too_old",
                    "message": f"Modèle vieil de {age_days} jours",
                    "current_version": current_version.version_id,
                    "age_days": age_days
                }
            
            # Vérifier s'il y a de nouvelles données
            tracks_count = await self._get_tracks_count()
            model_tracks = current_version.model_data.get("metadata", {}).get("tracks_count", 0)
            
            # Si 10% de nouvelles tracks ou plus
            if tracks_count > model_tracks * 1.1:
                return {
                    "should_retrain": True,
                    "reason": "new_data_available",
                    "message": f"Nouvelles tracks détectées: {tracks_count - model_tracks}",
                    "current_version": current_version.version_id,
                    "tracks_count": tracks_count,
                    "model_tracks": model_tracks
                }
            
            return {
                "should_retrain": False,
                "reason": "up_to_date",
                "message": "Modèle à jour",
                "current_version": current_version.version_id,
                "age_days": age_days,
                "tracks_count": tracks_count
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification réentraînement: {e}")
            return {
                "should_retrain": True,
                "reason": "error",
                "message": f"Erreur: {str(e)}"
            }
    
    async def _get_tracks_count(self) -> int:
        """Récupère le nombre total de tracks."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.persistence_service.library_api_url}/api/tracks/count")
                if response.status_code == 200:
                    return response.json().get("count", 0)
                return 0
        except Exception as e:
            logger.warning(f"Impossible récupérer nombre tracks: {e}")
            return 0
    
    async def retrain_with_versioning(self, force: bool = False) -> Dict[str, Any]:
        """
        Réentraîne le modèle avec gestion de versioning.
        
        Args:
            force: Forcer le réentraînement même si pas nécessaire
            
        Returns:
            Résultat du réentraînement avec versioning
        """
        try:
            # Vérifier si réentraînement nécessaire
            if not force:
                should_retrain = await self.should_retrain()
                if not should_retrain["should_retrain"]:
                    return {
                        "status": "skipped",
                        "message": should_retrain["message"],
                        "details": should_retrain
                    }
            
            # Entraîner nouveau modèle
            logger.info("=== RÉENTRAÎNEMENT AVEC VERSIONING ===")
            
            service = OptimizedVectorizationService()
            train_result = await service.train_vectorizers()
            
            if train_result["status"] != "success":
                return train_result
            
            # Sauvegarder avec versioning
            current_versions = await self.persistence_service.list_model_versions()
            
            # Créer nouveau nom de version
            if current_versions:
                latest_version = current_versions[0]
                # Extraire numéro de version
                try:
                    version_num = int(latest_version.version_id.replace("v", ""))
                    new_version = f"v{version_num + 1}"
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Erreur parsing version ID '{latest_version.version_id}': {e}")
                    new_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                new_version = "v1"
            
            # Sauvegarder le nouveau modèle
            new_version_obj = await self.persistence_service.save_model_version(
                service, new_version
            )
            
            # Nettoyer anciennes versions si trop nombreuses
            if len(current_versions) >= self.version_history_limit:
                old_versions = current_versions[self.version_history_limit:]
                for old_version in old_versions:
                    await self.persistence_service.delete_model_version(old_version.version_id)
            
            result = {
                "status": "success",
                "previous_version": current_versions[0].version_id if current_versions else None,
                "new_version": new_version,
                "training_stats": train_result,
                "version_info": {
                    "id": new_version_obj.version_id,
                    "created_at": new_version_obj.created_at.isoformat(),
                    "checksum": new_version_obj.checksum
                }
            }
            
            logger.info(f"=== RÉENTRAÎNEMENT TERMINÉ: {new_version} ===")
            return result
            
        except Exception as e:
            logger.error(f"Erreur réentraînement avec versioning: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# === FONCTIONS UTILITAIRES ===

async def quick_retrain(force: bool = False) -> Dict[str, Any]:
    """
    Fonction utilitaire pour réentraînement rapide.
    
    Args:
        force: Forcer le réentraînement
        
    Returns:
        Résultat du réentraînement
    """
    versioning_service = ModelVersioningService()
    return await versioning_service.retrain_with_versioning(force)


async def show_model_versions() -> List[Dict[str, Any]]:
    """
    Affiche toutes les versions de modèles.
    
    Returns:
        Liste des versions avec détails
    """
    persistence_service = ModelPersistenceService()
    versions = await persistence_service.list_model_versions()
    
    return [
        {
            "version_id": v.version_id,
            "created_at": v.created_at.isoformat(),
            "tracks_processed": v.model_data.get("tracks_processed", 0),
            "vector_dimension": v.model_data.get("metadata", {}).get("vector_dimension", 0),
            "model_type": v.model_data.get("metadata", {}).get("model_type", ""),
            "checksum": v.checksum
        }
        for v in versions
    ]


if __name__ == "__main__":
    """Tests du service de persistance."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def test_persistence():
        """Test de la persistance."""
        print("=== TEST PERSISTANCE MODÈLES ===")
        
        # Créer un service de test
        service = OptimizedVectorizationService()
        
        # Simuler données d'entraînement
        
        # Entraîner (simulation)
        service.text_vectorizer.is_fitted = True
        service.audio_vectorizer.is_fitted = True
        service.tag_classifier.is_fitted = True
        service.is_trained = True
        
        persistence_service = ModelPersistenceService()
        
        # Test sauvegarde
        print("\n1. Test sauvegarde...")
        version = await persistence_service.save_model_version(service, "test_v1")
        print(f"Version sauvegardée: {version.version_id}")
        
        # Test listing
        print("\n2. Test listage...")
        versions = await persistence_service.list_model_versions()
        print(f"Versions trouvées: {len(versions)}")
        for v in versions:
            print(f"  - {v.version_id} ({v.created_at})")
        
        # Test versioning
        print("\n3. Test versioning...")
        versioning_service = ModelVersioningService()
        retrain_result = await versioning_service.retrain_with_versioning(force=True)
        print(f"Réentraînement: {retrain_result['status']}")
        
        print("\n=== TESTS TERMINÉS ===")
    
    # Exécuter les tests
    asyncio.run(test_persistence())
# -*- coding: utf-8 -*-
"""
Service de Vectorisation Sémantique pour SoniqueBay.

Le service s'appuie désormais sur `sentence-transformers`
avec le modèle **all-MiniLM-L6-v2** au lieu d'Ollama.
Compatible avec Raspberry Pi 4 et architecture microservices.

Auteur: SoniqueBay Team
"""

import asyncio
import httpx
import numpy as np
from typing import List, Optional, Dict, Any
import os
from backend_worker.utils.logging import logger
from backend_worker.services.ollama_embedding_service import (
    OllamaEmbeddingService,
    OllamaEmbeddingError
)


class VectorizationError(Exception):
    """Exception pour les erreurs de vectorisation."""
    pass


class OptimizedVectorizationService:
    """
    Service de vectorisation optimisé utilisant le service
    d'embeddings local. Les vecteurs produits font actuellement
    384 dimensions.
    """

    def __init__(self) -> None:
        """Initialise le service d'embeddings local."""
        self.embedding_service = OllamaEmbeddingService()
        self.is_trained = True  # le modèle local n'a pas besoin d'entraînement
        self.vector_dimension = OllamaEmbeddingService.EMBEDDING_DIMENSION
        
        # Attributs de compatibilité pour ModelPersistenceService (versioning)
        # Ces attributs simulent les vectorizers entraînables pour la compatibilité
        # avec l'ancien système de versioning sklearn
        self.text_vectorizer = _DummyTextVectorizer()
        self.audio_vectorizer = _DummyAudioVectorizer()
        self.tag_classifier = _DummyTagClassifier()

        logger.info(
            f"[VECTORIZATION] Service initialisé, dimension={self.vector_dimension}"
        )

    async def fetch_tracks_from_api(
        self, track_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les données des tracks depuis library_api.

        Args:
            track_ids: Liste des IDs (None pour toutes)

        Returns:
            Liste des données de tracks
        """
        return await self.embedding_service.fetch_tracks_from_api(track_ids)

    async def vectorize_single_track(
        self, track_data: Dict[str, Any]
    ) -> List[float]:
        """
        Vectorise une track unique.

        Args:
            track_data: Données de la track

        Returns:
            Vecteur d'embedding ({} dimensions)
        """.format(self.vector_dimension)
        try:
            # Formater le texte
            text = self.embedding_service.format_track_text(track_data)

            # Générer l'embedding
            embedding = await self.embedding_service.get_embedding(text)

            if not embedding:
                logger.warning(
                    f"[VECTORIZATION] Embedding nul pour track "
                    f"{track_data.get('id', 'unknown')}"
                )
                return [0.0] * self.vector_dimension

            logger.debug(
                f"[VECTORIZATION] Embedding généré: {len(embedding)} dimensions"
            )
            return embedding

        except OllamaEmbeddingError as e:
            logger.error(f"[VECTORIZATION] Erreur embedding: {e}")
            return [0.0] * self.vector_dimension
        except Exception as e:
            logger.error(f"[VECTORIZATION] Erreur inattendue: {e}")
            return [0.0] * self.vector_dimension

    async def store_vector_to_database(
        self, track_id: int, embedding: List[float]
    ) -> bool:
        """
        Stocke le vecteur dans la base de données via API.

        Args:
            track_id: ID de la track
            embedding: Vecteur d'embedding

        Returns:
            True si succès, False sinon
        """
        return await self.embedding_service.store_embedding_to_database(
            track_id, embedding
        )

    async def vectorize_and_store(
        self, track_id: int, track_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Vectorise et stocke une track.

        Args:
            track_id: ID de la track
            track_data: Données optionnelles de la track

        Returns:
            Résultat de la vectorisation
        """
        try:
            # Récupérer les données si non fournies
            if track_data is None:
                track_data = await self.embedding_service.fetch_track_from_api(
                    track_id
                )
                if not track_data:
                    return {
                        'track_id': track_id,
                        'status': 'error',
                        'message': 'Track non trouvée'
                    }

            # Vectoriser
            embedding = await self.vectorize_single_track(track_data)

            # Stocker
            success = await self.store_vector_to_database(track_id, embedding)

            return {
                'track_id': track_id,
                'status': 'success' if success else 'warning',
                'vector_dimension': len(embedding),
                'embedding_model': OllamaEmbeddingService.MODEL_NAME,
                'storage_success': success
            }

        except Exception as e:
            logger.error(f"[VECTORIZATION] Erreur vectorize_and_store: {e}")
            return {
                'track_id': track_id,
                'status': 'error',
                'message': str(e)
            }

    async def vectorize_and_store_batch(
        self, track_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Vectorise et stocke un batch de tracks.

        Args:
            track_ids: Liste des IDs de tracks

        Returns:
            Résultats de l'opération
        """
        return await self.embedding_service.vectorize_tracks_batch(track_ids)

    def is_ollama_available(self) -> bool:
        """Historique : vérifie si le modèle d'embedding local est disponible.

        La méthode conserve son nom pour rétro‑compatibilité, mais le
        modèle n'a plus rien à voir avec Ollama.
        """
        return self.embedding_service.is_model_available()

    # alias moderne
    def is_model_available(self) -> bool:
        """Alias plus générique de `is_ollama_available`."""
        return self.is_ollama_available()

    async def train_vectorizers(self) -> Dict[str, Any]:
        """
        Méthode de compatibilité pour le versioning des modèles.
        
        Le modèle sentence-transformers (all-MiniLM-L6-v2) est pré-entraîné
        et n'a pas besoin d'entraînement. Cette méthode retourne un succès
        immédiat car le modèle est déjà disponible.
        
        Returns:
            Dict avec le statut de l'entraînement (toujours succès)
        """
        logger.info("[VECTORIZATION] Vérification modèle pré-entraîné (sentence-transformers)")
        
        # Vérifier que le modèle est disponible
        model_available = self.is_model_available()
        
        if model_available:
            return {
                "status": "success",
                "message": "Modèle sentence-transformers prêt (pré-entraîné)",
                "model_type": "sentence-transformers",
                "model_name": OllamaEmbeddingService.MODEL_NAME,
                "vector_dimension": self.vector_dimension,
                "is_pretrained": True,
                "tracks_processed": 0  # Pas de nouvel entraînement nécessaire
            }
        else:
            return {
                "status": "error",
                "message": "Modèle sentence-transformers non disponible",
                "model_type": "sentence-transformers"
            }


# === FONCTIONS UTILITAIRES ===

async def vectorize_single_track_util(track_id: int) -> Dict[str, Any]:
    """
    Vectorise une track avec le service d'embeddings local.

    Args:
        track_id: ID de la track à vectoriser

    Returns:
        Résultat de la vectorisation
    """
    service = OptimizedVectorizationService()
    return await service.vectorize_and_store(track_id)


async def vectorize_all_tracks() -> Dict[str, Any]:
    """
    Vectorise toutes les tracks de la bibliothèque.

    Returns:
        Résultats complets de la vectorisation
    """
    service = OptimizedVectorizationService()

    try:
        # Récupérer tous les IDs de tracks
        tracks_data = await service.fetch_tracks_from_api()
        track_ids = [track["id"] for track in tracks_data if track.get("id")]

        if not track_ids:
            return {
                'status': 'warning',
                'message': 'Aucune track à vectoriser',
                'total_tracks': 0
            }

        logger.info(
            f"[VECTORIZATION] Début vectorisation: {len(track_ids)} tracks"
        )

        # Vectoriser par batches
        result = await service.vectorize_and_store_batch(track_ids)
        result['embedding_model'] = OllamaEmbeddingService.MODEL_NAME

        return result

    except Exception as e:
        logger.error(f"[VECTORIZATION] Erreur: {e}")
        return {'status': 'error', 'message': str(e)}


# === INTERFACE CELERY ===

def create_vectorization_task():
    """Factory pour créer des tâches Celery de vectorisation."""
    from celery import Task

    class VectorizeTrackTask(Task):
        """Tâche Celery pour vectoriser une track."""

        def run(self, track_id: int):
            """Exécute la vectorisation d'une track."""
            return asyncio.run(vectorize_single_track_util(track_id))

    return VectorizeTrackTask()


if __name__ == "__main__":
    """Tests du service de vectorisation."""
    import logging
    logging.basicConfig(level=logging.INFO)

    async def test_service():
        """Test du service de vectorisation local."""
        print("=== TEST VECTORIZATION ===")

        service = OptimizedVectorizationService()

        # Vérifier disponibilité du modèle
        print(f"\n1. Vérification modèle...")
        available = service.is_model_available()
        print(f"Modèle disponible: {available}")

        if not available:
            print("Note: modèle d'embedding non disponible")
            return

        # Test avec données fictives
        print("\n2. Test vectorisation...")
        test_data = {
            'title': 'Bohemian Rhapsody',
            'artist_name': 'Queen',
            'album_title': 'A Night at the Opera',
            'genre': 'Rock',
            'key': 'Bb',
            'bpm': 72,
            'duration': 354
        }

        embedding = await service.vectorize_single_track(test_data)
        print(f"Embedding généré: {len(embedding)} dimensions")
        print(f"Premières valeurs: {embedding[:5]}")

        print("\n=== TESTS TERMINÉS ===")

    # Exécuter les tests
    asyncio.run(test_service())


# === CLASSES FACTICES POUR COMPATIBILITÉ VERSIONING ===

class _DummyTextVectorizer:
    """Classe factice pour compatibilité avec ModelPersistenceService.
    
    Le modèle sentence-transformers est pré-entraîné et n'a pas besoin
    de vectorizer sklearn entraînable.
    """
    def __init__(self):
        self.pipeline = None
        self.vector_dimension = OllamaEmbeddingService.EMBEDDING_DIMENSION
        self.is_fitted = True
    
    def extract_text_features(self, text: str) -> dict:
        """Retourne un dictionnaire vide pour compatibilité."""
        return {}


class _DummyAudioVectorizer:
    """Classe factice pour compatibilité avec ModelPersistenceService."""
    def __init__(self):
        self.scaler = None
        self.key_encoder = None
        self.scale_encoder = None
        self.camelot_encoder = None
        self.is_fitted = True
        self.feature_names = []


class _DummyTagClassifier:
    """Classe factice pour compatibilité avec ModelPersistenceService."""
    def __init__(self):
        self.genre_classifier = None
        self.mood_classifier = None
        self.genre_classes = []
        self.mood_classes = []
        self.is_fitted = True

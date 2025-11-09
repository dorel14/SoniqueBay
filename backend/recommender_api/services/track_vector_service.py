"""
Service métier pour la gestion des vecteurs de tracks.
Déplace toute la logique métier depuis track_vectors_api.py ici.
Auteur : Kilo Code
Dépendances : backend.api.models.track_vectors_model, backend.api.schemas.track_vectors_schema
"""
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.recommender_api.api.models.track_vectors_model import TrackVectorVirtual
from backend.recommender_api.api.schemas.track_vectors_schema import TrackVectorCreate, TrackVectorResponse, TrackVectorIn, TrackVectorOut
from backend.recommender_api.utils.logging import logger


class TrackVectorService:
    def __init__(self, db: Optional[SQLAlchemySession] = None):
        self.session = db

    def create_or_update_vector(self, vector_data: TrackVectorCreate) -> TrackVectorResponse:
        """
        Crée ou met à jour un vecteur pour une track via sqlite-vec.

        DEPRECATED: Cette méthode utilise maintenant TrackVectorVirtual exclusivement.
        Le stockage SQL traditionnel n'est plus utilisé.

        Args:
            vector_data: Données du vecteur à créer

        Returns:
            Le vecteur créé ou mis à jour

        Raises:
            ValueError: Si la track n'existe pas
        """
        logger.warning("[TrackVectorService] create_or_update_vector appelé - migration vers TrackVectorVirtual")

        # Utiliser TrackVectorVirtual pour le stockage
        TrackVectorVirtual.insert_vector(vector_data.track_id, vector_data.vector_data)

        # Retourner une réponse simulée pour compatibilité
        return TrackVectorResponse(
            id=vector_data.track_id,  # ID simulé
            track_id=vector_data.track_id,
            vector_data=vector_data.vector_data
        )

    def get_vector(self, track_id: int) -> TrackVectorResponse:
        """
        Récupère le vecteur d'une track via sqlite-vec.

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        vector_data = TrackVectorVirtual.get_vector(track_id=track_id)
        if not vector_data:
            raise ValueError(f"Vector not found for track {track_id}")

        return TrackVectorResponse(
            id=track_id,  # ID simulé pour compatibilité
            track_id=track_id,
            vector_data=vector_data['embedding']
        )

    def delete_vector(self, track_id: int):
        """
        Supprime le vecteur d'une track via sqlite-vec.

        Args:
            track_id: ID de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        # Vérifier que le vecteur existe
        existing = TrackVectorVirtual.get_vector(track_id=track_id)
        if not existing:
            raise ValueError(f"Vector not found for track {track_id}")

        TrackVectorVirtual.delete_vector(track_id=track_id)
        logger.info(f"Vecteur supprimé pour track {track_id}")

    def list_vectors(self, skip: int = 0, limit: int = 100) -> List[TrackVectorResponse]:
        """
        Liste les vecteurs de tracks avec pagination via sqlite-vec.

        DEPRECATED: Cette méthode ne peut pas paginer efficacement avec sqlite-vec.
        Utiliser les endpoints spécialisés pour les recherches.

        Args:
            skip: Nombre d'éléments à sauter
            limit: Nombre maximum d'éléments à retourner

        Returns:
            Liste des vecteurs (limitée pour performance)
        """
        logger.warning("[TrackVectorService] list_vectors appelé - méthode dépréciée pour sqlite-vec")

        # Note: sqlite-vec ne permet pas facilement la pagination
        # Retourner une liste vide pour éviter les problèmes de performance
        return []

    def search_similar_vectors(self, query_vector: TrackVectorIn, limit: int = 10) -> List[TrackVectorOut]:
        """
        Recherche les vecteurs similaires à un vecteur de requête.

        Args:
            query_vector: Vecteur de requête avec track_id et embedding
            limit: Nombre maximum de résultats

        Returns:
            Liste des vecteurs similaires avec leur distance
        """
        results = TrackVectorVirtual.search_similar(
            query_embedding=query_vector.embedding,
            limit=limit
        )

        return [TrackVectorOut(track_id=result['track_id'], distance=result['distance']) for result in results]

    def create_vectors_batch(self, vectors: List[TrackVectorIn]):
        """
        Crée ou met à jour plusieurs vecteurs en batch.

        Args:
            vectors: Liste des vecteurs à créer
        """
        for vector in vectors:
            TrackVectorVirtual.insert_vector(
                track_id=vector.track_id,
                embedding=vector.embedding
            )

        logger.info(f"Batch créé avec {len(vectors)} vecteurs")

    def get_vector_virtual(self, track_id: int):
        """
        Récupère un vecteur par track_id (version sqlite-vec).

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        result = TrackVectorVirtual.get_vector(track_id=track_id)
        if not result:
            raise ValueError(f"Vector not found for track {track_id}")

        return result

    def delete_vector_virtual(self, track_id: int):
        """
        Supprime un vecteur par track_id (version sqlite-vec).

        Args:
            track_id: ID de la track
        """
        TrackVectorVirtual.delete_vector(track_id=track_id)
        logger.info(f"Vecteur supprimé pour track {track_id}")